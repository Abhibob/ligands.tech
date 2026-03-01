"""Database connection management. Graceful no-op when no DB configured."""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Generator

if TYPE_CHECKING:
    import psycopg2.extensions

logger = logging.getLogger(__name__)

_DB_URL_ENVVARS = ("BIND_DB_URL", "DATABASE_URL")


def get_db_url() -> str | None:
    """Read DB connection string from environment. Returns None if not configured."""
    for var in _DB_URL_ENVVARS:
        url = os.environ.get(var)
        if url:
            return url
    return None


def is_db_available() -> bool:
    """Check if a database URL is configured."""
    return get_db_url() is not None


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection | None, None, None]:
    """Yield a psycopg2 connection, or None if no DB is configured.

    Usage::

        with get_connection() as conn:
            if conn is None:
                return  # no DB configured, skip
            with conn.cursor() as cur:
                cur.execute(...)
    """
    url = get_db_url()
    if url is None:
        yield None
        return

    try:
        import psycopg2
    except ImportError:
        logger.debug("psycopg2 not installed, skipping DB")
        yield None
        return

    conn = psycopg2.connect(url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
