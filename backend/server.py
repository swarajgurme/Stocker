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
from database import init_db, migrate_csv_to_db, get_db_session
from auth_service import hash_password
from models import User, UserRole
# ============= CONFIGURATION =============
# Set environment variables before importing app
os.environ.setdefault('FLASK_ENV', 'development')
os.environ.setdefault('FLASK_DEBUG', 'True')
os.environ.setdefault('FLASK_PORT', '5000')
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@localhost:5432/stocker_db')

# CSV data path (override with STOCKER_CSV_PATH, relative names resolve under backend_dir)
_csv_env = os.environ.get("STOCKER_CSV_PATH", "data.csv")
CSV_DATA_PATH = (
    _csv_env if os.path.isabs(_csv_env) else os.path.join(backend_dir, _csv_env)
)

# ============= CREATE APPLICATION =============
def _ensure_schema():
    """Apply Alembic migrations when available; otherwise SQLAlchemy create_all."""
    log = logging.getLogger(__name__)
    if os.getenv("SKIP_ALEMBIC", "").lower() == "true":
        init_db()
        log.debug("Schema ensured via init_db (SKIP_ALEMBIC)")
        return
    ini_path = backend_dir / "alembic.ini"
    if not ini_path.is_file():
        init_db()
        log.warning("alembic.ini missing; schema ensured via init_db()")
        return
    try:
        from alembic.config import Config
        from alembic import command

        cfg = Config(str(ini_path))
        command.upgrade(cfg, "head")
        log.info("Schema migrated to Alembic head")
    except Exception as exc:
        log.warning("Alembic upgrade failed (%s); falling back to init_db()", exc)
        init_db()


app = create_app()
_ensure_schema()

# ============= INITIALIZE DATABASE =============
def initialize_database():
    """Initialize database and migrate CSV data on first request"""
    try:
        logger = logging.getLogger(__name__)

        from models import Sale

        with get_db_session() as db:
            bootstrap_pw = os.environ.get("STOCKER_BOOTSTRAP_ADMIN_PASSWORD")
            admin_email = os.environ.get(
                "STOCKER_BOOTSTRAP_ADMIN_EMAIL", "admin@stocker.com"
            )
            if bootstrap_pw:
                exists = db.query(User).filter_by(email=admin_email).first()
                if not exists:
                    db.add(
                        User(
                            email=admin_email,
                            password_hash=hash_password(bootstrap_pw),
                            full_name="System Administrator",
                            role=UserRole.ADMIN,
                            is_active=True,
                        )
                    )
                    logger.info(
                        "Created bootstrap administrator %s from environment credentials",
                        admin_email,
                    )
            else:
                logger.warning(
                    "STOCKER_BOOTSTRAP_ADMIN_PASSWORD not set — no admin autocreate"
                )

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
@app.cli.command("upgrade-db")
def upgrade_db_command():
    """Run Alembic migrations to head."""
    from alembic.config import Config
    from alembic import command

    ini_path = backend_dir / "alembic.ini"
    if not ini_path.is_file():
        print("alembic.ini not found")
        return
    cfg = Config(str(ini_path))
    command.upgrade(cfg, "head")
    print("Alembic upgrade complete")


@app.cli.command('init-db')
def init_db_command():
    """Initialize database and migrate CSV data"""
    init_db()
    print("Database tables created")

    from models import Sale

    with get_db_session() as db:
        count = db.query(Sale).count()
        if count == 0:
            print("Migrating CSV data...")
            migrate_csv_to_db(CSV_DATA_PATH)
        else:
            print(f"Database already has {count} sales records")


@app.cli.command('reset-db')
def reset_db_command():
    """Drop and recreate all tables (WARNING: destructive)"""
    from database import engine
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
    app.run(host=flask_host, port=flask_port, debug=flask_debug, use_reloader=False)
