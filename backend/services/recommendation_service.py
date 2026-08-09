"""
Recommendation Engine Service
AI-driven recommendations for inventory and procurement
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import numpy as np

from database import get_db_session
from models import (
    Store,
    Product,
    InventoryLevel,
    Forecast,
    ForecastValue,
    Recommendation,
    RecommendationType,
)

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Generates actionable recommendations based on forecasts and inventory"""

    def __init__(self, db_session):
        self.db = db_session

    def generate_stock_recommendations(
        self,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Generate stock level recommendations using forecast data

        Logic:
        1. Get latest forecast for each product/store
        2. Compare current stock vs reorder point
        3. Compare with future demand (next 30-90 days)
        4. Account for lead time

        Returns:
            List of recommendation dicts
        """
        recommendations = []

        with get_db_session() as db:
            # Get all inventory levels, optionally filtered
            query = db.query(InventoryLevel)
            if store_id:
                query = query.filter_by(store_id=store_id)
            if product_id:
                query = query.filter_by(product_id=product_id)

            levels = query.all()

            for level in levels:
                store = db.query(Store).get(level.store_id)
                product = db.query(Product).get(level.product_id)

                if not store or not product:
                    continue

                # Get latest forecast for this product/store
                forecast = db.query(Forecast).filter_by(
                    store_id=level.store_id,
                    product_id=level.product_id,
                    status='completed'
                ).order_by(Forecast.created_at.desc()).first()

                if not forecast:
                    continue  # No forecast available

                # Get forecast values for next 30 days
                cutoff = datetime.utcnow().date()
                forecast_values = db.query(ForecastValue).filter_by(
                    forecast_id=forecast.id
                ).filter(ForecastValue.date >= cutoff)\
                 .order_by(ForecastValue.date).limit(30).all()

                if not forecast_values:
                    continue

                # Calculate projected shortfall/surplus
                projected_demand = sum(fv.predicted for fv in forecast_values)
                current_stock = level.current_stock
                safety_stock = level.safety_stock

                # Lead time demand
                lead_time_demand = projected_demand * (level.lead_time_days / 30.0)

                # Decision logic
                if current_stock < safety_stock:
                    # Critical: immediate restock needed
                    recommended_qty = max(
                        safety_stock * 1.2 - current_stock,  # Replenish to 120% of safety
                        lead_time_demand * 1.1 - current_stock  # Plus lead time buffer
                    )
                    rec_type = RecommendationType.INCREASE_STOCK
                    priority = 1  # Critical
                    title = "Immediate Restock Required"
                    message = f"Stock below safety level ({current_stock} < {safety_stock:.0f}). Order at least {recommended_qty:.0f} units immediately."
                elif current_stock < level.reorder_point:
                    # Warning: approaching reorder point
                    recommended_qty = level.reorder_point - current_stock + safety_stock * 0.5
                    rec_type = RecommendationType.INCREASE_STOCK
                    priority = 2  # High
                    title = "Reorder Soon"
                    message = f"Stock approaching reorder point ({current_stock:.0f} of {level.reorder_point:.0f}). Consider ordering {recommended_qty:.0f} units."
                elif current_stock > projected_demand * 1.5:
                    # Overstock
                    excess_qty = current_stock - projected_demand * 1.2
                    rec_type = RecommendationType.REDUCE_INVENTORY
                    priority = 3  # Medium
                    title = "Reduce Inventory"
                    message = f"Excess stock detected ({current_stock:.0f} units for projected demand {projected_demand:.0f}). Consider promotions or returns of {excess_qty:.0f} units."
                else:
                    # Healthy - no action needed
                    continue

                # Save recommendation
                existing = db.query(Recommendation).filter_by(
                    store_id=level.store_id,
                    product_id=level.product_id,
                    rec_type=rec_type,
                    is_acted=False
                ).first()

                if not existing:
                    mape = float(forecast.mape) if forecast.mape is not None else 50.0
                    confidence = max(0.55, min(0.97, 1.0 - (mape / 100.0)))
                    exp_impact = (
                        f"Prevent stockout in {level.lead_time_days} days"
                        if rec_type == RecommendationType.INCREASE_STOCK
                        else f"Free up {excess_qty:.0f} units of capital"
                    )
                    rec = Recommendation(
                        store_id=level.store_id,
                        product_id=level.product_id,
                        rec_type=rec_type,
                        priority=priority,
                        title=title,
                        description=message,
                        rationale=f"Based on {forecast.model_type.value} forecast (MAPE: {mape:.2f}%)",
                        confidence_score=round(confidence, 3),
                        expected_impact=exp_impact,
                        expires_at=datetime.utcnow() + timedelta(days=7)
                    )
                    db.add(rec)
                    recommendations.append({
                        "store_id": store.store_code,
                        "product_name": product.name,
                        "type": rec_type.value,
                        "priority": priority,
                        "title": title,
                        "message": message,
                        "current_stock": current_stock,
                        "recommended_qty": round(recommended_qty, 0)
                    })

            db.commit()

        logger.info(f"Generated {len(recommendations)} stock recommendations")
        return recommendations

    def generate_procurement_recommendations(
        self,
        store_id: int,
        horizon_days: int = 90
    ) -> Dict:
        """
        Generate bulk procurement recommendations for a store

        Returns:
            {
                "store_id": "S001",
                "total_items": 20,
                "critical_items": 3,
                "recommendations": [
                    {"product": "Battery", "order_qty": 150, "urgency": "high"},
                    ...
                ]
            }
        """
        with get_db_session() as db:
            recs = db.query(Recommendation).filter_by(
                store_id=store_id,
                rec_type=RecommendationType.INCREASE_STOCK,
                is_acted=False
            ).order_by(Recommendation.priority.asc()).all()

            store = db.query(Store).get(store_id)

            result = {
                "store_id": store.store_code if store else str(store_id),
                "total_items": len(recs),
                "critical_items": sum(1 for r in recs if r.priority == 1),
                "recommendations": []
            }

            for r in recs:
                product = db.query(Product).get(r.product_id)
                if product:
                    result["recommendations"].append({
                        "product": product.name,
                        "category": product.category,
                        "order_qty": int(float(r.description.split()[-2])),  # Extract qty from message
                        "priority": r.priority,
                        "title": r.title,
                        "confidence": r.confidence_score
                    })

            return result

    def generate_procurement_cards(self, store_id: Optional[int] = None) -> List[Dict]:
        """
        FR-PR1, FR-PR2 & FR-F3: Actionable Procurement Cards with Order-By Date and Urgent Flags.
        """
        from sqlalchemy import and_, func
        from models import Supplier, Anomaly, AnomalyType, InventoryLevel, Product, Store, Sale
        from services.inventory_service import InventoryService

        with get_db_session() as db:
            inv_query = db.query(InventoryLevel)
            if store_id:
                inv_query = inv_query.filter_by(store_id=store_id)

            levels = inv_query.all()
            cards = []
            today = datetime.utcnow().date()
            inv_service = InventoryService(db)

            for level in levels:
                product = db.query(Product).get(level.product_id)
                store = db.query(Store).get(level.store_id)
                if not product or not store:
                    continue

                supplier = db.query(Supplier).get(product.supplier_id) if product.supplier_id else None
                supplier_name = supplier.name if supplier else "Apex Auto Logistics"
                lead_time_days = supplier.lead_time_days if supplier else (level.lead_time_days or 7)

                # Calculate EOQ
                eoq_info = inv_service.calculate_eoq(product.id)
                order_qty = eoq_info["eoq"]

                # Calculate average daily demand
                cutoff = today - timedelta(days=90)
                tot_sales = db.query(func.sum(Sale.quantity)).filter(
                    and_(Sale.store_id == level.store_id, Sale.product_id == level.product_id, Sale.sale_date >= cutoff)
                ).scalar() or 0
                avg_daily_demand = max(0.5, float(tot_sales) / 90.0)

                # Days until stock reaches 0
                days_until_breach = max(0.0, float(level.current_stock) / avg_daily_demand)
                target_breach_date = today + timedelta(days=int(days_until_breach))

                # Order by date = target breach date - lead time days
                order_by_date_obj = target_breach_date - timedelta(days=lead_time_days)
                if order_by_date_obj <= today or level.current_stock < level.reorder_point:
                    order_by_date_str = today.strftime("%Y-%m-%d")
                    status = "ORDER_NOW"
                else:
                    order_by_date_str = order_by_date_obj.strftime("%Y-%m-%d")
                    status = "PLANNED"

                # Check for demand spike anomaly
                anomaly = db.query(Anomaly).filter(
                    and_(
                        Anomaly.store_id == level.store_id,
                        Anomaly.product_id == level.product_id,
                        Anomaly.anomaly_type == AnomalyType.DEMAND_SPIKE,
                        Anomaly.is_reviewed == False
                    )
                ).first()

                urgent_review = (anomaly is not None) or (level.current_stock < level.safety_stock)

                if level.current_stock < level.reorder_point or urgent_review or status == "ORDER_NOW":
                    why = f"Current stock ({level.current_stock}) is below ROP ({level.reorder_point:.0f}). "
                    if urgent_review:
                        why += "Demand spike anomaly detected — Urgent Procurement Review required. "
                    why += f"Supplier lead time is {lead_time_days} days."

                    cards.append({
                        "id": f"PROC-{level.store_id}-{level.product_id}",
                        "product_id": product.id,
                        "product_name": product.name,
                        "sku": product.sku,
                        "category": product.category,
                        "store_id": store.store_code,
                        "store_name": store.name,
                        "supplier_id": supplier.id if supplier else None,
                        "supplier_name": supplier_name,
                        "lead_time_days": lead_time_days,
                        "current_stock": level.current_stock,
                        "reorder_point": round(level.reorder_point, 2),
                        "safety_stock": round(level.safety_stock, 2),
                        "order_quantity": order_qty,
                        "order_by_date": order_by_date_str,
                        "status": status,
                        "urgent_review_flag": urgent_review,
                        "urgent_review_status": "Urgent Procurement Review" if urgent_review else "Normal",
                        "reason": why,
                        "priority": 1 if urgent_review else (2 if level.current_stock < level.reorder_point else 3)
                    })

            cards.sort(key=lambda x: (x["priority"], x["order_by_date"]))
            return cards


def get_recommendation_engine() -> RecommendationEngine:
    from database import db_session
    return RecommendationEngine(db_session)
