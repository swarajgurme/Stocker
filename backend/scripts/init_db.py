#!/usr/bin/env python3
"""
Database Migration & Initialization Script
Migrates CSV data to PostgreSQL and creates admin user
"""

import sys
import os
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from database import init_db, migrate_csv_to_db, check_db_connection
from models import User, UserRole
from auth_service import hash_password
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run full initialization"""
    logger.info("=" * 60)
    logger.info("Stocker Database Initialization")
    logger.info("=" * 60)

    # 1. Check DB connection
    logger.info("Checking database connection...")
    if not check_db_connection():
        logger.error("Cannot connect to database. Check DATABASE_URL in .env")
        sys.exit(1)

    # 2. Schema (Alembic when available)
    logger.info("Applying database schema...")
    if os.getenv("SKIP_ALEMBIC", "").lower() == "true":
        init_db()
    else:
        ini = backend_dir / "alembic.ini"
        if ini.is_file():
            from alembic.config import Config
            from alembic import command

            cfg = Config(str(ini))
            command.upgrade(cfg, "head")
            logger.info("Alembic migrations applied")
        else:
            init_db()
            logger.info("Tables created via SQLAlchemy (no alembic.ini)")

    # 3. Migrate CSV data
    csv_rel = os.environ.get("STOCKER_CSV_PATH", "data.csv")
    csv_path = Path(csv_rel) if Path(csv_rel).is_absolute() else backend_dir / csv_rel
    if csv_path.exists():
        logger.info(f"Migrating CSV data from {csv_path}...")
        success = migrate_csv_to_db(str(csv_path))
        if success:
            logger.info("CSV migration completed")
        else:
            logger.error("CSV migration failed")
            sys.exit(1)
    else:
        logger.warning("data.csv not found, skipping CSV migration")

    from database import get_db_session

    with get_db_session() as db:
        admin_email = os.environ.get("STOCKER_BOOTSTRAP_ADMIN_EMAIL", "admin@stocker.com")
        bootstrap_pw = os.environ.get("STOCKER_BOOTSTRAP_ADMIN_PASSWORD")
        if not bootstrap_pw:
            logger.error(
                "Set STOCKER_BOOTSTRAP_ADMIN_PASSWORD in the environment before init."
            )
            sys.exit(1)

        existing = db.query(User).filter_by(email=admin_email).first()

        if not existing:
            admin = User(
                email=admin_email,
                password_hash=hash_password(bootstrap_pw),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            logger.info("Admin user created for %s", admin_email)
        else:
            logger.info("Admin user already exists: %s", admin_email)

    logger.info("=" * 60)
    logger.info("Initialization Complete!")
    logger.info("")
    logger.info("Bootstrap admin email: %s", os.environ.get("STOCKER_BOOTSTRAP_ADMIN_EMAIL", "admin@stocker.com"))
    logger.info("")
    logger.info("Start the server with: python server.py")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
