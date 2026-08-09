"""
Database configuration and session management
SQLAlchemy engine, session factory, and utilities
"""

import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
import logging
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ============= DATABASE CONFIGURATION =============
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@localhost:5432/stocker_db"
)

# Connection pool settings
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 20))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", 30))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 1800))  # 30 minutes

# ============= ENGINE CREATION =============
def _is_sqlite(url: str) -> bool:
    return url.strip().lower().startswith("sqlite")


_SQLITE_ENGINE_KWARGS = dict(
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
)

_POSTGRES_ENGINE_KWARGS = dict(
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,
    echo=os.getenv("SQL_ECHO", "False").lower() == "true",
)

def _get_engine():
    url = DATABASE_URL
    if _is_sqlite(url):
        return create_engine(url, **_SQLITE_ENGINE_KWARGS)
    try:
        eng = create_engine(url, **_POSTGRES_ENGINE_KWARGS)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as exc:
        logger.warning(f"PostgreSQL connection failed ({exc}); falling back to SQLite stocker_demo.db")
        return create_engine("sqlite:///stocker_demo.db", **_SQLITE_ENGINE_KWARGS)

engine = _get_engine()

# ============= SESSION FACTORY =============
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Scoped session for thread-safety
db_session = scoped_session(SessionLocal)


# ============= DATABASE UTILITIES =============
@contextmanager
def get_db_session() -> Session:
    """
    Context manager for database sessions.
    Automatically handles rollback on exception and closes session.

    Usage:
        with get_db_session() as db:
            user = db.query(User).filter_by(id=1).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database error: {str(e)}")
        raise
    finally:
        session.close()


def init_db():
    """Initialize database tables"""
    from models import Base

    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise


def check_db_connection():
    """Test database connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False


def close_db_session():
    """Remove scoped session (for app teardown)"""
    db_session.remove()


# ============= MIGRATION UTILITIES =============
def _bootstrap_inventory_from_sales(db) -> None:
    """
    Create inventory_levels for each store-product with observed sales when missing.
    Derives deterministic stock levels from trailing demand proxy (supports demos).
    """
    from sqlalchemy import func
    from datetime import timedelta
    from models import InventoryLevel, Sale

    max_date = db.query(func.max(Sale.sale_date)).scalar()
    cutoff = (max_date - timedelta(days=365)) if max_date else (datetime.utcnow().date() - timedelta(days=365))
    rows = (
        db.query(
            Sale.store_id,
            Sale.product_id,
            func.sum(Sale.quantity).label("tq"),
            func.avg(Sale.ewma).label("avg_sig"),
        )
        .filter(Sale.sale_date >= cutoff)
        .group_by(Sale.store_id, Sale.product_id)
        .all()
    )

    for row in rows:
        exists = db.query(InventoryLevel).filter_by(
            store_id=row.store_id,
            product_id=row.product_id,
        ).first()
        if exists:
            continue
        qty = int(row.tq or 0)
        sig = float(row.avg_sig or 0)
        current = max(35, min(950, qty * 3 + int(sig % 200)))
        lvl = InventoryLevel(
            store_id=row.store_id,
            product_id=row.product_id,
            current_stock=current,
            safety_stock=max(25.0, sig * 0.05),
            reorder_point=max(40.0, sig * 0.12),
            lead_time_days=7,
            last_calculated=datetime.utcnow(),
        )
        db.add(lvl)
    logger.info("Inventory levels bootstrapped for store-product combinations")


