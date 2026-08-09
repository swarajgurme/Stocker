"""
Analytics Service
Cluster analysis, trend detection, KPI calculations
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func

from database import get_db_session
from models import Store, Product, Sale, Cluster

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for analytics and statistical analysis"""

    def __init__(self, db_session):
        self.db = db_session

    def run_cluster_analysis(
        self,
        analysis_date: Optional[datetime] = None,
        n_clusters: Optional[int] = None
    ) -> Dict:
        """
        Perform K-means clustering on category-store sales data

        Args:
            analysis_date: Date to analyze (defaults to latest)
            n_clusters: Fixed cluster count (auto-detect if None)

        Returns:
            Dict with cluster assignments and statistics
        """
        try:
            if analysis_date is None:
                max_date = self.db.query(func.max(Sale.sale_date)).scalar()
                analysis_date = max_date or datetime.utcnow().date()

            # Get aggregated sales by category and store
            # Using latest 90 days of data
            cutoff = analysis_date - timedelta(days=90)

            query = self.db.query(
                Product.category,
                Sale.store_id,
                func.sum(Sale.ewma).label('total_ewma')
            ).join(Product, Sale.product_id == Product.id)\
             .filter(Sale.sale_date >= cutoff)\
             .group_by(Product.category, Sale.store_id)

            results = query.all()

            if not results:
                raise ValueError("No sales data available for clustering")

            # Create DataFrame
            df = pd.DataFrame([{
                'category': r.category,
                'store_id': r.store_id,
                'sales_ewma': float(r.total_ewma)
            } for r in results])

            # Encode categories to numeric for clustering
            from sklearn.preprocessing import LabelEncoder
            cat_encoder = LabelEncoder()
            store_encoder = LabelEncoder()

            df['category_encoded'] = cat_encoder.fit_transform(df['category'])
            df['store_encoded'] = store_encoder.fit_transform(df['store_id'].astype(str))

            X = df[['sales_ewma', 'category_encoded', 'store_encoded']].values

            # Standardize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Determine optimal k using elbow method if not specified
            if n_clusters is None:
                inertias = []
                max_k = min(10, len(X_scaled))
                for k in range(1, max_k + 1):
                    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
                    kmeans.fit(X_scaled)
                    inertias.append(kmeans.inertia_)

                # Find elbow (largest gap)
                if len(inertias) >= 2:
                    diffs = np.diff(inertias)
                    optimal_k = np.argmax(diffs) + 2
                    optimal_k = min(optimal_k, len(X_scaled) // 2)  # Reasonable upper bound
                else:
                    optimal_k = 1
            else:
                optimal_k = n_clusters

            # Final clustering
            kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
            df['cluster_label'] = kmeans.fit_predict(X_scaled)

            # Save to database
            # First, clear old clusters for this date
            old_clusters = self.db.query(Cluster).filter_by(
                cluster_analysis_date=analysis_date
            ).all()
            for c in old_clusters:
                self.db.delete(c)

            for _, row in df.iterrows():
                cluster = Cluster(
                    store_id=int(row['store_id']),
                    category=row['category'],
                    sales_ewma=row['sales_ewma'],
                    cluster_label=int(row['cluster_label']),
                    cluster_analysis_date=analysis_date
                )
                self.db.add(cluster)

            self.db.commit()

            logger.info(f"Clustering completed: {len(df)} records, {optimal_k} clusters")

            return {
                "total_records": len(df),
                "optimal_clusters": optimal_k,
                "assignments": df.to_dict('records')
            }

        except Exception as e:
            logger.error(f"Cluster analysis error: {str(e)}")
            raise

    def get_sales_trend(
        self,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        days: int = 30
    ) -> List[Dict]:
        """
        Get sales trend over time

        Args:
            store_id: Filter by store (optional)
            product_id: Filter by product (optional)
            days: Number of days to look back

        Returns:
            List of {date, revenue, quantity} dictionaries
        """
        from sqlalchemy import func
        cutoff = datetime.utcnow().date() - timedelta(days=days)

        query = self.db.query(
            Sale.sale_date,
            func.sum(Sale.revenue).label('revenue'),
            func.sum(Sale.quantity).label('quantity')
        ).filter(Sale.sale_date >= cutoff)

        if store_id:
            query = query.filter(Sale.store_id == store_id)
        if product_id:
            query = query.filter(Sale.product_id == product_id)

        results = query.group_by(Sale.sale_date)\
            .order_by(Sale.sale_date).all()

        return [{
            "date": row.sale_date.isoformat(),
            "revenue": round(float(row.revenue or 0), 2),
            "quantity": int(row.quantity or 0)
        } for row in results]

    def get_top_products(
        self,
        limit: int = 10,
        period_days: int = 30,
        store_id: Optional[int] = None
    ) -> List[Dict]:
        """Get top-selling products"""
        cutoff = datetime.utcnow().date() - timedelta(days=period_days)

        query = self.db.query(
            Product.name,
            Product.category,
            func.sum(Sale.revenue).label('revenue'),
            func.sum(Sale.quantity).label('quantity')
        ).join(Sale, Product.id == Sale.product_id)\
         .filter(Sale.sale_date >= cutoff)

        if store_id:
            query = query.filter(Sale.store_id == store_id)

        results = query.group_by(Product.id)\
            .order_by(func.sum(Sale.revenue).desc())\
            .limit(limit).all()

        return [{
            "product_name": row.name,
            "category": row.category,
            "revenue": round(float(row.revenue or 0), 2),
            "units": int(row.quantity or 0)
        } for row in results]

    def get_forecast_accuracy_by_product(
        self,
        limit: int = 10,
        store_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Get forecast accuracy metrics per product

        Returns products with best/worst MAPE scores
        """
        from models import Forecast, ForecastValue

        # Get latest forecasts
        subq = self.db.query(
            Forecast.product_id,
            func.max(Forecast.created_at).label('latest')
        ).filter(Forecast.status == 'completed')\
         .group_by(Forecast.product_id).subquery()

        forecasts = self.db.query(Forecast).join(
            subq,
            and_(
                Forecast.product_id == subq.c.product_id,
                Forecast.created_at == subq.c.latest
            )
        ).all()

        results = []
        for f in forecasts:
            if f.mape is not None:
                product = self.db.query(Product).get(f.product_id)
                if product:
                    results.append({
                        "product_name": product.name,
                        "category": product.category,
                        "mape": round(f.mape, 2),
                        "rmse": round(f.rmse, 2) if f.rmse else None,
                        "forecast_date": f.created_at.isoformat()
                    })

        results.sort(key=lambda x: x['mape'])
        return results[:limit]

    def generate_stock_transfers(self) -> List[Dict]:
        """
        Evaluate store inventory across the network to generate intelligent stock transfer directives.
        FR-P1: If Store A current stock < ROP and Store B stock > 2x ROP, generate transfer recommendation.
        """
        from models import InventoryLevel, Store, Product

        inventory_records = self.db.query(InventoryLevel).all()
        product_stocks = {}
        for inv in inventory_records:
            if inv.product_id not in product_stocks:
                product_stocks[inv.product_id] = []
            product_stocks[inv.product_id].append(inv)

        transfers = []
        for product_id, inv_list in product_stocks.items():
            product = self.db.query(Product).get(product_id)
            if not product:
                continue

            low_stores = [inv for inv in inv_list if inv.current_stock < inv.reorder_point]
            surplus_stores = [inv for inv in inv_list if inv.current_stock > (inv.reorder_point * 1.8)]

            for low_inv in low_stores:
                store_a = self.db.query(Store).get(low_inv.store_id)
                needed = int(round(low_inv.reorder_point * 1.5 - low_inv.current_stock))
                needed = max(10, needed)

                for surplus_inv in surplus_stores:
                    if surplus_inv.store_id == low_inv.store_id:
                        continue
                    store_b = self.db.query(Store).get(surplus_inv.store_id)
                    avail = int(round(surplus_inv.current_stock - surplus_inv.reorder_point * 1.2))
                    if avail > 5:
                        qty = min(needed, avail)
                        store_a_code = store_a.store_code if store_a else f"S{low_inv.store_id:03d}"
                        store_a_name = store_a.name if store_a else f"Store {low_inv.store_id}"
                        store_b_code = store_b.store_code if store_b else f"S{surplus_inv.store_id:03d}"
                        store_b_name = store_b.name if store_b else f"Store {surplus_inv.store_id}"

                        transfers.append({
                            "id": f"TR-{product.id}-{surplus_inv.store_id}-{low_inv.store_id}",
                            "product_id": product.id,
                            "product_name": product.name,
                            "sku": product.sku,
                            "source_store_id": store_b_code,
                            "source_store_name": store_b_name,
                            "target_store_id": store_a_code,
                            "target_store_name": store_a_name,
                            "quantity": qty,
                            "directive": f"Transfer {qty} units of {product.name} from {store_b_name} to {store_a_name} instead of placing a new order.",
                            "urgency": "High" if low_inv.current_stock < low_inv.safety_stock else "Medium"
                        })
                        needed -= qty
                        if needed <= 0:
                            break

        return transfers


def get_analytics_service() -> AnalyticsService:
    from database import db_session
    return AnalyticsService(db_session)
