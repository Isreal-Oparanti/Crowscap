from __future__ import annotations

import sys
import os

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    ActionItem,
    Capture,
    ChatMessage,
    Conversation,
    EmailLoginCode,
    Memory,
    MemoryArchiveEvent,
    MemoryPerspectiveNote,
    MemoryRelation,
    NotificationDelivery,
    PushSubscription,
    ProcessingJob,
    RecallReview,
    Reminder,
    Source,
    User,
    UserPreference,
)
from app.db.vector import update_memory_embedding_vector

MODEL_ORDER = [
    User,
    EmailLoginCode,
    UserPreference,
    PushSubscription,
    Conversation,
    ChatMessage,
    Source,
    Capture,
    ProcessingJob,
    Memory,
    RecallReview,
    Reminder,
    NotificationDelivery,
    ActionItem,
    MemoryArchiveEvent,
    MemoryPerspectiveNote,
    MemoryRelation,
]

def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python migrate_neon_to_supabase.py <NEON_SOURCE_URL> <SUPABASE_TARGET_URL>")
        sys.exit(1)

    source_url = sys.argv[1]
    target_url = sys.argv[2]

    print(f" Connecting to Source (Neon)...")
    source_engine = create_engine(source_url)
    SourceSession = sessionmaker(bind=source_engine, autoflush=False, autocommit=False)

    print(f" Connecting to Target (Supabase)...")
    target_engine = create_engine(target_url)
    TargetSession = sessionmaker(bind=target_engine, autoflush=False, autocommit=False)

    # 1. Enable pgvector in Supabase if not enabled
    print(" Ensuring 'vector' extension exists in Supabase...")
    with target_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    # 2. Copy rows table by table
    total_copied = 0
    with SourceSession() as source_db, TargetSession() as target_db:
        for model in MODEL_ORDER:
            table_name = model.__tablename__
            try:
                rows = list(source_db.scalars(select(model)).all())
            except Exception as e:
                print(f"⚠️ Warning reading table '{table_name}': {e}")
                continue

            count = 0
            for row in rows:
                values = {
                    column.name: getattr(row, column.name)
                    for column in model.__table__.columns
                }
                target_db.merge(model(**values))
                count += 1

            if count > 0:
                target_db.commit()
                print(f" Migrated table '{table_name}': {count} row(s)")
            else:
                print(f" Table '{table_name}' is empty (0 rows)")

            total_copied += count

        # 3. Backfill pgvector embeddings
        print(" Backfilling pgvector embeddings on Supabase...")
        vector_count = _backfill_vectors(target_db=target_db)
        target_db.commit()

    print(f" Migration complete! Total rows migrated: {total_copied}, pgvectors synced: {vector_count}")

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
