from __future__ import annotations

import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    ActionItem,
    Capture,
    ChatMessage,
    Conversation,
    Memory,
    MemoryArchiveEvent,
    MemoryRelation,
    ProcessingJob,
    RecallReview,
    Reminder,
    Source,
)
from app.db.session import SessionLocal as TargetSessionLocal
from app.db.session import engine as target_engine
from app.db.vector import update_memory_embedding_vector

SOURCE_SQLITE_URL = os.getenv("SQLITE_DATABASE_URL", "sqlite:///./crowscap_dev.db")
MODEL_ORDER = [
    Conversation,
    ChatMessage,
    Source,
    Capture,
    ProcessingJob,
    Memory,
    RecallReview,
    Reminder,
    ActionItem,
    MemoryArchiveEvent,
    MemoryRelation,
]


def main() -> None:
    if target_engine.dialect.name != "postgresql":
        print("migrated=false reason=DATABASE_URL must point to PostgreSQL target")
        return

    source_engine = create_engine(SOURCE_SQLITE_URL, connect_args={"check_same_thread": False})
    SourceSessionLocal = sessionmaker(bind=source_engine, autoflush=False, autocommit=False)

    with SourceSessionLocal() as source_db, TargetSessionLocal() as target_db:
        copied = _copy_rows(source_db=source_db, target_db=target_db)
        vectors = _backfill_vectors(target_db=target_db)
        target_db.commit()

    print(f"migrated=true rows={copied} pgvectors={vectors}")


def _copy_rows(*, source_db: Session, target_db: Session) -> int:
    copied = 0
    for model in MODEL_ORDER:
        rows = list(source_db.scalars(select(model)).all())
        for row in rows:
            values = {
                column.name: getattr(row, column.name)
                for column in model.__table__.columns
            }
            target_db.merge(model(**values))
            copied += 1
        if rows:
            target_db.flush()
            print(f"copied table={model.__tablename__} rows={len(rows)}")
    return copied


def _backfill_vectors(*, target_db: Session) -> int:
    memories = target_db.scalars(select(Memory).where(Memory.embedding_json.is_not(None))).all()
    updated = 0
    for memory in memories:
        if update_memory_embedding_vector(
            db=target_db,
            memory_id=memory.id,
            embedding=memory.embedding_json,
        ):
            updated += 1
    return updated


if __name__ == "__main__":
    main()
