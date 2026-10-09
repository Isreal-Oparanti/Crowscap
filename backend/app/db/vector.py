from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("db.vector")


class PgVectorUnavailableError(RuntimeError):
    """Raised when pgvector setup/writes fail and Settings.require_pgvector is True.

    Without this, a Postgres deployment whose pgvector extension or column
    is broken (permissions, extension not whitelisted, disk full on the
    CREATE INDEX, a bad migration) falls back silently to the
    embedding_json / in-process-cosine-similarity path -- correct answers,
    much slower, capped at 1000 rows
    (search_service._load_searchable_memories), and nothing ever alerts
    anyone. Set `require_pgvector=True` in production so this fails the
    request/startup instead of degrading invisibly.
    """

# Dimension of Qwen's text-embedding-v4 model output.
# IMPORTANT: This must match the `vector(N)` column type defined in the pgvector
# schema below. If you switch embedding models, update this constant AND run an
# Alembic migration to change the column type (you cannot resize a vector column
# in-place without re-embedding all stored memories).
QWEN_EMBEDDING_DIMENSIONS = 1024


def is_postgres_bind(bind: object) -> bool:
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", "") == "postgresql"


def format_pgvector(embedding: Sequence[float]) -> str:
    return "[" + ",".join(f"{float(value):.10g}" for value in embedding) + "]"


def ensure_postgres_vector_schema(*, engine: Engine) -> None:
    if not is_postgres_bind(engine):
        return

    require_pgvector = get_settings().require_pgvector

    inspector = inspect(engine)
    if "memories" not in inspector.get_table_names():
        logger.warning(
            "⚠️ db.vector.schema_missing table=memories action='run alembic upgrade head'"
        )
        if require_pgvector:
            raise PgVectorUnavailableError(
                "memories table is missing; run 'alembic upgrade head' before starting "
                "with require_pgvector=True"
            )
    try:
        existing_cols = {c["name"] for c in inspector.get_columns("memories")}
        if "embedding_vector" in existing_cols:
            logger.info("✅ db.vector.ready extension=vector column=memories.embedding_vector")
            return
    except Exception:
        pass

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
        if require_pgvector:
            raise PgVectorUnavailableError(
                f"pgvector extension/column setup failed and require_pgvector=True: "
                f"{_compact_error(exc)}"
            ) from exc
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

    require_pgvector = get_settings().require_pgvector

    if len(embedding) != QWEN_EMBEDDING_DIMENSIONS:
        logger.warning(
            "⚠️ db.vector.dimension_mismatch memory_id=%s expected=%s actual=%s",
            memory_id,
            QWEN_EMBEDDING_DIMENSIONS,
            len(embedding),
        )
        if require_pgvector:
            raise PgVectorUnavailableError(
                f"embedding dimension mismatch for memory {memory_id}: "
                f"expected {QWEN_EMBEDDING_DIMENSIONS}, got {len(embedding)}"
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
        if require_pgvector:
            raise PgVectorUnavailableError(
                f"pgvector write failed for memory {memory_id} and require_pgvector=True: "
                f"{_compact_error(exc)}"
            ) from exc
        return False

    return True


def _compact_error(exc: BaseException) -> str:
    return str(exc).replace("\n", " ")[:500]
