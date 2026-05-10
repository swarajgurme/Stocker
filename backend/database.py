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
engine = create_engine(
    DATABASE_URL,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_pre_ping=True,  # Verify connections before using
    echo=os.getenv("SQL_ECHO", "False").lower() == "true"  # Log SQL queries (dev only)
)

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
def migrate_csv_to_db(csv_path: str):
    """
    Migrate existing CSV data to PostgreSQL database.
    Called once during initial setup.

    Args:
        csv_path: Path to backend/data.csv
    """
    import pandas as pd
    from models import Store, Product, Sale

    logger.info(f"Starting CSV migration from {csv_path}")

    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records from CSV")

        with get_db_session() as db:
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

                existing_product = db.query(Product).filter_by(name=product_name).first()
                if not existing_product:
                    product = Product(
                        product_code=f"P{i+1:03d}",
                        name=product_name,
                        category=category,
                        sku=f"SKU-{product_name.replace(' ', '-').upper()}",
                        is_active=True
                    )
                    db.add(product)
                    db.flush()
                    product_mapping[i] = product.id
                else:
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
