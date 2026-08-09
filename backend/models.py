"""
Database models for Stocker Enterprise Platform
SQLAlchemy ORM models defining all database entities
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime, Boolean,
    ForeignKey, Enum, Text, JSON, Index
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


# ============= ENUM TYPES =============
class UserRole(enum.Enum):
    ADMIN = "admin"
    BUSINESS_ANALYST = "business_analyst"
    SUPPLY_CHAIN_PLANNER = "supply_chain_planner"
    STORE_MANAGER = "store_manager"
    EXECUTIVE = "executive"


class AlertType(enum.Enum):
    LOW_STOCK = "low_stock"
    OVERSTOCK = "overstock"
    UNDERSTOCK_RISK = "understock_risk"
    FORECAST_ANOMALY = "forecast_anomaly"
    DEMAND_SPIKE = "demand_spike"
    DEMAND_COLLAPSE = "demand_collapse"
    SYSTEM_ERROR = "system_error"


class AlertSeverity(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ForecastModelType(enum.Enum):
    PROPHET = "prophet"
    ARIMA = "arima"
    XGBOOST = "xgboost"
    LSTM = "lstm"


class RecommendationType(enum.Enum):
    INCREASE_STOCK = "increase_stock"
    REDUCE_INVENTORY = "reduce_inventory"
    PROCUREMENT = "procurement"
    SEASONAL_PLANNING = "seasonal_planning"


class AnomalyType(enum.Enum):
    DEMAND_SPIKE = "demand_spike"
    DEMAND_COLLAPSE = "demand_collapse"
    SEASONAL_ABNORMALITY = "seasonal_abnormality"
    INVENTORY_INCONSISTENCY = "inventory_inconsistency"
    TRANSACTION_OUTLIER = "transaction_outlier"


class ReportFormat(enum.Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"


# ============= USER & AUTH =============
class User(Base):
    """User account with role-based access control"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole), nullable=False, default=UserRole.BUSINESS_ANALYST)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    scheduled_reports = relationship("ScheduledReport", back_populates="created_by_user")

    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_role', 'role'),
    )


# ============= STORE & PRODUCT MASTER DATA =============
class Supplier(Base):
    """Supplier master data for procurement timing and lead times"""
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    lead_time_days = Column(Integer, nullable=False, default=7)
    contact_email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    products = relationship("Product", back_populates="supplier")

    __table_args__ = (
        Index('idx_supplier_name', 'name'),
    )


class Store(Base):
    """Store/master data for retail locations"""
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_code = Column(String(10), unique=True, nullable=False)  # S001-S005
    name = Column(String(255))
    region = Column(String(50), nullable=False, index=True)
    manager_name = Column(String(255))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(100))
    country = Column(String(100), default="India")
    phone = Column(String(20))
    email = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sales = relationship("Sale", back_populates="store", cascade="all, delete-orphan")
    inventory_levels = relationship("InventoryLevel", back_populates="store", cascade="all, delete-orphan")
    # Access alerts via store.inventory_levels[x].alerts
    cluster_assignments = relationship("Cluster", back_populates="store", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_store_code', 'store_code'),
        Index('idx_store_region', 'region'),
    )


