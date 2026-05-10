"""
Recommendation Routes (Blueprint: /api/recommendations)
AI-driven inventory and procurement recommendations
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g

from database import get_db_session
from models import Store, Product, Recommendation, RecommendationType
from services.recommendation_service import RecommendationEngine, get_recommendation_engine
from auth_service import require_role, UserRole, get_current_user, log_auth_action

logger = logging.getLogger(__name__)

recommendation_bp = Blueprint('recommendation', __name__)


# ============= GET RECOMMENDATIONS =============
@recommendation_bp.route('', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_recommendations():
    """
    Get actionable AI recommendations

    Query params:
        ?store_id=S001
        &product_name=Battery
        &type=increase_stock
        &priority=1
        &unaddressed=true

    Response (200):
        {
            "status": "success",
            "data": {
                "recommendations": [
                    {
                        "id": 1,
                        "store_id": "S001",
                        "product_name": "Battery",
                        "type": "increase_stock",
                        "priority": 1,
                        "title": "Immediate Restock Required",
                        "description": "...",
                        "rationale": "...",
                        "confidence_score": 0.85,
                        "expected_impact": "...",
                        "created_at": "2026-05-10T..."
                    },
                    ...
                ],
                "count": 5
            }
        }
    """
    try:
        store_id = request.args.get('store_id')
        product_name = request.args.get('product_name')
        rec_type = request.args.get('type')
        priority = request.args.get('priority')
        unaddressed = request.args.get('unaddressed', 'true').lower() == 'true'

        with get_db_session() as db:
            query = db.query(Recommendation)

            if store_id:
                store = db.query(Store).filter_by(store_code=store_id).first()
                if store:
                    query = query.filter_by(store_id=store.id)

            if product_name:
                product = db.query(Product).filter_by(name=product_name).first()
                if product:
                    query = query.filter_by(product_id=product.id)

            if rec_type:
                try:
                    rt = RecommendationType(rec_type)
                    query = query.filter_by(rec_type=rt)
                except ValueError:
                    pass

            if priority:
                try:
                    pri = int(priority)
                    query = query.filter_by(priority=pri)
                except ValueError:
                    pass

            if unaddressed:
                query = query.filter_by(is_acted=False)

            # Also filter expired
            query = query.filter(
                (Recommendation.expires_at.is_(None)) |
                (Recommendation.expires_at > datetime.utcnow())
            )

            recs = query.order_by(
                Recommendation.priority.asc(),
                Recommendation.created_at.desc()
            ).limit(50).all()

            result = []
            for r in recs:
                store_obj = db.query(Store).get(r.store_id) if r.store_id else None
                product_obj = db.query(Product).get(r.product_id) if r.product_id else None

                result.append({
                    "id": r.id,
                    "store_id": store_obj.store_code if store_obj else None,
                    "product_name": product_obj.name if product_obj else None,
                    "type": r.rec_type.value,
                    "priority": r.priority,
                    "title": r.title,
                    "description": r.description,
                    "rationale": r.rationale,
                    "confidence_score": r.confidence_score,
                    "expected_impact": r.expected_impact,
                    "is_acted": r.is_acted,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "expires_at": r.expires_at.isoformat() if r.expires_at else None
                })

            return jsonify({
                "status": "success",
                "data": {
                    "recommendations": result,
                    "count": len(result)
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Get recommendations error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve recommendations",
            "code": "RETRIEVAL_ERROR"
        }), 500


# ============= GENERATE RECOMMENDATIONS =============
@recommendation_bp.route('/generate', methods=['POST'])
@require_role(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_PLANNER, UserRole.BUSINESS_ANALYST)
def generate_recommendations():
    """
    Manually trigger recommendation generation

    Request Body:
        {
            "store_id": "S001",  # optional, generates for all if None
            "product_name": "Battery"  # optional
        }

    Response (200):
        {
            "status": "success",
            "data": {
                "generated": 5,
                "recommendations": [...]
            }
        }
    """
    user = g.current_user
    try:
        data = request.get_json() or {}
        store_id = data.get('store_id')
        product_name = data.get('product_name')

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

        # Generate
        engine = get_recommendation_engine()
        recs = engine.generate_stock_recommendations(
            store_id=store_id_int,
            product_id=product_id_int,
            limit=20
        )

        # Audit
        log_auth_action(
            user_id=user.id,
            action="recommendations_generated",
            resource_type="recommendation",
            details={"store_id": store_id, "product": product_name, "count": len(recs)}
        )

        return jsonify({
            "status": "success",
            "data": {
                "generated": len(recs),
                "recommendations": recs
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Generate recommendations error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to generate recommendations",
            "code": "GENERATION_ERROR"
        }), 500


# ============= MARK RECOMMENDATION ACTED =============
@recommendation_bp.route('/<int:rec_id>/act', methods=['POST'])
@require_role(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_PLANNER, UserRole.STORE_MANAGER)
def mark_recommendation_acted(rec_id: int):
    """
    Mark a recommendation as acted upon (order placed, stock adjusted, etc.)

    Request Body:
        {
            "notes": "Ordered 150 units from supplier"
        }

    Response (200):
        {
            "status": "success",
            "message": "Recommendation marked as acted"
        }
    """
    user = g.current_user
    try:
        data = request.get_json() or {}
        notes = data.get('notes', '')

        with get_db_session() as db:
            rec = db.query(Recommendation).filter_by(id=rec_id).first()
            if not rec:
                return jsonify({
                    "status": "error",
                    "error": "Recommendation not found",
                    "code": "NOT_FOUND"
                }), 404

            rec.is_acted = True
            rec.acted_at = datetime.utcnow()

            db.commit()

            # Audit
            log_auth_action(
                user_id=user.id,
                action="recommendation_acted",
                resource_type="recommendation",
                resource_id=str(rec_id),
                details={"notes": notes}
            )

            return jsonify({
                "status": "success",
                "message": "Recommendation marked as acted"
            }), 200

    except Exception as e:
        logger.error(f"Act recommendation error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to mark recommendation",
            "code": "ACTION_ERROR"
        }), 500