def migrate_csv_to_db(csv_path: str):
    """
    Migrate existing CSV data to PostgreSQL database.
    Called once during initial setup.

    Args:
        csv_path: Path to backend/data.csv
    """
    import pandas as pd
    from models import Store, Product, Sale, Supplier

    logger.info(f"Starting CSV migration from {csv_path}")

    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records from CSV")

        with get_db_session() as db:
            # ============= MIGRATE SUPPLIERS =============
            suppliers_data = [
                {"name": "Apex Auto Logistics", "lead_time_days": 5, "contact_email": "orders@apexauto.com"},
                {"name": "Continental Components Ltd", "lead_time_days": 7, "contact_email": "supply@continental.com"},
                {"name": "Precision Dynamics", "lead_time_days": 10, "contact_email": "sales@precisiondyn.com"},
                {"name": "Metro Automotive Supply", "lead_time_days": 3, "contact_email": "orders@metrosupply.com"},
            ]
            supplier_ids = []
            for s_info in suppliers_data:
                existing_s = db.query(Supplier).filter_by(name=s_info["name"]).first()
                if not existing_s:
                    s_obj = Supplier(
                        name=s_info["name"],
                        lead_time_days=s_info["lead_time_days"],
                        contact_email=s_info["contact_email"],
                        is_active=True
                    )
                    db.add(s_obj)
                    db.flush()
                    supplier_ids.append(s_obj.id)
                else:
                    supplier_ids.append(existing_s.id)

            # ============= MIGRATE STORES =============
            store_mapping = {}
            for store_code in df['Store ID'].unique():
                store_id_encoded = store_code  # CSV has 0-4
                store_code_str = f"S{int(store_id_encoded)+1:03d}"  # Convert 0->S001, 1->S002

                existing_store = db.query(Store).filter_by(store_code=store_code_str).first()
                if not existing_store:
                    store = Store(
                        store_code=store_code_str,
                        name=f"Store {store_code_str}",
                        region=["East", "North", "South", "West"][int(store_id_encoded) % 4],
                        is_active=True
                    )
                    db.add(store)
                    db.flush()  # Get ID
                    store_mapping[store_id_encoded] = store.id
                else:
                    store_mapping[store_id_encoded] = existing_store.id

            logger.info(f"Migrated {len(store_mapping)} stores")

            # ============= MIGRATE PRODUCTS =============
            product_mapping = {}
            product_names = [
                "Air Filter", "Alternator", "Battery", "Brake Pad", "Coolant",
                "Disc Rotor", "Engine Oil", "Fans", "Fuse", "LED",
                "Radiator", "Rearview Mirror", "Resistors", "Sensor",
                "Sideview Mirror", "Spark Plugs", "Thermostat", "Water Pump",
                "Windshield", "Wires"
            ]
            categories = ["Accessories", "Breaks", "Cooling System", "Electrical", "Engine"]

            for i, product_name in enumerate(product_names):
                category = categories[i // 4] if i < 20 else "Misc"
                assigned_supplier_id = supplier_ids[i % len(supplier_ids)] if supplier_ids else None

                existing_product = db.query(Product).filter_by(name=product_name).first()
                if not existing_product:
                    product = Product(
                        product_code=f"P{i+1:03d}",
                        name=product_name,
                        category=category,
                        sku=f"SKU-{product_name.replace(' ', '-').upper()}",
                        supplier_id=assigned_supplier_id,
                        ordering_cost=float(40 + (i * 5) % 60),  # S: $40-$95 per PO
                        holding_cost_per_unit=float(2.5 + (i * 0.5) % 8.0),  # H: $2.5-$10.0 annual holding cost
                        is_active=True
                    )
                    db.add(product)
                    db.flush()
                    product_mapping[i] = product.id
                else:
                    # Update supplier and costs if missing
                    if not existing_product.supplier_id:
                        existing_product.supplier_id = assigned_supplier_id
                    if not existing_product.ordering_cost:
                        existing_product.ordering_cost = float(40 + (i * 5) % 60)
                    if not existing_product.holding_cost_per_unit:
                        existing_product.holding_cost_per_unit = float(2.5 + (i * 0.5) % 8.0)
                    product_mapping[i] = existing_product.id

            logger.info(f"Migrated {len(product_mapping)} products")

            # ============= MIGRATE SALES =============
            sales_created = 0
            for _, row in df.iterrows():
                store_id = store_mapping.get(row['Store ID'])
                product_id = product_mapping.get(row['Product Name'])

                if store_id and product_id:
                    # Check if sale already exists
                    existing = db.query(Sale).filter_by(
                        store_id=store_id,
                        product_id=product_id,
                        sale_date=pd.to_datetime(row['Date']).date()
                    ).first()

                    if not existing:
                        sale = Sale(
                            store_id=store_id,
                            product_id=product_id,
                            sale_date=pd.to_datetime(row['Date']).date(),
                            year=int(row['Year']),
                            quarter=int(row['Quarter']),
                            day_of_week=int(row['Day']),
                            quantity=1,  # Assuming 1 unit per record
                            revenue=float(row['EWMA']),  # Using EWMA as revenue proxy
                            ewma=float(row['EWMA'])
                        )
                        db.add(sale)
                        sales_created += 1

            logger.info(f"Migrated {sales_created} sales records")

            _bootstrap_inventory_from_sales(db)
            db.commit()

        logger.info("CSV migration completed successfully")
        return True

    except Exception as e:
        logger.error(f"CSV migration failed: {str(e)}")
        return False


# ============= SESSION MIDDLEWARE FOR FLASK =============
def setup_db_session(app):
    """
    Configure Flask app to use database sessions.
    Call this from server.py after creating Flask app.
    """
    from flask import g

    @app.before_request
    def create_db_session():
        """Create a new database session for each request"""
        g.db = SessionLocal()

    @app.teardown_request
    def close_db_session(error):
        """Close database session after request"""
        if hasattr(g, 'db'):
            g.db.close()

    logger.info("Database session middleware configured")
