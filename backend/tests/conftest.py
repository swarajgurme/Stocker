import os

# Ensure test database before any backend modules load
os.environ["FLASK_ENV"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SKIP_ALEMBIC"] = "true"
