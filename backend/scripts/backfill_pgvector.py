from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine
from app.db.vector import update_memory_embedding_vector


def main() -> None:
    if engine.dialect.name != "postgresql":
        print("skipped=true reason=DATABASE_URL is not PostgreSQL")
        return

    with SessionLocal() as db:
        count = _backfill(db)
        db.commit()

    print(f"pgvector_backfilled={count}")


def _backfill(db: Session) -> int:
    rows = db.execute(
        text(
            "SELECT id, embedding_json "
            "FROM memories "
            "WHERE embedding_json IS NOT NULL "
            "AND embedding_vector IS NULL"
        )
    ).mappings()

    updated = 0
    for row in rows:
        embedding = row["embedding_json"]
        if update_memory_embedding_vector(
            db=db,
            memory_id=str(row["id"]),
            embedding=embedding,
        ):
            updated += 1

    return updated


if __name__ == "__main__":
    main()
