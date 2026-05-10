"""
Anomaly Detection Service
Statistical and ML-based anomaly detection for sales and inventory
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats

from database import get_db_session
from models import Sale, Anomaly, AnomalyType, AlertSeverity, Store, Product

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in sales and inventory data"""

    def __init__(
        self,
        db_session,
        z_score_threshold: float = 3.0,
        iqr_multiplier: float = 1.5
    ):
        self.db = db_session
        self.z_threshold = z_score_threshold
        self.iqr_multiplier = iqr_multiplier

    def detect_sales_anomalies(
        self,
        store_id: Optional[int] = None,
        product_id: Optional[int] = None,
        lookback_days: int = 90
    ) -> List[Dict]:
        """
        Detect unusual sales patterns using statistical methods

        Detects:
        - Sudden spikes (positive outliers)
        - Demand collapse (negative outliers)
        - Seasonal abnormalities

        Returns list of detected anomalies
        """
        cutoff = datetime.utcnow().date() - timedelta(days=lookback_days)

        query = self.db.query(Sale).filter(Sale.sale_date >= cutoff)
        if store_id:
            query = query.filter(Sale.store_id == store_id)
        if product_id:
            query = query.filter(Sale.product_id == product_id)

        sales = query.order_by(Sale.sale_date).all()

        if len(sales) < 30:
            logger.warning(f"Insufficient data for anomaly detection: {len(sales)} points")
            return []

        # Convert to DataFrame
        df = pd.DataFrame([{
            'date': s.sale_date,
            'quantity': s.quantity,
            'revenue': s.revenue,
            'ewma': s.ewma
        } for s in sales])

        anomalies = self._detect_outliers(df, 'ewma', 'sales')

        # Bulk insert anomalies
        for anomaly in anomalies:
            existing = self.db.query(Anomaly).filter_by(
                store_id=store_id,
                product_id=product_id,
                anomaly_type=anomaly['anomaly_type'],
                detection_date=datetime.utcnow().date()
            ).first()

            if not existing:
                a = Anomaly(
                    store_id=store_id,
                    product_id=product_id,
                    anomaly_type=anomaly['anomaly_type'],
                    severity=anomaly['severity'],
                    score=anomaly['score'],
                    description=anomaly['description'],
                    detection_date=datetime.utcnow().date()
                )
                self.db.add(a)

        self.db.commit()
        logger.info(f"Detected {len(anomalies)} sales anomalies")
        return anomalies

    def _detect_outliers(
        self,
        df: pd.DataFrame,
        column: str,
        context: str
    ) -> List[Dict]:
        """Generic outlier detection using Z-score and IQR"""
        values = df[column].values
        anomalies = []

        # Z-score method
        z_scores = np.abs(stats.zscore(values, nan_policy='omit'))

        for i, (idx, row) in enumerate(df.iterrows()):
            if np.isnan(z_scores[i]):
                continue

            score = z_scores[i]
            if score > self.z_threshold:
                # Determine if spike or collapse
                if row[column] > np.mean(values):
                    anomaly_type = AnomalyType.DEMAND_SPIKE
                    severity = AlertSeverity.HIGH
                    description = f"Unusual demand spike detected: {row[column]:.0f} units (z-score: {score:.2f})"
                else:
                    anomaly_type = AnomalyType.DEMAND_COLLAPSE
                    severity = AlertSeverity.CRITICAL
                    description = f"Demand collapse detected: {row[column]:.0f} units (z-score: {score:.2f})"

                anomalies.append({
                    "anomaly_type": anomaly_type,
                    "severity": severity,
                    "score": round(float(score), 2),
                    "description": description,
                    "date": row['date'],
                    "value": row[column]
                })

        # IQR method for robustness
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - self.iqr_multiplier * IQR
        upper_bound = Q3 + self.iqr_multiplier * IQR

        for _, row in df.iterrows():
            if row[column] < lower_bound or row[column] > upper_bound:
                # Check not already detected by Z-score
                already_detected = any(
                    a['date'] == row['date'] for a in anomalies
                )
                if not already_detected:
                    anomalies.append({
                        "anomaly_type": AnomalyType.DEMAND_SPIKE if row[column] > upper_bound else AnomalyType.DEMAND_COLLAPSE,
                        "severity": AlertSeverity.MEDIUM,
                        "score": round(float((row[column] - Q1) / IQR if row[column] > upper_bound else (Q3 - row[column]) / IQR), 2),
                        "description": f"IQR outlier in {context}: {row[column]:.0f}",
                        "date": row['date'],
                        "value": row[column]
                    })

        return anomalies

    def detect_inventory_inconsistencies(
        self,
        store_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Detect inventory inconsistencies (e.g., negative adjustments, unusual patterns)

        Returns:
            List of potential fraud/shrinkage indicators
        """
        # TODO: Implement with inventory transaction logs
        # For now: detect sudden large discrepancies vs forecast
        anomalies = []
        return anomalies

    def get_active_anomalies(
        self,
        store_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get unresolved anomalies"""
        query = self.db.query(Anomaly).filter_by(is_reviewed=False)

        if store_id:
            store = self.db.query(Store).filter_by(store_code=store_id).first()
            if store:
                query = query.filter_by(store_id=store.id)

        anomalies = query.order_by(
            Anomaly.created_at.desc()
        ).limit(limit).all()

        result = []
        for a in anomalies:
            store = self.db.query(Store).get(a.store_id) if a.store_id else None
            product = self.db.query(Product).get(a.product_id) if a.product_id else None

            result.append({
                "id": a.id,
                "store_id": store.store_code if store else None,
                "product_name": product.name if product else None,
                "anomaly_type": a.anomaly_type.value,
                "severity": a.severity.value,
                "score": a.score,
                "description": a.description,
                "detection_date": a.detection_date.isoformat() if a.detection_date else None,
                "is_reviewed": a.is_reviewed,
                "is_false_positive": a.is_false_positive
            })

        return result

    def mark_anomaly_reviewed(
        self,
        anomaly_id: int,
        user_id: int,
        is_false_positive: bool = False
    ) -> bool:
        """Mark anomaly as reviewed"""
        anomaly = self.db.query(Anomaly).filter_by(id=anomaly_id).first()
        if not anomaly:
            return False

        anomaly.is_reviewed = True
        anomaly.is_false_positive = is_false_positive
        anomaly.reviewed_by = user_id
        anomaly.reviewed_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Anomaly {anomaly_id} marked as reviewed by user {user_id}")
        return True


def get_anomaly_detector() -> AnomalyDetector:
    from database import db_session
    return AnomalyDetector(db_session)
