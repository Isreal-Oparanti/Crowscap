"""Initial PostgreSQL schema with pgvector.

Revision ID: 0001_initial_postgres_pgvector
Revises:
Create Date: 2026-07-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial_postgres_pgvector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("This migration is for PostgreSQL. SQLite uses local create_all bootstrap.")

    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("title", sa.String(length=120), nullable=False, server_default="New thought"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("ix_chat_messages_user_id", "chat_messages", ["user_id"])

    op.create_table(
        "sources",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=True),
        sa.Column("resolved_url", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("captured_snapshot_uri", sa.Text(), nullable=True),
        sa.Column("raw_text_uri", sa.Text(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("extracted_text_hash", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_sources_user_id", "sources", ["user_id"])
    op.create_index("ix_sources_extracted_text_hash", "sources", ["extracted_text_hash"])
    op.create_index("ix_sources_resolved_url", "sources", ["resolved_url"])

    op.create_table(
        "captures",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("user_note", sa.Text(), nullable=True),
        sa.Column("user_intent_text", sa.Text(), nullable=True),
        sa.Column("inferred_intents", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
    )
    op.create_index("ix_captures_user_id", "captures", ["user_id"])
    op.create_index("ix_captures_source_id", "captures", ["source_id"])

    op.create_table(
        "memories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("capture_id", sa.String(length=36), nullable=False),
        sa.Column("memory_type", sa.String(length=40), nullable=False),
        sa.Column("epistemic_label", sa.String(length=80), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("confidence_reason", sa.Text(), nullable=True),
        sa.Column("source_strength", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("importance_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("decay_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("embedding_json", postgresql.JSONB(), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recall_score", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["capture_id"], ["captures.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
    )
    op.create_index("ix_memories_user_id", "memories", ["user_id"])
    op.create_index("ix_memories_source_id", "memories", ["source_id"])
    op.create_index("ix_memories_capture_id", "memories", ["capture_id"])
    op.create_index("ix_memories_next_review_at", "memories", ["next_review_at"])
    op.execute("ALTER TABLE memories ADD COLUMN embedding_vector vector(1024)")
    op.execute(
        "CREATE INDEX ix_memories_embedding_vector_hnsw "
        "ON memories USING hnsw (embedding_vector vector_cosine_ops) "
        "WHERE embedding_vector IS NOT NULL"
    )

    op.create_table(
        "recall_reviews",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("memory_id", sa.String(length=36), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("self_rating", sa.Integer(), nullable=True),
        sa.Column("evaluation_score", sa.Float(), nullable=False),
        sa.Column("rating", sa.String(length=30), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("understanding_summary", sa.Text(), nullable=False),
        sa.Column("knowledge_gaps", postgresql.JSONB(), nullable=True),
        sa.Column("context_to_consider", postgresql.JSONB(), nullable=True),
        sa.Column("next_question", sa.Text(), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"]),
    )
    op.create_index("ix_recall_reviews_user_id", "recall_reviews", ["user_id"])
    op.create_index("ix_recall_reviews_memory_id", "recall_reviews", ["memory_id"])

    op.create_table(
        "memory_relations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("source_memory_id", sa.String(length=36), nullable=False),
        sa.Column("target_memory_id", sa.String(length=36), nullable=False),
        sa.Column("relation_type", sa.String(length=40), nullable=False),
        sa.Column("strength", sa.String(length=20), nullable=False, server_default="unknown"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_memory_id"], ["memories.id"]),
        sa.ForeignKeyConstraint(["target_memory_id"], ["memories.id"]),
    )
    op.create_index("ix_memory_relations_user_id", "memory_relations", ["user_id"])
    op.create_index("ix_memory_relations_source_memory_id", "memory_relations", ["source_memory_id"])
    op.create_index("ix_memory_relations_target_memory_id", "memory_relations", ["target_memory_id"])


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        raise RuntimeError("This migration is for PostgreSQL.")

    op.drop_index("ix_memory_relations_target_memory_id", table_name="memory_relations")
    op.drop_index("ix_memory_relations_source_memory_id", table_name="memory_relations")
    op.drop_index("ix_memory_relations_user_id", table_name="memory_relations")
    op.drop_table("memory_relations")

    op.drop_index("ix_recall_reviews_memory_id", table_name="recall_reviews")
    op.drop_index("ix_recall_reviews_user_id", table_name="recall_reviews")
    op.drop_table("recall_reviews")

    op.execute("DROP INDEX IF EXISTS ix_memories_embedding_vector_hnsw")
    op.drop_index("ix_memories_next_review_at", table_name="memories")
    op.drop_index("ix_memories_capture_id", table_name="memories")
    op.drop_index("ix_memories_source_id", table_name="memories")
    op.drop_index("ix_memories_user_id", table_name="memories")
    op.drop_table("memories")

    op.drop_index("ix_captures_source_id", table_name="captures")
    op.drop_index("ix_captures_user_id", table_name="captures")
    op.drop_table("captures")

    op.drop_index("ix_sources_resolved_url", table_name="sources")
    op.drop_index("ix_sources_extracted_text_hash", table_name="sources")
    op.drop_index("ix_sources_user_id", table_name="sources")
    op.drop_table("sources")

    op.drop_index("ix_chat_messages_user_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_conversation_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_table("conversations")
