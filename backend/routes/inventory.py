"""
Inventory Routes (Blueprint: /api/inventory)
Inventory optimization, reorder points, safety stock, alerts
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from sqlalchemy import and_, func

from database import get_db_session
from models import Store, Product, Supplier, InventoryLevel, InventoryAlert
from services.inventory_service import InventoryService, get_inventory_service
from services.forecast_service import ForecastService
from auth_service import require_role, UserRole, get_current_user, log_auth_action

logger = logging.getLogger(__name__)

inventory_bp = Blueprint('inventory', __name__)


# ============= INVENTORY OPTIMIZATION ENDPOINT =============
@inventory_bp.route('/optimization/<int:product_id>', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_inventory_optimization(product_id: int):
    """
    Get inventory optimization details (current stock, calculated ROP, calculated EOQ) for a product
    """
    try:
        with get_db_session() as db:
            product = db.query(Product).get(product_id)
            if not product:
                return jsonify({
                    "status": "error",
                    "error": f"Product with ID {product_id} not found",
                    "code": "NOT_FOUND"
                }), 404

            total_stock = db.query(func.sum(InventoryLevel.current_stock)).filter_by(product_id=product_id).scalar() or 0
            avg_rop = db.query(func.avg(InventoryLevel.reorder_point)).filter_by(product_id=product_id).scalar() or 0.0
            avg_safety_stock = db.query(func.avg(InventoryLevel.safety_stock)).filter_by(product_id=product_id).scalar() or 0.0

            inv_service = InventoryService(db)
            eoq_data = inv_service.calculate_eoq(product_id)

            supplier = db.query(Supplier).get(product.supplier_id) if product.supplier_id else None

            return jsonify({
                "status": "success",
                "data": {
                    "product_id": product.id,
                    "product_name": product.name,
                    "sku": product.sku,
                    "category": product.category,
                    "supplier_name": supplier.name if supplier else "Default Supplier",
                    "lead_time_days": supplier.lead_time_days if supplier else 7,
                    "current_stock": int(total_stock),
                    "calculated_rop": round(float(avg_rop), 2),
                    "calculated_safety_stock": round(float(avg_safety_stock), 2),
                    "calculated_eoq": eoq_data["eoq"],
                    "ordering_cost": eoq_data["ordering_cost"],
                    "holding_cost_per_unit": eoq_data["holding_cost_per_unit"],
                    "annual_demand": eoq_data["annual_demand"]
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200
    except Exception as e:
        logger.error(f"Inventory optimization error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": str(e),
            "code": "OPTIMIZATION_ERROR"
        }), 500


# ============= GET INVENTORY LEVELS =============
# SRS-compatible root path + nested path
@inventory_bp.route('', methods=['GET'])
@inventory_bp.route('/levels', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_inventory_levels():
    """
    Get current inventory levels for all or filtered store/products

    Query params:
        ?store_id=S001
        &product_name=Battery
        &low_stock_only=true

    Response (200):
        {
            "status": "success",
            "data": {
                "inventory": [
                    {
                        "id": 1,
                        "store_id": "S001",
                        "product_name": "Battery",
                        "current_stock": 150,
                        "safety_stock": 50.0,
                        "reorder_point": 200.0,
                        "lead_time_days": 7,
                        "status": "healthy"  // healthy, warning, critical
                    },
                    ...
                ]
            }
        }
    """
    try:
        store_id = request.args.get('store_id')
        product_name = request.args.get('product_name')
        low_stock_only = request.args.get('low_stock_only', 'false').lower() == 'true'

        with get_db_session() as db:
            query = db.query(InventoryLevel)

            if store_id:
                store = db.query(Store).filter_by(store_code=store_id).first()
                if store:
                    query = query.filter_by(store_id=store.id)

            if product_name:
                product = db.query(Product).filter_by(name=product_name).first()
                if product:
                    query = query.filter_by(product_id=product.id)

            levels = query.all()

            result = []
            for level in levels:
                store = db.query(Store).get(level.store_id)
                product = db.query(Product).get(level.product_id)

                if not store or not product:
                    continue

                # Determine status
                if level.current_stock < level.safety_stock:
                    status = "critical"
                elif level.current_stock < level.reorder_point:
                    status = "warning"
                else:
                    status = "healthy"

                if low_stock_only and status not in ("warning", "critical"):
                    continue

                result.append({
                    "id": level.id,
                    "store_id": store.store_code,
                    "product_name": product.name,
                    "category": product.category,
                    "current_stock": level.current_stock,
                    "safety_stock": round(level.safety_stock, 2),
                    "reorder_point": round(level.reorder_point, 2),
                    "lead_time_days": level.lead_time_days,
                    "last_calculated": level.last_calculated.isoformat() if level.last_calculated else None,
                    "status": status
                })

            return jsonify({
                "status": "success",
                "data": {
                    "inventory": result,
                    "count": len(result)
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Get inventory error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve inventory",
            "code": "RETRIEVAL_ERROR"
        }), 500


# ============= UPDATE INVENTORY LEVEL =============
@inventory_bp.route('/levels/<int:level_id>', methods=['PUT'])
@require_role(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_PLANNER, UserRole.STORE_MANAGER)
def update_inventory_level(level_id: int):
    """
    Update inventory level (current stock, lead time, etc.)

    Request Body:
        {
            "current_stock": 150,
            "lead_time_days": 7
        }

    Response (200):
        {
            "status": "success",
            "data": { updated inventory object }
        }
    """
    user = g.current_user
    try:
        data = request.get_json() or {}

        with get_db_session() as db:
            level = db.query(InventoryLevel).filter_by(id=level_id).first()
            if not level:
                return jsonify({
                    "status": "error",
                    "error": "Inventory level not found",
                    "code": "NOT_FOUND"
                }), 404

            if 'current_stock' in data:
                level.current_stock = int(data['current_stock'])
            if 'lead_time_days' in data:
                level.lead_time_days = int(data['lead_time_days'])

            # Recalculate ROP if stock or lead time changed
            if 'current_stock' in data or 'lead_time_days' in data:
                service = InventoryService(db)
                result = service.calculate_reorder_point(
                    level.store_id,
                    level.product_id,
                    level.lead_time_days
                )
                level.safety_stock = result['safety_stock']
                level.reorder_point = result['reorder_point']

            level.updated_at = datetime.utcnow()
            db.commit()

            # Audit
            log_auth_action(
                user_id=user.id,
                action="inventory_updated",
                resource_type="inventory_level",
                resource_id=str(level_id),
                details=data
            )

            return jsonify({
                "status": "success",
                "data": {
                    "id": level.id,
                    "current_stock": level.current_stock,
                    "safety_stock": round(level.safety_stock, 2),
                    "reorder_point": round(level.reorder_point, 2),
                    "lead_time_days": level.lead_time_days
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Update inventory error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to update inventory",
            "code": "UPDATE_ERROR"
        }), 500


# ============= CALCULATE ROP =============
@inventory_bp.route('/reorder-point/<string:store_id>/<string:product_name>', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_reorder_point(store_id: str, product_name: str):
    """
    Calculate and return reorder point for a store-product

    Response (200):
        {
            "status": "success",
            "data": {
                "store_id": "S001",
                "product_name": "Battery",
                "avg_daily_demand": 12.5,
                "std_daily_demand": 3.2,
                "lead_time_days": 7,
                "safety_stock": 15.3,
                "reorder_point": 103.3
            }
        }
    """
    try:
        with get_db_session() as db:
            store = db.query(Store).filter_by(store_code=store_id).first()
            product = db.query(Product).filter_by(name=product_name).first()

            if not store or not product:
                return jsonify({
                    "status": "error",
                    "error": "Store or product not found",
                    "code": "NOT_FOUND"
                }), 404

            service = InventoryService(db)
            result = service.calculate_reorder_point(store.id, product.id)

            return jsonify({
                "status": "success",
                "data": result,
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except ValueError as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "code": "INSUFFICIENT_DATA"
        }), 400
    except Exception as e:
        logger.error(f"ROP calculation error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Calculation failed",
            "code": "CALCULATION_ERROR"
        }), 500


# ============= GET ALERTS =============
@inventory_bp.route('/alerts', methods=['GET'])
@require_role(
    UserRole.ADMIN,
    UserRole.BUSINESS_ANALYST,
    UserRole.SUPPLY_CHAIN_PLANNER,
    UserRole.STORE_MANAGER
)
def get_alerts():
    """
    Get active inventory alerts

    Query params:
        ?store_id=S001
        &alert_type=low_stock
        &severity=critical
        &unresolved_only=true

    Response (200):
        {
            "status": "success",
            "data": {
                "alerts": [
                    {
                        "id": 1,
                        "store_id": "S001",
                        "product_name": "Battery",
                        "alert_type": "low_stock",
                        "severity": "critical",
                        "message": "...",
                        "created_at": "2026-05-10T..."
                    },
                    ...
                ]
            }
        }
    """
    try:
        store_id = request.args.get('store_id')
        alert_type = request.args.get('alert_type')
        severity = request.args.get('severity')
        unresolved_only = request.args.get('unresolved_only', 'true').lower() == 'true'

        with get_db_session() as db:
            query = db.query(InventoryAlert)

            if store_id:
                store = db.query(Store).filter_by(store_code=store_id).first()
                if store:
                    query = query.join(InventoryLevel).filter(
                        InventoryLevel.store_id == store.id
                    )

            if alert_type:
                try:
                    at = AlertType(alert_type)
                    query = query.filter_by(alert_type=at)
                except ValueError:
                    pass

            if severity:
                try:
                    sev = AlertSeverity(severity)
                    query = query.filter_by(severity=sev)
                except ValueError:
                    pass

            if unresolved_only:
                query = query.filter_by(is_resolved=False)

            alerts = query.order_by(
                InventoryAlert.created_at.desc()
            ).limit(100).all()

            result = []
            for alert in alerts:
                inv = db.query(InventoryLevel).get(alert.inventory_level_id)
                if not inv:
                    continue

                store = db.query(Store).get(inv.store_id)
                product = db.query(Product).get(inv.product_id)

                result.append({
                    "id": alert.id,
                    "store_id": store.store_code if store else "Unknown",
                    "product_name": product.name if product else "Unknown",
                    "alert_type": alert.alert_type.value,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value,
                    "is_resolved": alert.is_resolved,
                    "created_at": alert.created_at.isoformat() if alert.created_at else None
                })

            return jsonify({
                "status": "success",
                "data": {
                    "alerts": result,
                    "count": len(result)
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Get alerts error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to retrieve alerts",
            "code": "RETRIEVAL_ERROR"
        }), 500


# ============= RESOLVE ALERT =============
@inventory_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
@require_role(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_PLANNER, UserRole.STORE_MANAGER)
def resolve_alert(alert_id: int):
    """
    Mark an inventory alert as resolved

    Request Body:
        {
            "resolution_notes": "Stock replenished"
        }

    Response (200):
        {
            "status": "success",
            "message": "Alert resolved"
        }
    """
    user = g.current_user
    try:
        data = request.get_json() or {}
        notes = data.get('resolution_notes', '')

        with get_db_session() as db:
            alert = db.query(InventoryAlert).filter_by(id=alert_id).first()
            if not alert:
                return jsonify({
                    "status": "error",
                    "error": "Alert not found",
                    "code": "NOT_FOUND"
                }), 404

            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()

            db.commit()

            # Audit
            log_auth_action(
                user_id=user.id,
                action="alert_resolved",
                resource_type="inventory_alert",
                resource_id=str(alert_id),
                details={"notes": notes}
            )

            return jsonify({
                "status": "success",
                "message": "Alert resolved"
            }), 200

    except Exception as e:
        logger.error(f"Resolve alert error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Failed to resolve alert",
            "code": "RESOLVE_ERROR"
        }), 500


# ============= BULK UPDATE INVENTORY =============
@inventory_bp.route('/levels/bulk-update', methods=['POST'])
@require_role(UserRole.ADMIN, UserRole.SUPPLY_CHAIN_PLANNER)
def bulk_update_inventory():
    """
    Bulk update inventory levels (e.g., after stock count)

    Request Body:
        [
            {
                "store_id": "S001",
                "product_name": "Battery",
                "current_stock": 150
            },
            ...
        ]

    Response (200):
        {
            "status": "success",
            "data": {
                "updated": 5,
                "failed": 0
            }
        }
    """
    user = g.current_user
    try:
        updates = request.get_json()
        if not isinstance(updates, list):
            return jsonify({
                "status": "error",
                "error": "Expected array of updates",
                "code": "VALIDATION_ERROR"
            }), 400

        with get_db_session() as db:
            updated = 0
            failed = 0

            for item in updates:
                store_id = item.get('store_id')
                product_name = item.get('product_name')
                current_stock = item.get('current_stock')

                if not store_id or not product_name or current_stock is None:
                    failed += 1
                    continue

                store = db.query(Store).filter_by(store_code=store_id).first()
                product = db.query(Product).filter_by(name=product_name).first()

                if not store or not product:
                    failed += 1
                    continue

                level = db.query(InventoryLevel).filter_by(
                    store_id=store.id,
                    product_id=product.id
                ).first()

                if level:
                    level.current_stock = int(current_stock)
                else:
                    level = InventoryLevel(
                        store_id=store.id,
                        product_id=product.id,
                        current_stock=int(current_stock),
                        safety_stock=0,
                        reorder_point=0,
                        last_calculated=datetime.utcnow()
                    )
                    db.add(level)

                # Recalculate ROP
                service = InventoryService(db)
                try:
                    result = service.calculate_reorder_point(store.id, product.id)
                    level.safety_stock = result['safety_stock']
                    level.reorder_point = result['reorder_point']
                    updated += 1
                except Exception as e:
                    logger.warning(f"Failed ROP calc for {store_id}/{product_name}: {e}")
                    failed += 1

            db.commit()

            # Audit
            log_auth_action(
                user_id=user.id,
                action="bulk_inventory_update",
                resource_type="inventory",
                details={"updated": updated, "failed": failed}
            )

            return jsonify({
                "status": "success",
                "data": {
                    "updated": updated,
                    "failed": failed
                },
                "timestamp": datetime.utcnow().isoformat()
            }), 200

    except Exception as e:
        logger.error(f"Bulk update error: {str(e)}")
        return jsonify({
            "status": "error",
            "error": "Bulk update failed",
            "code": "BULK_ERROR"
        }), 500
