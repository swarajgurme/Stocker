"""
Routes Package
All Flask blueprints
"""

from routes.auth import auth_bp
from routes.forecast import forecast_bp
from routes.inventory import inventory_bp
from routes.analytics import analytics_bp
from routes.anomaly import anomaly_bp
from routes.recommendation import recommendation_bp
from routes.report import report_bp

__all__ = [
    'auth_bp',
    'forecast_bp',
    'inventory_bp',
    'analytics_bp',
    'anomaly_bp',
    'recommendation_bp',
    'report_bp'
]
