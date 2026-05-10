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
from models import Store, Product, InventoryLevel, Forecast, Recommendation, RecommendationType

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
                    rec = Recommendation(
                        store_id=level.store_id,
                        product_id=level.product_id,
                        rec_type=rec_type,
                        priority=priority,
                        title=title,
                        description=message,
                        rationale=f"Based on {forecast.model_type.value} forecast (MAPE: {forecast.mape:.2f}%)",
                        confidence_score=0.85,  # TODO: derive from model metrics
                        expected_impact=f"Prevent stockout in {level.lead_time_days} days" if rec_type == RecommendationType.INCREASE_STOCK else f"Free up {excess_qty:.0f} units of capital",
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


def get_recommendation_engine() -> RecommendationEngine:
    from database import db_session
    return RecommendationEngine(db_session)
