"""Add autonomous perspective notes.

Revision ID: 0006_pref_perspectives
Revises: 0005_users_auth
Create Date: 2026-07-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_pref_perspectives"
down_revision = "0005_users_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        msg = "This migration targets PostgreSQL because Crowscap uses pgvector."
        raise RuntimeError(msg)

    op.create_table(
        "memory_perspective_notes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("memory_id", sa.String(length=36), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("perspective_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("suggested_query", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("surface_after_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("surfaced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_perspective_notes_user_id", "memory_perspective_notes", ["user_id"])
    op.create_index("ix_memory_perspective_notes_memory_id", "memory_perspective_notes", ["memory_id"])
    op.create_index("ix_memory_perspective_notes_status", "memory_perspective_notes", ["status"])
    op.create_index(
        "ix_memory_perspective_notes_surface_after_at",
        "memory_perspective_notes",
        ["surface_after_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_memory_perspective_notes_surface_after_at", table_name="memory_perspective_notes")
    op.drop_index("ix_memory_perspective_notes_status", table_name="memory_perspective_notes")
    op.drop_index("ix_memory_perspective_notes_memory_id", table_name="memory_perspective_notes")
    op.drop_index("ix_memory_perspective_notes_user_id", table_name="memory_perspective_notes")
    op.drop_table("memory_perspective_notes")
