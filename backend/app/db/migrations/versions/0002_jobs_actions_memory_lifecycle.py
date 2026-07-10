"""Add processing jobs, action items, and memory lifecycle events.

Revision ID: 0002_jobs_actions_lifecycle
Revises: 0001_initial_postgres_pgvector
Create Date: 2026-07-06
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_jobs_actions_lifecycle"
down_revision = "0001_initial_postgres_pgvector"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        msg = "This migration targets PostgreSQL because Crowscap uses pgvector."
        raise RuntimeError(msg)

    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("job_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("step", sa.String(length=80), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("capture_id", sa.String(length=36), sa.ForeignKey("captures.id"), nullable=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_processing_jobs_user_id", "processing_jobs", ["user_id"])
    op.create_index("ix_processing_jobs_job_type", "processing_jobs", ["job_type"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])
    op.create_index("ix_processing_jobs_capture_id", "processing_jobs", ["capture_id"])
    op.create_index("ix_processing_jobs_source_id", "processing_jobs", ["source_id"])

    op.create_table(
        "action_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("memory_id", sa.String(length=36), sa.ForeignKey("memories.id"), nullable=True),
        sa.Column("source_id", sa.String(length=36), sa.ForeignKey("sources.id"), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="planned"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_from", sa.String(length=40), nullable=False, server_default="memory"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_action_items_user_id", "action_items", ["user_id"])
    op.create_index("ix_action_items_memory_id", "action_items", ["memory_id"])
    op.create_index("ix_action_items_source_id", "action_items", ["source_id"])
    op.create_index("ix_action_items_status", "action_items", ["status"])

    op.create_table(
        "memory_archive_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("memory_id", sa.String(length=36), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("previous_status", sa.String(length=40), nullable=False),
        sa.Column("new_status", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.String(length=80), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="user"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_archive_events_user_id", "memory_archive_events", ["user_id"])
    op.create_index("ix_memory_archive_events_memory_id", "memory_archive_events", ["memory_id"])


def downgrade() -> None:
    op.drop_index("ix_memory_archive_events_memory_id", table_name="memory_archive_events")
    op.drop_index("ix_memory_archive_events_user_id", table_name="memory_archive_events")
    op.drop_table("memory_archive_events")

    op.drop_index("ix_action_items_status", table_name="action_items")
    op.drop_index("ix_action_items_source_id", table_name="action_items")
    op.drop_index("ix_action_items_memory_id", table_name="action_items")
    op.drop_index("ix_action_items_user_id", table_name="action_items")
    op.drop_table("action_items")

    op.drop_index("ix_processing_jobs_source_id", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_capture_id", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_job_type", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_user_id", table_name="processing_jobs")
    op.drop_table("processing_jobs")
