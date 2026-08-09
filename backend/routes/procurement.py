"""
Procurement Routes (Blueprint: /api/procurement)
FR-PR1: Procurement Recommendation UI Cards
FR-PR2: Lead Time Integration and Order By Date
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from database import get_db_session
from models import Store
from services.recommendation_service import RecommendationEngine
from auth_service import require_role, UserRole

logger = logging.getLogger(__name__)

procurement_bp = Blueprint('procurement', __name__)


@procurement_bp.route('/recommendations', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_procurement_recommendations():
    """
    GET /api/procurement/recommendations
    Returns actionable procurement cards including order_by_date based on supplier lead times and anomaly flags.
    """
    try:
        store_code = request.args.get('store_id')
        store_id_int = None

        with get_db_session() as db:
            if store_code:
                st = db.query(Store).filter_by(store_code=store_code).first()
                if st:
                    store_id_int = st.id

            engine = RecommendationEngine(db)
            cards = engine.generate_procurement_cards(store_id=store_id_int)

            return jsonify({
                "status": "success",
                "data": {
                    "recommendations": cards,
                    "count": len(cards)
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Procurement recommendations error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to generate procurement recommendations",
            "code": "PROCUREMENT_ERROR"
        }), 500