class Product(Base):
    """Product master data"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    sku = Column(String(100), unique=True)
    brand = Column(String(100))
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    unit_of_measure = Column(String(20), default="unit")
    unit_cost = Column(Float)
    selling_price = Column(Float)
    ordering_cost = Column(Float, default=50.0)  # S: Cost per purchase order
    holding_cost_per_unit = Column(Float, default=5.0)  # H: Annual holding cost per unit
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    sales = relationship("Sale", back_populates="product", cascade="all, delete-orphan")
    inventory_levels = relationship("InventoryLevel", back_populates="product", cascade="all, delete-orphan")
    # Access alerts via product.inventory_levels[x].alerts
    cluster_assignments = relationship("Cluster", back_populates="product", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_product_name', 'name'),
        Index('idx_product_category', 'category'),
        Index('idx_product_sku', 'sku'),
        Index('idx_product_supplier', 'supplier_id'),
    )


# ============= HISTORICAL SALES DATA =============
class Sale(Base):
    """Historical sales records (time-series data)"""
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    sale_date = Column(Date, nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    quarter = Column(Integer, nullable=False)
    day_of_week = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    revenue = Column(Float, nullable=False)
    ewma = Column(Float, nullable=False)  # Exponentially Weighted Moving Average
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="sales")
    product = relationship("Product", back_populates="sales")

    __table_args__ = (
        Index('idx_sale_date', 'sale_date'),
        Index('idx_sale_store_product', 'store_id', 'product_id'),
        Index('idx_sale_composite', 'store_id', 'product_id', 'sale_date'),
    )


# ============= FORECASTING =============
class Forecast(Base):
    """Forecast metadata - one forecast batch"""
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    model_type = Column(Enum(ForecastModelType), nullable=False, index=True)
    horizon_days = Column(Integer, nullable=False, default=365)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(String(50), default="pending", index=True)  # pending, running, completed, failed
    rmse = Column(Float)  # Model accuracy metrics
    mae = Column(Float)
    mape = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)

    # Relationships
    store = relationship("Store")
    product = relationship("Product")
    values = relationship("ForecastValue", back_populates="forecast", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_forecast_store_product', 'store_id', 'product_id'),
        Index('idx_forecast_status', 'status'),
        Index('idx_forecast_created', 'created_at'),
    )


class ForecastValue(Base):
    """Individual forecast predictions with confidence intervals"""
    __tablename__ = "forecast_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    forecast_id = Column(Integer, ForeignKey("forecasts.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    predicted = Column(Float, nullable=False)
    lower_bound = Column(Float, nullable=False)  # 95% confidence interval lower
    upper_bound = Column(Float, nullable=False)  # 95% confidence interval upper
    actual = Column(Float, nullable=True)  # Filled in after actuals are known
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    forecast = relationship("Forecast", back_populates="values")

    __table_args__ = (
        Index('idx_forecast_value_date', 'date'),
        Index('idx_forecast_value_composite', 'forecast_id', 'date'),
    )


# ============= INVENTORY MANAGEMENT =============
class InventoryLevel(Base):
    """Current inventory levels and optimization parameters"""
    __tablename__ = "inventory_levels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    current_stock = Column(Integer, nullable=False, default=0)
    safety_stock = Column(Float, nullable=False, default=0.0)
    reorder_point = Column(Float, nullable=False, default=0.0)  # ROP = (Daily Demand × Lead Time) + Safety Stock
    lead_time_days = Column(Integer, nullable=False, default=7)  # Supplier lead time
    last_count_date = Column(Date)
    last_calculated = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="inventory_levels")
    product = relationship("Product", back_populates="inventory_levels")
    alerts = relationship("InventoryAlert", back_populates="inventory_level", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_inventory_store_product', 'store_id', 'product_id', unique=True),
        Index('idx_inventory_last_calc', 'last_calculated'),
    )


class InventoryAlert(Base):
    """Inventory-related alerts (low stock, overstock, etc.)"""
    __tablename__ = "inventory_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    inventory_level_id = Column(Integer, ForeignKey("inventory_levels.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM, index=True)
    message = Column(Text, nullable=False)
    current_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    is_resolved = Column(Boolean, default=False, index=True)
    resolved_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    inventory_level = relationship("InventoryLevel", back_populates="alerts")

    __table_args__ = (
        Index('idx_alert_type_severity', 'alert_type', 'severity'),
        Index('idx_alert_resolved', 'is_resolved', 'created_at'),
    )


# ============= CLUSTER ANALYSIS =============
class Cluster(Base):
    """Cluster analysis results for category-store segmentation"""
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True)  # Nullable for category-level
    category = Column(String(100), nullable=False, index=True)
    sales_ewma = Column(Float, nullable=False)
    cluster_label = Column(Integer, nullable=False, index=True)
    cluster_analysis_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    store = relationship("Store", back_populates="cluster_assignments")
    product = relationship("Product", back_populates="cluster_assignments")

    __table_args__ = (
        Index('idx_cluster_label_date', 'cluster_label', 'cluster_analysis_date'),
        Index('idx_cluster_store_category', 'store_id', 'category'),
    )


# ============= ANOMALY DETECTION =============
class Anomaly(Base):
    """Detected anomalies in sales or inventory patterns"""
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    anomaly_type = Column(Enum(AnomalyType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM, index=True)
    score = Column(Float, nullable=False)  # Anomaly score (0-1 or z-score)
    description = Column(Text, nullable=False)
    detection_date = Column(Date, nullable=False, index=True)
    is_reviewed = Column(Boolean, default=False, index=True)
    is_false_positive = Column(Boolean, default=False)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_anomaly_type_severity', 'anomaly_type', 'severity'),
        Index('idx_anomaly_date', 'detection_date'),
    )


# ============= RECOMMENDATIONS =============
class Recommendation(Base):
    """AI-generated recommendations for inventory/forecasting decisions"""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=True, index=True)
    rec_type = Column(Enum(RecommendationType), nullable=False, index=True)
    priority = Column(Integer, default=3, index=True)  # 1=critical, 5=low
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    rationale = Column(Text)  # SHAP/explanations
    confidence_score = Column(Float, nullable=False)  # Model confidence (0-1)
    expected_impact = Column(Text)  # JSON or text describing expected benefit
    is_acted = Column(Boolean, default=False, index=True)
    acted_at = Column(DateTime)
    expires_at = Column(DateTime, index=True)  # Recommendations have shelf life
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    store = relationship("Store")
    product = relationship("Product")

    __table_args__ = (
        Index('idx_rec_type_priority', 'rec_type', 'priority'),
        Index('idx_rec_created_expires', 'created_at', 'expires_at'),
    )


# ============= AUDIT LOGGING =============
class AuditLog(Base):
    """Immutable audit trail of all user actions"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # login, forecast_view, report_export, etc.
    resource_type = Column(String(50), nullable=False)  # forecast, inventory, user, etc.
    resource_id = Column(String(100), nullable=True)  # ID of affected resource
    details = Column(JSON, nullable=True)  # Additional metadata
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action'),
        Index('idx_audit_created', 'created_at'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
    )


