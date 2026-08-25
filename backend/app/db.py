"""
db.py — Synchronous SQLAlchemy engine + connection helper.

Exposes:
  - engine        : SQLAlchemy Engine backed by psycopg2 (sync, for simple
                    one-shot scripts and route handlers that don't need async).
  - get_db_conn() : context manager that yields a raw Connection.

For async routes use get_async_session() from db_async.py (Phase 4).
"""
import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_raw_url = os.getenv("DATABASE_URL", "")
if _raw_url.startswith("postgres://"):
    _raw_url = _raw_url.replace("postgres://", "postgresql://", 1)

# psycopg2 dialect (sync) — used by recommend routes & chat retriever
engine = create_engine(_raw_url, pool_pre_ping=True, pool_size=5, max_overflow=10)


@contextmanager
def get_db_conn():
    """Yield a raw SQLAlchemy Connection, auto-committed on exit."""
    with engine.begin() as conn:
        yield conn
