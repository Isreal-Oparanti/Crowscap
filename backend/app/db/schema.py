from __future__ import annotations

from sqlalchemy import Engine, inspect, text

from app.core.logging import get_logger
from app.db.base import Base
from app.db.models import utc_now
from app.db.vector import ensure_postgres_vector_schema

logger = get_logger("db.schema")


def ensure_database_schema(*, engine: Engine, database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        ensure_postgres_vector_schema(engine=engine)
        return

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_source_columns(engine=engine)
    _ensure_sqlite_memory_columns(engine=engine)


def _ensure_sqlite_source_columns(*, engine: Engine) -> None:
    inspector = inspect(engine)
    if "sources" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("sources")}
    column_sql = {
        "raw_text": "ALTER TABLE sources ADD COLUMN raw_text TEXT",
        "resolved_url": "ALTER TABLE sources ADD COLUMN resolved_url TEXT",
    }
    added: list[str] = []
    with engine.begin() as connection:
        for column_name, statement in column_sql.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(statement))
            added.append(column_name)

    if added:
        logger.info("\U0001f527 db.schema.sqlite_columns_added table=sources columns=%s", added)


def _ensure_sqlite_memory_columns(*, engine: Engine) -> None:
    inspector = inspect(engine)
    if "memories" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("memories")}
    column_sql = {
        "next_review_at": "ALTER TABLE memories ADD COLUMN next_review_at DATETIME",
        "last_reviewed_at": "ALTER TABLE memories ADD COLUMN last_reviewed_at DATETIME",
        "review_count": "ALTER TABLE memories ADD COLUMN review_count INTEGER NOT NULL DEFAULT 0",
        "recall_score": "ALTER TABLE memories ADD COLUMN recall_score FLOAT NOT NULL DEFAULT 0.5",
    }

    added: list[str] = []
    with engine.begin() as connection:
        for column_name, statement in column_sql.items():
            if column_name in existing_columns:
                continue
            connection.execute(text(statement))
            added.append(column_name)

        connection.execute(
            text("UPDATE memories SET next_review_at = :now WHERE next_review_at IS NULL"),
            {"now": utc_now()},
        )
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_memories_next_review_at ON memories (next_review_at)")
        )

    if added:
        logger.info("\U0001f527 db.schema.sqlite_columns_added table=memories columns=%s", added)
