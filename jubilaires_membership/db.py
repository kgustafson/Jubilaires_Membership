import os
from collections.abc import Mapping
from typing import Any, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


DEFAULT_DATABASE_URL = "postgresql+psycopg2://admin:jubilaires@localhost:5433/jubilaires_membership"


def database_url() -> str:
    return os.environ.get("JUBILAIRES_DATABASE_URL", DEFAULT_DATABASE_URL)


def make_engine(url: Optional[str] = None) -> Engine:
    return create_engine(url or database_url(), pool_pre_ping=True)


def fetch_all(sql: str, params: Optional[Mapping[str, Any]] = None, engine: Optional[Engine] = None) -> list[dict[str, Any]]:
    active_engine = engine or make_engine()
    with active_engine.connect() as connection:
        result = connection.execute(text(sql), params or {})
        return [dict(row._mapping) for row in result]


def fetch_one(sql: str, params: Optional[Mapping[str, Any]] = None, engine: Optional[Engine] = None) -> Optional[dict[str, Any]]:
    rows = fetch_all(sql, params, engine)
    return rows[0] if rows else None


def fetch_one_write(sql: str, params: Optional[Mapping[str, Any]] = None, engine: Optional[Engine] = None) -> Optional[dict[str, Any]]:
    active_engine = engine or make_engine()
    with active_engine.begin() as connection:
        result = connection.execute(text(sql), params or {})
        row = result.first()
        return dict(row._mapping) if row else None


def execute(sql: str, params: Optional[Mapping[str, Any]] = None, engine: Optional[Engine] = None) -> None:
    active_engine = engine or make_engine()
    with active_engine.begin() as connection:
        connection.execute(text(sql), params or {})
