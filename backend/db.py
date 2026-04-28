"""
Database connection pool — psycopg2 + context manager.
All SQL lives here or in routers. The dashboard never touches the DB.
"""
import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
import psycopg2.pool
from dotenv import load_dotenv

load_dotenv()

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            dbname=os.getenv("DB_NAME", "smart_city"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )
    return _pool


@contextmanager
def get_conn() -> Generator:
    """Yield a connection from the pool, return it on exit."""
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def fetch_all(sql: str, params=None) -> list[dict]:
    """Run a SELECT, return list of dicts."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


def fetch_one(sql: str, params=None) -> dict | None:
    """Run a SELECT, return first row as dict or None."""
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params=None) -> None:
    """Run INSERT / UPDATE / DELETE."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())


def ping() -> str:
    """Return DB version string, or raise on failure."""
    row = fetch_one("SELECT version()")
    return row["version"]
