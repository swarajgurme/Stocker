"""
Forecast Routes (Blueprint: /api/forecast)
AI-driven sales forecasting with multiple models
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from flask import Blueprint, request, jsonify, current_app, g
from sqlalchemy import func, and_
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import numpy as np

from database import get_db_session, db_session
from models import (
    Store, Product, Sale, Forecast, ForecastValue,
    ForecastModelType, ModelVersion
)
from config import get_config
from services.forecast_service import ForecastService

from auth_service import require_role, UserRole, log_auth_action

logger = logging.getLogger(__name__)
config = get_config()

forecast_bp = Blueprint('forecast', __name__)


def _round_metric(value: Any) -> Optional[float]:
    """Round numeric metrics; MAPE may be None when evaluation has no valid baseline."""
    if value is None:
        return None
    return round(float(value), 4)


# ============= GENERATE FORECAST =============
@forecast_bp.route('/generate', methods=['POST'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def generate_forecast():
    """
    Generate sales forecast for a store-product combination

    Request Body:
        {
            "store_id": "S001",
            "product_name": "Battery",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "horizon_days": 365,  # optional
            "model_type": "prophet"  # optional: "prophet", "arima", "xgboost", "lstm", "auto"
        }

    Response (200):
        {
            "status": "success",
            "data": {
                "forecast_id": 123,
                "store_id": "S001",
                "product_name": "Battery",
                "model_type": "prophet",
                "forecast": [
                    {"date": "2024-01-01", "predicted": 120.5, "lower_bound": 100.2, "upper_bound": 140.8},
                    ...
                ],
                "metrics": {
                    "rmse": 15.3,
                    "mae": 12.1,
                    "mape": 8.5
                },
                "execution_time_seconds": 8.2
            },
            "timestamp": "2026-05-10T..."
        }
    """
    from auth_service import get_current_user
    user = g.current_user
    request_id = f"req-{datetime.utcnow().timestamp():.0f}"

    start_time = datetime.utcnow()

    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "error": "Request body required",
                "code": "INVALID_INPUT"
            }), 400

        # Extract parameters
        store_id = str(data.get('store_id', '')).strip()
        product_name = str(data.get('product_name', '')).strip()
        start_date_str = str(data.get('start_date', '')).strip()
        end_date_str = str(data.get('end_date', '')).strip()
        horizon_days = int(data.get('horizon_days', config.FORECAST_HORIZON_DAYS))
        model_type_str = str(data.get('model_type', 'auto')).lower()

        # Validate inputs
        from ml_utils.validators import validate_input as validate_store_product_dates
        is_valid, error_msg = validate_store_product_dates(
            store_id, product_name, start_date_str, end_date_str, horizon_days
        )
        if not is_valid:
            return jsonify({
                "status": "error",
                "error": error_msg,
                "code": "VALIDATION_ERROR"
            }), 400

        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

        allowed = frozenset({"prophet", "arima", "xgboost", "auto"})
        if model_type_str == "lstm":
            return jsonify({
                "status": "error",
                "error": "LSTM is not enabled in this deployment.",
                "code": "MODEL_NOT_AVAILABLE",
            }), 400
        if model_type_str not in allowed:
            model_type_str = "prophet"

        # Get store and product from DB (keep PKs — session closes before ML runs)
        with get_db_session() as db:
            store = db.query(Store).filter_by(store_code=store_id, is_active=True).first()
            product = db.query(Product).filter_by(name=product_name, is_active=True).first()

            if not store or not product:
                return jsonify({
                    "status": "error",
                    "error": "Store or product not found",
                    "code": "NOT_FOUND"
                }), 404

            store_pk = store.id
            product_pk = product.id

            # Fetch historical sales
            sales_query = db.query(Sale).filter(
                and_(
                    Sale.store_id == store_pk,
                    Sale.product_id == product_pk,
                    Sale.sale_date >= start_date - timedelta(days=365),  # Include prior year for context
                    Sale.sale_date <= end_date
                )
            ).order_by(Sale.sale_date)

            sales = sales_query.all()

            if len(sales) < config.MIN_HISTORICAL_DATA_POINTS:
                return jsonify({
                    "status": "error",
                    "error": f"Insufficient historical data. Need at least {config.MIN_HISTORICAL_DATA_POINTS} records, got {len(sales)}",
                    "code": "INSUFFICIENT_DATA"
                }), 400

            # Convert to DataFrame for ML
            df = pd.DataFrame([{
                'ds': s.sale_date,
                'y': s.ewma,
                'quantity': s.quantity,
                'revenue': s.revenue
            } for s in sales])

        try:
            forecaster = ForecastService()
            forecast_result = forecaster.train_and_forecast(
                df=df,
                horizon_days=horizon_days,
                confidence_interval=config.CONFIDENCE_INTERVAL,
                model_type=model_type_str,
            )
        except ValueError as e:
            return jsonify({
                "status": "error",
                "error": str(e),
                "code": "MODEL_ERROR",
            }), 400

        used_model = forecast_result.get("model_type", "prophet")
        try:
            persisted_model_type = ForecastModelType(used_model)
        except ValueError:
            persisted_model_type = ForecastModelType.PROPHET

        # Create forecast record in DB
        with get_db_session() as db:
            forecast = Forecast(
                store_id=store_pk,
                product_id=product_pk,
                model_type=persisted_model_type,
                horizon_days=horizon_days,
                start_date=start_date,
                end_date=end_date,
                status='completed',
                rmse=_round_metric(forecast_result['metrics'].get('rmse')),
                mae=_round_metric(forecast_result['metrics'].get('mae')),
                mape=_round_metric(forecast_result['metrics'].get('mape')),
                completed_at=datetime.utcnow()
            )
            db.add(forecast)
            db.flush()

            # Save forecast values
            for point in forecast_result['forecast']:
                fv = ForecastValue(
                    forecast_id=forecast.id,
                    date=datetime.strptime(point['date'], '%Y-%m-%d').date(),
                    predicted=point['predicted'],
                    lower_bound=point['lower_bound'],
                    upper_bound=point['upper_bound'],
                    actual=point.get('actual')  # For historical dates
                )
                db.add(fv)

            db.commit()
            forecast_id = forecast.id

        # Log audit
        log_auth_action(
            user_id=user.id,
            action="forecast_generated",
            resource_type="forecast",
            resource_id=str(forecast_id),
            details={
                "store_id": store_id,
                "product": product_name,
                "model": persisted_model_type.value,
                "horizon_days": horizon_days,
                "rmse": forecast_result['metrics']['rmse']
            }
        )

        execution_time = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"[{request_id}] Forecast completed in {execution_time:.2f}s: {store_id}/{product_name}")

        return jsonify({
            "status": "success",
            "data": {
                "forecast_id": forecast_id,
                "store_id": store_id,
                "product_name": product_name,
                "model_type": persisted_model_type.value,
                "forecast": forecast_result['forecast'],
                "metrics": {
                    "rmse": _round_metric(forecast_result['metrics'].get('rmse')),
                    "mae": _round_metric(forecast_result['metrics'].get('mae')),
                    "mape": _round_metric(forecast_result['metrics'].get('mape')),
                },
                "execution_time_seconds": round(execution_time, 2)
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except SQLAlchemyError as e:
        logger.error(f"[{request_id}] DB error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Database error during forecast",
            "code": "DB_ERROR"
        }), 500
    except ValueError as e:
        logger.error(f"[{request_id}] ValueError: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "code": "VALIDATION_ERROR"
        }), 400
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": "Forecast generation failed",
            "code": "FORECAST_ERROR"
        }), 500


# ============= GET FORECAST BY ID =============
@forecast_bp.route('/<int:forecast_id>', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER,
    UserRole.EXECUTIVE
)
def get_forecast(forecast_id: int):
    """
    Retrieve a previously generated forecast

    Response (200):
        {
            "status": "success",
            "data": { full forecast object with values }
        }
    """
    try:
        with get_db_session() as db:
            forecast = db.query(Forecast).filter_by(id=forecast_id).first()
            if not forecast:
                return jsonify({
                    "status": "error",
                    "error": "Forecast not found",
                    "code": "NOT_FOUND"
                }), 404

            # Fetch values
            values = db.query(ForecastValue).filter_by(forecast_id=forecast_id)\
                .order_by(ForecastValue.date).all()

            forecast_data = {
                "id": forecast.id,
                "store_id": forecast.store.store_code,
                "product_name": forecast.product.name,
                "model_type": forecast.model_type.value,
                "status": forecast.status,
                "metrics": {
                    "rmse": forecast.rmse,
                    "mae": forecast.mae,
                    "mape": forecast.mape
                },
                "created_at": forecast.created_at.isoformat() if forecast.created_at else None,
                "values": [{
                    "date": v.date.isoformat(),
                    "predicted": v.predicted,
                    "lower_bound": v.lower_bound,
                    "upper_bound": v.upper_bound,
                    "actual": v.actual
                } for v in values]
            }

        # Audit
        user = g.current_user
        log_auth_action(
            user_id=user.id,
            action="forecast_viewed",
            resource_type="forecast",
            resource_id=str(forecast_id)
        )

        return jsonify({
            "status": "success",
            "data": forecast_data,
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Get forecast error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve forecast",
            "code": "RETRIEVAL_ERROR"
        }), 500


# ============= LIST FORECASTS =============
@forecast_bp.route('/history', methods=['GET'])
@forecast_bp.route('', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER,
    UserRole.EXECUTIVE
)
def list_forecasts():
    """
    List forecasts with optional filters

    Query params:
        ?store_id=S001
        &product_name=Battery
        &model_type=prophet
        &status=completed
        &limit=50
        &offset=0

    Response (200):
        {
            "status": "success",
            "data": {
                "forecasts": [...],
                "total": 10
            }
        }
    """
    try:
        with get_db_session() as db:
            query = db.query(Forecast)

            # Apply filters
            store_id = request.args.get('store_id')
            if store_id:
                store = db.query(Store).filter_by(store_code=store_id).first()
                if store:
                    query = query.filter_by(store_id=store.id)

            product_name = request.args.get('product_name')
            if product_name:
                product = db.query(Product).filter_by(name=product_name).first()
                if product:
                    query = query.filter_by(product_id=product.id)

            model_type = request.args.get('model_type')
            if model_type:
                try:
                    mt = ForecastModelType(model_type)
                    query = query.filter_by(model_type=mt)
                except ValueError:
                    pass

            status = request.args.get('status')
            if status:
                query = query.filter_by(status=status)

            # Pagination
            limit = min(int(request.args.get('limit', 50)), 100)
            offset = int(request.args.get('offset', 0))

            total = query.count()
            forecasts = query.order_by(Forecast.created_at.desc())\
                .offset(offset).limit(limit).all()

            result = [{
                "id": f.id,
                "store_id": f.store.store_code,
                "product_name": f.product.name,
                "model_type": f.model_type.value,
                "status": f.status,
                "rmse": f.rmse,
                "mae": f.mae,
                "mape": f.mape,
                "created_at": f.created_at.isoformat() if f.created_at else None
            } for f in forecasts]

            return jsonify({
                "status": "success",
                "data": {
                    "forecasts": result,
                    "total": total,
                    "limit": limit,
                    "offset": offset
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"List forecasts error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to list forecasts",
            "code": "LIST_ERROR"
        }), 500


# ============= DELETE FORECAST =============
@forecast_bp.route('/<int:forecast_id>', methods=['DELETE'])
@require_role(UserRole.ADMIN, UserRole.BUSINESS_ANALYST)
def delete_forecast(forecast_id: int):
    """
    Delete a forecast (soft delete by marking status)

    Response (204):
        No content
    """
    try:
        with get_db_session() as db:
            forecast = db.query(Forecast).filter_by(id=forecast_id).first()
            if not forecast:
                return jsonify({
                    "status": "error",
                    "error": "Forecast not found",
                    "code": "NOT_FOUND"
                }), 404

            forecast.status = 'deleted'
            db.commit()

            user = g.current_user
            log_auth_action(
                user_id=user.id,
                action="forecast_deleted",
                resource_type="forecast",
                resource_id=str(forecast_id)
            )

            return '', 204

    except Exception as e:
        logger.error(f"Delete forecast error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to delete forecast",
            "code": "DELETE_ERROR"
        }), 500
