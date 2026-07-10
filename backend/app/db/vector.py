from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger

logger = get_logger("db.vector")

QWEN_EMBEDDING_DIMENSIONS = 1024


def is_postgres_bind(bind: object) -> bool:
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "") == "postgresql"


def format_pgvector(embedding: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(value):.10g}" for value in embedding) + "]"


def ensure_postgres_vector_schema(*, engine: Engine) -> None:
    if not is_postgres_bind(engine):
        return

    inspector = inspect(engine)
    if "memories" not in inspector.get_table_names():
        logger.warning(
            "⚠️ db.vector.schema_missing table=memories action='run alembic upgrade head'"
        )
        return

    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.execute(
                text(
                    "ALTER TABLE memories "
                    "ADD COLUMN IF NOT EXISTS embedding_vector vector(1024)"
                )
            )
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_memories_embedding_vector_hnsw "
                    "ON memories USING hnsw (embedding_vector vector_cosine_ops) "
                    "WHERE embedding_vector IS NOT NULL"
                )
            )
    except SQLAlchemyError as exc:
        logger.warning(
            "⚠️ db.vector.unavailable reason=%s fallback=embedding_json",
            _compact_error(exc),
        )
        return

    logger.info("✅ db.vector.ready extension=vector column=memories.embedding_vector")


def update_memory_embedding_vector(
    *,
    db: Session,
    memory_id: str,
    embedding: Sequence[float] | None,
) -> bool:
    if not embedding:
        return False

    bind = db.get_bind()
    if not is_postgres_bind(bind):
        return False

    if len(embedding) != QWEN_EMBEDDING_DIMENSIONS:
        logger.warning(
            "⚠️ db.vector.dimension_mismatch memory_id=%s expected=%s actual=%s",
            memory_id,
            QWEN_EMBEDDING_DIMENSIONS,
            len(embedding),
        )
        return False

    try:
        db.execute(
            text(
                "UPDATE memories "
                "SET embedding_vector = CAST(:embedding AS vector) "
                "WHERE id = :memory_id"
            ),
            {"embedding": format_pgvector(embedding), "memory_id": memory_id},
        )
    except SQLAlchemyError as exc:
        logger.warning(
            "⚠️ db.vector.write_failed memory_id=%s reason=%s",
            memory_id,
            _compact_error(exc),
        )
        return False

    return True


def _compact_error(exc: BaseException) -> str:
    return str(exc).replace("\n", " ")[:500]
