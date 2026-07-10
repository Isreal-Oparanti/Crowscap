from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine


def main() -> None:
    print(f"database_dialect={engine.dialect.name}")
    with engine.connect() as connection:
        if engine.dialect.name != "postgresql":
            print("postgres_ready=false reason=DATABASE_URL is not PostgreSQL")
            return

        version = connection.scalar(text("SELECT version()"))
        vector_installed = connection.scalar(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        memories_exists = connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'memories'"
                ")"
            )
        )
        vector_column_exists = connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'memories' AND column_name = 'embedding_vector'"
                ")"
            )
        )
        vector_index_exists = connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'memories' "
                "AND indexname = 'ix_memories_embedding_vector_hnsw'"
                ")"
            )
        )

        print(f"postgres_version={version}")
        print(f"pgvector_extension={bool(vector_installed)}")
        print(f"memories_table={bool(memories_exists)}")
        print(f"embedding_vector_column={bool(vector_column_exists)}")
        print(f"embedding_vector_hnsw_index={bool(vector_index_exists)}")
        print(
            "postgres_ready="
            f"{bool(vector_installed and memories_exists and vector_column_exists and vector_index_exists)}"
        )


if __name__ == "__main__":
    main()
