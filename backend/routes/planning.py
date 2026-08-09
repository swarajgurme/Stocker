"""
Supply Chain Planning Routes (Blueprint: /api/planning)
FR-P1: Intelligent Stock Transfer Suggestions across network
FR-P2: Network Segmentation
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify

from database import get_db_session
from services.analytics_service import AnalyticsService
from auth_service import require_role, UserRole

logger = logging.getLogger(__name__)

planning_bp = Blueprint('planning', __name__)


@planning_bp.route('/transfers', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_planning_transfers():
    """
    GET /api/planning/transfers
    Returns a JSON array of recommended inter-store stock transfers
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
