"""
Analytics Routes (Blueprint: /api/analytics)
Cluster analysis, KPIs, executive dashboards
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import func, and_

from flask import Blueprint, request, jsonify

from database import get_db_session, engine
from models import Store, Product, Sale, Cluster, Forecast, InventoryLevel, Anomaly
from services.analytics_service import AnalyticsService
from auth_service import require_role, UserRole, get_current_user, log_auth_action

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)


# ============= CLUSTER ANALYSIS =============
@analytics_bp.route('/cluster', methods=['GET'])
@analytics_bp.route('/clusters', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.EXECUTIVE
)
def get_clusters():
    """
    Get cluster analysis results

    Query params:
        ?analysis_date=2026-05-10  # latest if None
        &by_category=true
        &include_stats=true

    Response (200):
        {
            "status": "success",
            "data": {
                "analysis_date": "2026-05-10",
                "total_clusters": 5,
                "cluster_centroids": [...],
                "assignments": [
                    {
                        "store_id": "S001",
                        "category": "Engine",
                        "sales_ewma": 450.0,
                        "cluster": 2
                    },
                    ...
                ]
            }
        }
    """
    try:
        analysis_date_str = request.args.get('analysis_date')
        include_stats = request.args.get('include_stats', 'true').lower() == 'true'

        with get_db_session() as db:
            # Get latest analysis date if not specified
            if analysis_date_str:
                analysis_date = datetime.strptime(analysis_date_str, '%Y-%m-%d').date()
            else:
                latest = db.query(func.max(Cluster.cluster_analysis_date)).scalar()
                max_sale = db.query(func.max(Sale.sale_date)).scalar()
                analysis_date = latest or max_sale or datetime.utcnow().date()

            # Fetch cluster assignments
            clusters = db.query(Cluster).filter_by(
                cluster_analysis_date=analysis_date
            ).all()

            if not clusters:
                # Run clustering analysis
                service = AnalyticsService(db)
                service.run_cluster_analysis(analysis_date)
                clusters = db.query(Cluster).filter_by(
                    cluster_analysis_date=analysis_date
                ).all()

            # Build response
            assignments = []
            for c in clusters:
                store = db.query(Store).get(c.store_id)
                product = db.query(Product).get(c.product_id) if c.product_id else None

                assignments.append({
                    "store_id": store.store_code if store else "Unknown",
                    "product_name": product.name if product else None,
                    "category": c.category,
                    "sales_ewma": round(c.sales_ewma, 2),
                    "cluster": c.cluster_label
                })

            # Statistics
            stats = {}
            if include_stats:
                for a in assignments:
                    cluster = a['cluster']
                    if cluster not in stats:
                        stats[cluster] = {
                            "count": 0,
                            "total_sales": 0.0,
                            "avg_sales": 0.0
                        }
                    stats[cluster]["count"] += 1
                    stats[cluster]["total_sales"] += a['sales_ewma']

                for c in stats:
                    stats[c]["avg_sales"] = round(
                        stats[c]["total_sales"] / stats[c]["count"], 2
                    )

            total_clusters = len(set(a['cluster'] for a in assignments))

            # Audit
            user = get_current_user()
            if user:
                log_auth_action(
                    user_id=user.id,
                    action="clusters_viewed",
                    resource_type="analytics",
                    details={"date": str(analysis_date)}
                )

            return jsonify({
                "status": "success",
                "data": {
                    "analysis_date": str(analysis_date),
                    "total_clusters": total_clusters,
                    "assignments": assignments,
                    "statistics": stats
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Cluster analysis error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve cluster analysis",
            "code": "CLUSTER_ERROR"
        }), 500


# ============= EXECUTIVE KPI DASHBOARD =============
@analytics_bp.route('/dashboard/kpi', methods=['GET'])
@analytics_bp.route('/dashboard', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.EXECUTIVE
)
def get_executive_dashboard():
    """
    Get executive KPI dashboard data

    Response (200):
        {
            "status": "success",
            "data": {
                "revenue_trend": {...},
                "forecast_accuracy": {...},
                "inventory_turnover": {...},
                "low_stock_count": 5,
                "top_stores": [...],
                "category_performance": [...]
            }
        }
    """
    try:
        with get_db_session() as db:
            # Time range: last 12 months based on dataset sales
            max_date = db.query(func.max(Sale.sale_date)).scalar()
            end_date = max_date or datetime.utcnow().date()
            start_date = end_date - timedelta(days=365)

            # Revenue trend (monthly) — dialect-safe
            if engine.dialect.name == "postgresql":
                month_expr = func.date_trunc("month", Sale.sale_date).label("month")
            else:
                month_expr = func.strftime("%Y-%m", Sale.sale_date).label("month")

            monthly_revenue = (
                db.query(month_expr, func.sum(Sale.revenue).label("total"))
                .filter(Sale.sale_date.between(start_date, end_date))
                .group_by(month_expr)
                .order_by(month_expr)
                .all()
            )

            revenue_trend = []
            for row in monthly_revenue:
                m = row.month
                if hasattr(m, "strftime"):
                    month_str = m.strftime("%Y-%m")
                else:
                    month_str = str(m)[:7]
                revenue_trend.append(
                    {"month": month_str, "revenue": round(float(row.total), 2)}
                )

            # Forecast accuracy (avg MAPE)
            avg_mape = db.query(func.avg(Forecast.mape)).filter(
                Forecast.created_at >= datetime.utcnow() - timedelta(days=30),
                Forecast.status == 'completed'
            ).scalar()
            avg_mape = round(float(avg_mape or 0), 2)

            # Inventory turnover proxy: units sold / avg on-hand stock
            total_sales = (
                db.query(func.sum(Sale.quantity))
                .filter(Sale.sale_date >= start_date)
                .scalar()
                or 0
            )
            avg_inventory = (
                db.query(func.avg(InventoryLevel.current_stock)).scalar() or 0
            )
            avg_inventory_f = float(avg_inventory) if avg_inventory else 1.0
            inventory_turnover = round(
                float(total_sales) / avg_inventory_f if avg_inventory_f > 0 else 0,
                2,
            )

            # Low stock count
            low_stock = db.query(InventoryLevel).filter(
                InventoryLevel.current_stock < InventoryLevel.safety_stock
            ).count()

            anomalies_open = db.query(Anomaly).filter(
                Anomaly.is_reviewed.is_(False)
            ).count()

            active_stores = db.query(Store).filter(Store.is_active.is_(True)).count()

            # Top 5 stores by revenue
            top_stores = db.query(
                Store.store_code,
                func.sum(Sale.revenue).label('revenue')
            ).join(Sale, Store.id == Sale.store_id).filter(
                Sale.sale_date.between(start_date, end_date)
            ).group_by(Store.store_code)\
            .order_by(func.sum(Sale.revenue).desc()).limit(5).all()

            top_stores_list = [{
                "store_id": row.store_code,
                "revenue": round(float(row.revenue), 2)
            } for row in top_stores]

            # Category performance
            category_perf = db.query(
                Product.category,
                func.sum(Sale.revenue).label('revenue'),
                func.sum(Sale.quantity).label('quantity')
            ).join(Sale, Product.id == Sale.product_id).filter(
                Sale.sale_date.between(start_date, end_date)
            ).group_by(Product.category)\
            .order_by(func.sum(Sale.revenue).desc()).all()

            categories = [{
                "category": row.category,
                "revenue": round(float(row.revenue), 2),
                "quantity": int(row.quantity or 0)
            } for row in category_perf]

            return jsonify({
                "status": "success",
                "data": {
                    "revenue_trend": revenue_trend,
                    "forecast_accuracy": {
                        "avg_mape": avg_mape,
                        "interpretation": "Excellent" if avg_mape < 10 else "Good" if avg_mape < 20 else "Needs Improvement"
                    },
                    "inventory_turnover": inventory_turnover,
                    "low_stock_count": low_stock,
                    "anomalies_open": anomalies_open,
                    "active_stores": active_stores,
                    "demand_risk_score": round(
                        min(100.0, low_stock * 12 + anomalies_open * 7), 1
                    ),
                    "top_stores": top_stores_list,
                    "category_performance": categories,
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to load dashboard",
            "code": "DASHBOARD_ERROR"
        }), 500


# ============= SALES BY CATEGORY =============
@analytics_bp.route('/sales-by-category', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.EXECUTIVE
)
def sales_by_category():
    """
    Aggregate sales by product category

    Response (200):
        {
            "status": "success",
            "data": [
                {"category": "Engine", "total_sales": 12345.67, "units": 500},
                ...
            ]
        }
    """
    try:
        period = request.args.get('period', 'all')  # all, last_30_days, last_90_days, last_year

        with get_db_session() as db:
            query = db.query(
                Product.category,
                func.sum(Sale.revenue).label('total_sales'),
                func.sum(Sale.quantity).label('units')
            ).join(Product, Sale.product_id == Product.id)

            if period == 'last_30_days':
                cutoff = datetime.utcnow().date() - timedelta(days=30)
                query = query.filter(Sale.sale_date >= cutoff)
            elif period == 'last_90_days':
                cutoff = datetime.utcnow().date() - timedelta(days=90)
                query = query.filter(Sale.sale_date >= cutoff)
            elif period == 'last_year':
                cutoff = datetime.utcnow().date() - timedelta(days=365)
                query = query.filter(Sale.sale_date >= cutoff)

            query = query.group_by(Product.category)\
                .order_by(func.sum(Sale.revenue).desc())

            results = query.all()

            data = [{
                "category": row.category,
                "total_sales": round(float(row.total_sales or 0), 2),
                "units": int(row.units or 0)
            } for row in results]

            return jsonify({
                "status": "success",
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Sales by category error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve category sales",
            "code": "ANALYTICS_ERROR"
        }), 500


# ============= STORE COMPARISON =============
@analytics_bp.route('/store-comparison', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.EXECUTIVE
)
def compare_stores():
    """
    Compare performance across stores

    Query params:
        ?metric=revenue|units|forecast_accuracy
        &period=last_30_days

    Response (200):
        {
            "status": "success",
            "data": [
                {"store_id": "S001", "value": 12345.67},
                ...
            ]
        }
    """
    try:
        metric = request.args.get('metric', 'revenue')
        period = request.args.get('period', 'last_30_days')

        with get_db_session() as db:
            cutoff = datetime.utcnow().date()
            if period == 'last_30_days':
                cutoff -= timedelta(days=30)
            elif period == 'last_90_days':
                cutoff -= timedelta(days=90)
            elif period == 'last_year':
                cutoff -= timedelta(days=365)

            if metric == 'revenue':
                agg_value = func.sum(Sale.revenue).label('value')
            elif metric == 'units':
                agg_value = func.sum(Sale.quantity).label('value')
            else:
                return jsonify({
                    "status": "error",
                    "error": "Invalid metric. Use 'revenue' or 'units'",
                    "code": "VALIDATION_ERROR"
                }), 400

            results = db.query(
                Store.store_code,
                agg_value
            ).join(Sale, Store.id == Sale.store_id)\
             .filter(Sale.sale_date >= cutoff)\
             .group_by(Store.store_code)\
             .order_by(agg_value.desc())\
             .all()

            data = [{
                "store_id": row.store_code,
                "value": round(float(row.value or 0), 2)
            } for row in results]

            return jsonify({
                "status": "success",
                "data": data,
                "metric": metric,
                "period": period,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Store comparison error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to compare stores",
            "code": "COMPARISON_ERROR"
        }), 500


@analytics_bp.route('/transfers', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_analytics_transfers():
    """
    Get recommended inter-store stock transfers
    """
    try:
        with get_db_session() as db:
            service = AnalyticsService(db)
            transfers = service.generate_stock_transfers()
            return jsonify({
                "status": "success",
                "data": {
                    "transfers": transfers,
                    "count": len(transfers)
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200
    except Exception as e:
        logger.error(f"Error generating stock transfers: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to generate stock transfers",
            "code": "TRANSFER_ERROR"
        }), 500