# ============= REPORTING =============
class ScheduledReport(Base):
    """Scheduled report generation configuration"""
    __tablename__ = "scheduled_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    report_type = Column(String(100), nullable=False)  # forecast, inventory, cluster, executive
    format = Column(Enum(ReportFormat), nullable=False, default=ReportFormat.PDF)
    frequency = Column(String(50), nullable=False)  # daily, weekly, monthly
    cron_expression = Column(String(100))
    parameters = Column(JSON)  # Filters, store_ids, etc.
    recipients = Column(JSON, nullable=False)  # List of email addresses
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_by_user = relationship("User", back_populates="scheduled_reports")
    report_outputs = relationship("ReportOutput", back_populates="scheduled_report", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_scheduled_report_active', 'is_active', 'next_run'),
    )


class ReportOutput(Base):
    """Generated report output files"""
    __tablename__ = "report_outputs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scheduled_report_id = Column(Integer, ForeignKey("scheduled_reports.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)  # S3 or local path
    file_size = Column(Integer)
    format = Column(Enum(ReportFormat), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    downloaded_at = Column(DateTime)
    download_count = Column(Integer, default=0)

    # Relationships
    scheduled_report = relationship("ScheduledReport", back_populates="report_outputs")

    __table_args__ = (
        Index('idx_report_output_generated', 'generated_at'),
    )


# ============= MODEL TRACKING (MLflow replacement) =============
class ModelVersion(Base):
    """Track ML model versions and performance"""
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_type = Column(Enum(ForecastModelType), nullable=False, index=True)
    version = Column(String(50), nullable=False)  # Semantic version or timestamp
    training_date = Column(DateTime, default=datetime.utcnow, index=True)
    training_data_start = Column(Date, nullable=False)
    training_data_end = Column(Date, nullable=False)
    rmse = Column(Float)
    mae = Column(Float)
    mape = Column(Float)
    is_active = Column(Boolean, default=True, index=True)
    hyperparameters = Column(JSON)
    feature_importance = Column(JSON)  # SHAP values or feature weights
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_model_version_active', 'model_type', 'is_active'),
    )
