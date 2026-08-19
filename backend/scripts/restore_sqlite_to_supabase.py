from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
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
    ProcessingJob,
    PushSubscription,
    RecallReview,
    Reminder,
    Source,
    User,
    UserPreference,
)
from app.db.vector import update_memory_embedding_vector

SOURCE_SQLITE_PATH = os.getenv("SQLITE_DATABASE_PATH", "crowscap_dev.db")
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
    settings = get_settings()
    target_url = os.getenv("DATABASE_URL") or settings.database_url
    if not target_url:
        print("DATABASE_URL environment variable must be set.")
        sys.exit(1)

    print(f"Target DB URL: {target_url[:30]}...")

    sqlite_url = f"sqlite:///{SOURCE_SQLITE_PATH}"
    print(f"Connecting to SQLite source: {sqlite_url}")

    if not os.path.exists(SOURCE_SQLITE_PATH):
        print(f"SQLite file {SOURCE_SQLITE_PATH} not found.")
        sys.exit(1)

    source_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    SourceSession = sessionmaker(bind=source_engine, autoflush=False, autocommit=False)

    target_engine = create_engine(target_url)
    TargetSession = sessionmaker(bind=target_engine, autoflush=False, autocommit=False)

    # 1. Ensure vector extension on Supabase
    print("Ensuring 'vector' extension exists in Target PostgreSQL...")
    with target_engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))

    total_copied = 0
    with SourceSession() as source_db, TargetSession() as target_db:
        # 2. Ensure demo YC user exists
        demo_user = target_db.scalar(select(User).where(User.email == "yc@crowscap.xyz"))
        if not demo_user:
            print("Creating demo YC reviewer user (yc@crowscap.xyz)...")
            target_db.merge(
                User(
                    id="demo_yc_user",
                    email="yc@crowscap.xyz",
                    name="YC Reviewer",
                    provider="demo",
                )
            )
            target_db.commit()
            print("Demo YC user created.")

        # 3. Copy rows table by table from SQLite
        for model in MODEL_ORDER:
            table_name = model.__tablename__
            try:
                rows = list(source_db.scalars(select(model)).all())
            except Exception as e:
                print(f"Notice: Could not read table '{table_name}' from SQLite (might not exist in older schema): {e}")
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
                print(f"Restored table '{table_name}': {count} row(s)")
            total_copied += count

        # 4. Backfill pgvector embeddings
        print("Backfilling pgvector embeddings on Supabase...")
        vector_count = _backfill_vectors(target_db=target_db)
        target_db.commit()

    print(f"Restore finished! Total rows restored: {total_copied}, pgvectors synced: {vector_count}")

def _backfill_vectors(*, target_db: Session) -> int:
    memories = target_db.scalars(select(Memory).where(Memory.embedding_json.is_not(None))).all()
    updated = 0
    for memory in memories:
        try:
            if update_memory_embedding_vector(
                db=target_db,
                memory_id=memory.id,
                embedding=memory.embedding_json,
            ):
                updated += 1
        except Exception as e:
            print(f"Warning vector update failed for memory {memory.id}: {e}")
    return updated

if __name__ == "__main__":
    main()
