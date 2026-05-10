#!/usr/bin/env python3
"""
Database Migration & Initialization Script
Migrates CSV data to PostgreSQL and creates admin user
"""

import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent / 'backend'
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

    # 2. Create tables
    logger.info("Creating database tables...")
    init_db()

    # 3. Migrate CSV data
    csv_path = backend_dir / 'data.csv'
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

    # 4. Create admin user
    from database import db_session

    with db_session() as db:
        admin_email = "admin@stocker.com"
        existing = db.query(User).filter_by(email=admin_email).first()

        if not existing:
            admin = User(
                email=admin_email,
                password_hash=hash_password("Admin@123"),
                full_name="System Administrator",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            db.commit()
            logger.info(f"Admin user created: {admin_email} / Admin@123")
        else:
            logger.info(f"Admin user already exists: {admin_email}")

    logger.info("=" * 60)
    logger.info("Initialization Complete!")
    logger.info("")
    logger.info("You can now log in with:")
    logger.info("  Email: admin@stocker.com")
    logger.info("  Password: Admin@123")
    logger.info("")
    logger.info("Start the server with: python server.py")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
