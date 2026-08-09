"""
Inventory Service
Business logic for inventory optimization, reorder points, safety stock, alerts
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_
import numpy as np

from database import get_db_session
from models import (
    Store, Product, Sale, InventoryLevel, InventoryAlert,
    AlertType, AlertSeverity
)
from services.forecast_service import ForecastService

logger = logging.getLogger(__name__)


class InventoryService:
    """Service for inventory optimization calculations"""

    def __init__(self, db_session):
        self.db = db_session
        self.z_score = 1.65  # 95% service level for safety stock

    def calculate_reorder_point(
        self,
        store_id: int,
        product_id: int,
        lead_time_days: Optional[int] = None
    ) -> Dict:
        """
        Calculate Reorder Point (ROP)

        ROP = (Daily Average Demand × Lead Time) + Safety Stock

        Args:
            store_id: Store database ID
            product_id: Product database ID
            lead_time_days: Supplier lead time (default from inventory record or 7)

        Returns:
            Dict with reorder_point, daily_demand, safety_stock, etc.
        """
        try:
            # Get historical demand (last 90 days)
            cutoff_date = datetime.utcnow().date() - timedelta(days=90)
            sales = self.db.query(Sale).filter(
                and_(
                    Sale.store_id == store_id,
                    Sale.product_id == product_id,
                    Sale.sale_date >= cutoff_date
                )
            ).all()

            if not sales:
                raise ValueError("No sales data available for demand calculation")

            # Calculate daily demand
            daily_demands = [s.quantity for s in sales]
            avg_daily_demand = np.mean(daily_demands)
            std_daily_demand = np.std(daily_demands)

            # Get lead time
            inventory = self.db.query(InventoryLevel).filter_by(
                store_id=store_id,
                product_id=product_id
            ).first()
            lead_time = lead_time_days or (inventory.lead_time_days if inventory else 7)

            # Calculate safety stock
            # Safety Stock = Z-score × √(Lead Time) × Demand Std Dev
            safety_stock = self.z_score * np.sqrt(lead_time) * std_daily_demand

            # Calculate ROP
            reorder_point = (avg_daily_demand * lead_time) + safety_stock

            result = {
                "store_id": store_id,
                "product_id": product_id,
                "avg_daily_demand": round(float(avg_daily_demand), 2),
                "std_daily_demand": round(float(std_daily_demand), 2),
                "lead_time_days": lead_time,
                "safety_stock": round(float(safety_stock), 2),
                "reorder_point": round(float(reorder_point), 2)
            }

            # Save to inventory_levels table
            if inventory:
                inventory.safety_stock = safety_stock
                inventory.reorder_point = reorder_point
                inventory.last_calculated = datetime.utcnow()
            else:
                inventory = InventoryLevel(
                    store_id=store_id,
                    product_id=product_id,
                    current_stock=0,
                    safety_stock=safety_stock,
                    reorder_point=reorder_point,
                    lead_time_days=lead_time,
                    last_calculated=datetime.utcnow()
                )
                self.db.add(inventory)

            self.db.commit()

            logger.info(f"ROP calculated: store={store_id}, product={product_id}, ROP={reorder_point:.2f}")
            return result

        except Exception as e:
            logger.error(f"ROP calculation error: {str(e)}")
            raise

    def calculate_eoq(
        self,
        product_id: int,
        annual_demand: Optional[float] = None
    ) -> Dict:
        """
        Calculate Economic Order Quantity (EOQ)

        EOQ = sqrt((2 * D * S) / H)
        where:
        D = Annual Demand
        S = Ordering Cost per PO
        H = Holding Cost per unit per year
        """
        import math
        product = self.db.query(Product).get(product_id)
        if not product:
            raise ValueError(f"Product with id {product_id} not found")

        # If annual_demand not supplied, calculate from last 365 days of sales
        if annual_demand is None or annual_demand <= 0:
            cutoff = datetime.utcnow().date() - timedelta(days=365)
            tot_sales = self.db.query(func.sum(Sale.quantity)).filter(
                and_(Sale.product_id == product_id, Sale.sale_date >= cutoff)
            ).scalar()
            annual_demand = float(tot_sales) if tot_sales and tot_sales > 0 else 365.0

        S = float(product.ordering_cost or 50.0)
        H = float(product.holding_cost_per_unit or 5.0)

        if H <= 0:
            H = 1.0  # prevent division by zero

        eoq = math.sqrt((2.0 * annual_demand * S) / H)

        return {
            "product_id": product_id,
            "product_name": product.name,
            "annual_demand": round(annual_demand, 2),
            "ordering_cost": round(S, 2),
            "holding_cost_per_unit": round(H, 2),
            "eoq": int(round(eoq))
        }

    def calculate_safety_stock(
        self,
        store_id: int,
        product_id: int,
        service_level: float = 0.95
    ) -> float:
        """
        Calculate safety stock using statistical method

        Safety Stock = Z × σ_demand × √(Lead Time)
        """
        try:
            # Get demand data (last 6 months)
            cutoff_date = datetime.utcnow().date() - timedelta(days=180)
            sales = self.db.query(Sale).filter(
                and_(
                    Sale.store_id == store_id,
                    Sale.product_id == product_id,
                    Sale.sale_date >= cutoff_date
                )
            ).all()

            if not sales:
                return 0.0

            # Daily demand aggregation
            from collections import defaultdict
            daily_totals = defaultdict(int)
            for s in sales:
                daily_totals[s.sale_date] += s.quantity

            demands = list(daily_totals.values())
            std_demand = np.std(demands)

            # Z-score for service level
            from scipy.stats import norm
            z_score = norm.ppf(service_level)

            # Lead time (default 7 days)
            lead_time = 7

            safety_stock = z_score * np.sqrt(lead_time) * std_demand
            return round(float(safety_stock), 2)

        except Exception as e:
            logger.error(f"Safety stock calculation error: {str(e)}")
            return 0.0

    def detect_overstock(
        self,
        store_id: int,
        product_id: int,
        threshold_multiplier: float = 1.5
    ) -> Optional[Dict]:
        """
        Detect overstock condition

        Overstock if: Current Stock > (Avg Monthly Demand × Threshold Multiplier)

        Returns:
            Alert dictionary if overstock detected, None otherwise
        """
        try:
            inventory = self.db.query(InventoryLevel).filter_by(
                store_id=store_id,
                product_id=product_id
            ).first()

            if not inventory:
                return None

            # Get avg monthly demand
            cutoff_date = datetime.utcnow().date() - timedelta(days=30)
            monthly_sales = self.db.query(func.sum(Sale.quantity)).filter(
                and_(
                    Sale.store_id == store_id,
                    Sale.product_id == product_id,
                    Sale.sale_date >= cutoff_date
                )
            ).scalar() or 0

            threshold = monthly_sales * threshold_multiplier

            if inventory.current_stock > threshold:
                alert = {
                    "alert_type": AlertType.OVERSTOCK,
                    "severity": AlertSeverity.MEDIUM,
                    "message": f"Overstock detected: Current stock ({inventory.current_stock}) exceeds {threshold_multiplier}x monthly demand ({threshold:.0f})",
                    "current_value": inventory.current_stock,
                    "threshold_value": threshold
                }
                return alert

            return None

        except Exception as e:
            logger.error(f"Overstock detection error: {str(e)}")
            return None

    def detect_understock_risk(
        self,
        store_id: int,
        product_id: int
    ) -> Optional[Dict]:
        """
        Detect understock/risk of stockout

        Understock if: Current Stock < Safety Stock
        At risk if: Current Stock < ROP

        Returns:
            Alert dictionary if at risk
        """
        try:
            inventory = self.db.query(InventoryLevel).filter_by(
                store_id=store_id,
                product_id=product_id
            ).first()

            if not inventory:
                return None

            # Ensure we have ROP and safety stock calculated
            if inventory.reorder_point == 0 or inventory.safety_stock == 0:
                # Trigger calculation
                self.calculate_reorder_point(store_id, product_id)
                self.db.refresh(inventory)

            # Check conditions
            if inventory.current_stock < inventory.safety_stock:
                alert = {
                    "alert_type": AlertType.LOW_STOCK,
                    "severity": AlertSeverity.CRITICAL,
                    "message": f"Critical low stock: {inventory.current_stock} units below safety stock ({inventory.safety_stock})",
                    "current_value": inventory.current_stock,
                    "threshold_value": inventory.safety_stock
                }
                return alert
            elif inventory.current_stock < inventory.reorder_point:
                alert = {
                    "alert_type": AlertType.UNDERSTOCK_RISK,
                    "severity": AlertSeverity.HIGH,
                    "message": f"Reorder point reached: {inventory.current_stock} units (ROP: {inventory.reorder_point})",
                    "current_value": inventory.current_stock,
                    "threshold_value": inventory.reorder_point
                }
                return alert

            return None

        except Exception as e:
            logger.error(f"Understock detection error: {str(e)}")
            return None

    def generate_inventory_alerts(
        self,
        store_id: Optional[int] = None,
        limit_per_store: int = 10
    ) -> List[Dict]:
        """
        Generate inventory alerts for all stores or specific store

        Returns:
            List of alert dictionaries
        """
        alerts = []

        try:
            # Build query
            query = self.db.query(InventoryLevel)
            if store_id:
                query = query.filter_by(store_id=store_id)

            inventory_levels = query.all()

            for inv in inventory_levels:
                # Calculate ROP if not done
                if inv.reorder_point == 0:
                    self.calculate_reorder_point(inv.store_id, inv.product_id)
                    self.db.refresh(inv)

                # Check overstock
                overstock_alert = self.detect_overstock(inv.store_id, inv.product_id)
                if overstock_alert:
                    alerts.append(overstock_alert)

                # Check understock
                understock_alert = self.detect_understock_risk(inv.store_id, inv.product_id)
                if understock_alert:
                    alerts.append(understock_alert)

                # Persist alerts
                for alert in alerts[-2:]:  # Last 2 alerts for this product
                    existing = self.db.query(InventoryAlert).filter_by(
                        inventory_level_id=inv.id,
                        alert_type=alert['alert_type'],
                        is_resolved=False
                    ).first()

                    if not existing:
                        alert_record = InventoryAlert(
                            inventory_level_id=inv.id,
                            alert_type=alert['alert_type'],
                            severity=alert['severity'],
                            message=alert['message'],
                            current_value=alert['current_value'],
                            threshold_value=alert['threshold_value']
                        )
                        self.db.add(alert_record)

            self.db.commit()
            logger.info(f"Generated {len(alerts)} inventory alerts")
            return alerts

        except Exception as e:
            logger.error(f"Alert generation error: {str(e)}")
            return []


def get_inventory_service() -> InventoryService:
    """Dependency: Get inventory service instance"""
    from database import db_session
    return InventoryService(db_session)
