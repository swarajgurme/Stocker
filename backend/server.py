"""
Main Entry Point
Stocker Enterprise AI Supply Chain Platform - Backend Server
"""

import os
import sys
import logging
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app import create_app
from database import init_db, migrate_csv_to_db
# ============= CONFIGURATION =============
# Set environment variables before importing app
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('FLASK_DEBUG', 'True')
os.environ.setdefault('FLASK_PORT', '5000')
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@localhost:5432/stocker_db')

# CSV data path
CSV_DATA_PATH = os.path.join(backend_dir, 'data.csv')

# ============= CREATE APPLICATION =============
app = create_app()
init_db()

# ============= INITIALIZE DATABASE =============
def initialize_database():
    """Initialize database and migrate CSV data on first request"""
    try:
        logger = logging.getLogger(__name__)

        # Create tables
        init_db()
        logger.info("Database tables created/verified")

        # Check if data already exists
        from database import db_session
        from models import Sale

        with db_session() as db:
            sale_count = db.query(Sale).count()
            if sale_count == 0:
                logger.info("No sales data found. Migrating from CSV...")
                success = migrate_csv_to_db(CSV_DATA_PATH)
                if success:
                    logger.info("CSV migration completed successfully")
                else:
                    logger.error("CSV migration failed")
            else:
                logger.info(f"Database already contains {sale_count} sales records")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Database initialization error: {str(e)}")


# ============= CLI COMMANDS =============
@app.cli.command('init-db')
def init_db_command():
    """Initialize database and migrate CSV data"""
    init_db()
    print("Database tables created")

    from database import db_session
    from models import Sale

    with db_session() as db:
        count = db.query(Sale).count()
        if count == 0:
            print("Migrating CSV data...")
            migrate_csv_to_db(CSV_DATA_PATH)
        else:
            print(f"Database already has {count} sales records")


@app.cli.command('reset-db')
def reset_db_command():
    """Drop and recreate all tables (WARNING: destructive)"""
    from database import engine, Base
    from models import Base

    confirm = input("This will delete all data. Are you sure? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted")
        return

    Base.metadata.drop_all(bind=engine)
    print("All tables dropped")

    init_db()
    print("Tables recreated")

    # Migrate CSV
    migrate_csv_to_db(CSV_DATA_PATH)
    print("CSV data migrated")


# ============= MAIN =============
if __name__ == '__main__':
    # Configure basic logging before app starts
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Get config
    flask_env = os.getenv('FLASK_ENV', 'development')
    flask_debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    flask_port = int(os.getenv('FLASK_PORT', 5000))
    flask_host = os.getenv('FLASK_HOST', '0.0.0.0')

    logger.info("=" * 60)
    logger.info("Stocker Enterprise AI Platform")
    logger.info(f"Environment: {flask_env}")
    logger.info(f"Debug: {flask_debug}")
    logger.info(f"Host: {flask_host}:{flask_port}")
    logger.info("=" * 60)

    # Initialize database (only in dev)
    if flask_env == 'development':
        try:
            with app.app_context():
                initialize_database()
        except Exception as e:
            logger.error(f"Database init error: {e}")

    # Run app
    app.run(host=flask_host, port=flask_port, debug=flask_debug)
