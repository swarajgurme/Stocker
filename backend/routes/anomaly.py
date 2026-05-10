"""
Anomaly Detection Routes (Blueprint: /api/anomalies)
Sales anomaly detection, fraud detection, inventory inconsistencies
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from database import get_db_session
from models import Store, Product, Anomaly, AlertSeverity
from services.anomaly_service import AnomalyDetector, get_anomaly_detector
from auth_service import require_role, UserRole, get_current_user, log_auth_action

logger = logging.getLogger(__name__)

anomaly_bp = Blueprint('anomaly', __name__)


# ============= DETECT SALES ANOMALIES =============
@anomaly_bp.route('/detect/sales', methods=['POST'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER
)
def detect_sales_anomalies():
    """
    Trigger sales anomaly detection

    Request Body:
        {
            "store_id": "S001",  # optional
            "product_name": "Battery",  # optional
            "lookback_days": 90  # optional
        }

    Response (200):
        {
            "status": "success",
            "data": {
                "anomalies_detected": 3,
                "anomalies": [
                    {
                        "id": 1,
                        "date": "2026-05-01",
                        "anomaly_type": "demand_spike",
                        "severity": "high",
                        "score": 3.2,
                        "description": "..."
                    },
                    ...
                ]
            }
        }
    """
    user = g.current_user
    try:
        data = request.get_json() or {}
        store_id = data.get('store_id')
        product_name = data.get('product_name')
        lookback = int(data.get('lookback_days', 90))

        # Resolve IDs
        store_id_int = None
        product_id_int = None

        if store_id:
            with get_db_session() as db:
                store = db.query(Store).filter_by(store_code=store_id).first()
                if store:
                    store_id_int = store.id

        if product_name:
            with get_db_session() as db:
                product = db.query(Product).filter_by(name=product_name).first()
                if product:
                    product_id_int = product.id

        # Run detection
        detector = get_anomaly_detector()
        anomalies = detector.detect_sales_anomalies(
            store_id=store_id_int,
            product_id=product_id_int,
            lookback_days=lookback
        )

        # Audit
        log_auth_action(
            user_id=user.id,
            action="anomalies_detected",
            resource_type="anomaly",
            details={"store_id": store_id, "product": product_name, "count": len(anomalies)}
        )

        return jsonify({
            "status": "success",
            "data": {
                "anomalies_detected": len(anomalies),
                "anomalies": anomalies
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Anomaly detection error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Anomaly detection failed",
            "code": "DETECTION_ERROR"
        }), 500


# ============= LIST ANOMALIES =============
@anomaly_bp.route('', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.EXECUTIVE
)
def list_anomalies():
    """
    List detected anomalies

    Query params:
        ?store_id=S001
        &severity=critical
        &unreviewed_only=true
        &limit=50

    Response (200):
        {
            "status": "success",
            "data": {
                "anomalies": [...],
                "count": 5
            }
        }
    """
    try:
        store_id = request.args.get('store_id')
        severity = request.args.get('severity')
        unreviewed_only = request.args.get('unreviewed_only', 'false').lower() == 'true'
        limit = min(int(request.args.get('limit', 50)), 100)

        with get_db_session() as db:
            query = db.query(Anomaly)

            if store_id:
                store = db.query(Store).filter_by(store_code=store_id).first()
                if store:
                    query = query.filter_by(store_id=store.id)

            if severity:
                try:
                    sev = AlertSeverity(severity)
                    query = query.filter_by(severity=sev)
                except ValueError:
                    pass

            if unreviewed_only:
                query = query.filter_by(is_reviewed=False)

            query = query.order_by(Anomaly.created_at.desc()).limit(limit)
            anomalies = query.all()

            result = []
            for a in anomalies:
                store_obj = db.query(Store).get(a.store_id) if a.store_id else None
                product_obj = db.query(Product).get(a.product_id) if a.product_id else None

                result.append({
                    "id": a.id,
                    "store_id": store_obj.store_code if store_obj else None,
                    "product_name": product_obj.name if product_obj else None,
                    "anomaly_type": a.anomaly_type.value,
                    "severity": a.severity.value,
                    "score": a.score,
                    "description": a.description,
                    "detection_date": a.detection_date.isoformat() if a.detection_date else None,
                    "is_reviewed": a.is_reviewed,
                    "is_false_positive": a.is_false_positive,
                    "reviewed_by": a.reviewed_by,
                    "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None
                })

            return jsonify({
                "status": "success",
                "data": {
                    "anomalies": result,
                    "count": len(result)
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"List anomalies error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve anomalies",
            "code": "RETRIEVAL_ERROR"
        }), 500


# ============= MARK ANOMALY REVIEWED =============
@anomaly_bp.route('/<int:anomaly_id>/review', methods=['POST'])
@require_role(UserRole.ADMIN, UserRole.BUSINESS_ANALYST)
def review_anomaly(anomaly_id: int):
    """
    Mark an anomaly as reviewed (and optionally false positive)

    Request Body:
        {
            "is_false_positive": false  # optional
        }

    Response (200):
        {
            "status": "success",
            "message": "Anomaly marked as reviewed"
        }
    """
    user = g.current_user
    try:
        data = request.get_json() or {}
        is_false_positive = data.get('is_false_positive', False)

        detector = get_anomaly_detector()
        success = detector.mark_anomaly_reviewed(
            anomaly_id=anomaly_id,
            user_id=user.id,
            is_false_positive=is_false_positive
        )

        if not success:
            return jsonify({
                "status": "error",
                "error": "Anomaly not found",
                "code": "NOT_FOUND"
            }), 404

        # Audit
        log_auth_action(
            user_id=user.id,
            action="anomaly_reviewed",
            resource_type="anomaly",
            resource_id=str(anomaly_id),
            details={"is_false_positive": is_false_positive}
        )

        return jsonify({
            "status": "success",
            "message": "Anomaly reviewed"
        }), 200

    except Exception as e:
        logger.error(f"Review anomaly error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to review anomaly",
            "code": "REVIEW_ERROR"
        }), 500
