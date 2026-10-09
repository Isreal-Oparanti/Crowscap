from __future__ import annotations

from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.logging import get_logger
from app.db.base import Base
from app.db.models import utc_now
from app.db.vector import ensure_postgres_vector_schema

logger = get_logger("db.schema")


def ensure_database_schema(*, engine: Engine, database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        ensure_postgres_vector_schema(engine=engine)
        _ensure_postgres_additive_columns(engine=engine)
        return

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_source_columns(engine=engine)
    _ensure_sqlite_memory_columns(engine=engine)


# Self-heal net for additive (nullable, no-backfill) migrations on Postgres.
# Alembic (`alembic upgrade head`) stays the system of record for schema
# history/rollback -- this exists only because a missed/forgotten migration
# step on a deploy otherwise means every ORM query shaped like `SELECT *`
# against the affected table hard-crashes with `UndefinedColumn`, including
# unrelated background paths (e.g. the notification worker crashed on this
# exact class of error from 0010_memory_list_fields before this existed).
# Every entry here must be a column that is nullable with no backfill
# requirement, so adding it via `IF NOT EXISTS` on every startup is always
# safe, idempotent, and a no-op once the real migration has actually run
# (whichever applies it first wins; the other becomes a no-op). Keep this
# list append-only as new additive columns are introduced -- do not use it
# for anything that needs a backfill, a NOT NULL constraint, or a type
# change; those still require a real `alembic upgrade head`.
_POSTGRES_ADDITIVE_COLUMNS: dict[str, list[str]] = {
    "memories": [
        # 0010_memory_list_fields
        "ALTER TABLE memories ADD COLUMN IF NOT EXISTS list_group_id VARCHAR(80)",
        "ALTER TABLE memories ADD COLUMN IF NOT EXISTS list_position INTEGER",
        "ALTER TABLE memories ADD COLUMN IF NOT EXISTS list_total INTEGER",
    ],
    "sources": [
        # 0011_source_summary_markdown
        "ALTER TABLE sources ADD COLUMN IF NOT EXISTS summary_markdown TEXT",
    ],
}
_POSTGRES_ADDITIVE_INDEXES: list[str] = [
    "CREATE INDEX IF NOT EXISTS ix_memories_list_group_id ON memories (list_group_id)",
]


def _ensure_postgres_additive_columns(*, engine: Engine) -> None:
    if not engine.dialect.name == "postgresql":
        return

    try:
        with engine.begin() as connection:
            for table, statements in _POSTGRES_ADDITIVE_COLUMNS.items():
                if not connection.execute(
                    text("SELECT to_regclass(:qualified_name)"),
                    {"qualified_name": f"public.{table}"},
                ).scalar_one():
                    continue
                for statement in statements:
                    connection.execute(text(statement))
            for statement in _POSTGRES_ADDITIVE_INDEXES:
                connection.execute(text(statement))
    except SQLAlchemyError as exc:
        # Self-heal is a convenience, not the system of record — if this
        # fails (e.g. the DB role lacks ALTER TABLE privilege), log loudly
        # and let the real fix (alembic upgrade head, run with sufficient
        # privileges) be the one that's required. Don't mask the failure
        # by swallowing it silently.
        logger.warning(
            "⚠️ db.schema.postgres_self_heal_failed reason=%s "
            "action='run alembic upgrade head manually'",
            str(exc).replace("\n", " ")[:500],
        )


def _ensure_sqlite_source_columns(*, engine: Engine) -> None:
    inspector = inspect(engine)
    if "sources" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("sources")}
    column_sql = {
        "raw_text": "ALTER TABLE sources ADD COLUMN raw_text TEXT",
        "resolved_url": "ALTER TABLE sources ADD COLUMN resolved_url TEXT",
        # See db/migrations/versions/0011_source_summary_markdown.py (the
        # Postgres equivalent of this block).
        "summary_markdown": "ALTER TABLE sources ADD COLUMN summary_markdown TEXT",
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
        # See db/migrations/versions/0010_memory_list_fields.py (the Postgres
        # equivalent of this block) for why these exist: recording a
        # memory's place in an explicit enumerated list its source named.
        "list_group_id": "ALTER TABLE memories ADD COLUMN list_group_id VARCHAR(80)",
        "list_position": "ALTER TABLE memories ADD COLUMN list_position INTEGER",
        "list_total": "ALTER TABLE memories ADD COLUMN list_total INTEGER",
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
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_memories_list_group_id ON memories (list_group_id)")
        )

    if added:
        logger.info("\U0001f527 db.schema.sqlite_columns_added table=memories columns=%s", added)
