from collections.abc import Iterator
from functools import lru_cache

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from app.config import get_settings


@lru_cache
def engine_for_url(url: str) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql":
        raise ValueError("A PostgreSQL DATABASE_URL is required")
    if parsed.drivername == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg")
    return create_engine(
        parsed,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5, "options": "-ctimezone=UTC"},
    )


def get_engine() -> Engine:
    url = get_settings().database_url
    if not url:
        raise HTTPException(503, "Database is not configured; set DATABASE_URL and run migrations")
    try:
        return engine_for_url(url)
    except (ValueError, ImportError) as exc:
        raise HTTPException(503, "Configure a valid PostgreSQL DATABASE_URL") from exc


def get_db() -> Iterator[Session]:
    with Session(get_engine(), expire_on_commit=False) as session:
        yield session
