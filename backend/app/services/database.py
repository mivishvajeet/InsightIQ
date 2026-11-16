"""
Database Connectivity & Session Management for InsightIQ.

Provides:
- Admin engine for ingestion, DDL, and ETL operations.
- Read-only engine for AI Agent SQL queries with safety timeouts.
- Healthcheck and connection testing utilities.
"""

import os
from contextlib import contextmanager
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

# Admin credentials
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "insightiq")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

# Read-only credentials for SQL tool
POSTGRES_READONLY_USER = os.getenv("POSTGRES_READONLY_USER", "insightiq_readonly")
POSTGRES_READONLY_PASSWORD = os.getenv("POSTGRES_READONLY_PASSWORD", "readonly_secret")

# Safety limits
SQL_QUERY_TIMEOUT_SECONDS = int(os.getenv("SQL_QUERY_TIMEOUT_SECONDS", "10"))
SQL_MAX_ROWS_RETURNED = int(os.getenv("SQL_MAX_ROWS_RETURNED", "500"))


def get_admin_url() -> str:
    return f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


def get_readonly_url() -> str:
    return f"postgresql+psycopg2://{POSTGRES_READONLY_USER}:{POSTGRES_READONLY_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"


# Admin Engine (for setup, schema migrations, and ETL)
admin_engine: Engine = create_engine(
    get_admin_url(),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

# Read-Only Engine (for AI Agent query execution)
readonly_engine: Engine = create_engine(
    get_readonly_url(),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    execution_options={
        "isolation_level": "AUTOCOMMIT",
        "postgresql_readonly": True,
    },
    connect_args={
        "options": f"-c statement_timeout={SQL_QUERY_TIMEOUT_SECONDS * 1000} -c default_transaction_read_only=on"
    },
)

AdminSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=admin_engine)
ReadonlySessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=readonly_engine)


@contextmanager
def get_admin_db() -> Generator[Session, None, None]:
    """Context manager for admin database sessions."""
    db = AdminSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_readonly_db() -> Generator[Session, None, None]:
    """Context manager for read-only agent queries."""
    db = ReadonlySessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connections() -> dict[str, bool]:
    """Tests both admin and read-only connections."""
    results = {}
    try:
        with admin_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            results["admin"] = True
    except Exception as e:
        results["admin"] = False
        results["admin_error"] = str(e)

    try:
        with readonly_engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
            results["readonly"] = True
    except Exception as e:
        results["readonly"] = False
        results["readonly_error"] = str(e)

    return results
