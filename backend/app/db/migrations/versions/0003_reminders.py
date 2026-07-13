"""Add scheduled reminders.

Revision ID: 0003_reminders
Revises: 0002_jobs_actions_lifecycle
Create Date: 2026-07-12
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_reminders"
down_revision = "0002_jobs_actions_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        msg = "This migration targets PostgreSQL because Crowscap uses pgvector."
        raise RuntimeError(msg)

    op.create_table(
        "reminders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            sa.ForeignKey("conversations.id"),
            nullable=True,
        ),
        sa.Column("memory_id", sa.String(length=36), sa.ForeignKey("memories.id"), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="scheduled"),
        sa.Column("save_as_memory", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_conversation_id", "reminders", ["conversation_id"])
    op.create_index("ix_reminders_memory_id", "reminders", ["memory_id"])
    op.create_index("ix_reminders_due_at", "reminders", ["due_at"])
    op.create_index("ix_reminders_status", "reminders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_reminders_status", table_name="reminders")
    op.drop_index("ix_reminders_due_at", table_name="reminders")
    op.drop_index("ix_reminders_memory_id", table_name="reminders")
    op.drop_index("ix_reminders_conversation_id", table_name="reminders")
    op.drop_index("ix_reminders_user_id", table_name="reminders")
    op.drop_table("reminders")
