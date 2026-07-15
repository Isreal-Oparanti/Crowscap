"""Add durable user preference profiles.

Revision ID: 0004_user_preferences
Revises: 0003_reminders
Create Date: 2026-07-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_user_preferences"
down_revision = "0003_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        msg = "This migration targets PostgreSQL because Crowscap uses pgvector."
        raise RuntimeError(msg)

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("profile_key", sa.String(length=80), nullable=False),
        sa.Column("preferred_review_time", sa.String(length=40), nullable=True),
        sa.Column("recall_frequency", sa.String(length=40), nullable=True),
        sa.Column("answer_style", sa.String(length=40), nullable=True),
        sa.Column("evidence_strictness", sa.String(length=40), nullable=False, server_default="balanced"),
        sa.Column("challenge_style", sa.String(length=40), nullable=False, server_default="balanced"),
        sa.Column("memory_density", sa.String(length=40), nullable=True),
        sa.Column("notification_preference", sa.String(length=80), nullable=True),
        sa.Column("topics_of_interest", postgresql.JSONB(), nullable=True),
        sa.Column("source_preferences", postgresql.JSONB(), nullable=True),
        sa.Column(
            "updated_from_message_id",
            sa.String(length=36),
            sa.ForeignKey("chat_messages.id"),
            nullable=True,
        ),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"])
    op.create_index("ix_user_preferences_profile_key", "user_preferences", ["profile_key"], unique=True)
    op.create_index(
        "ix_user_preferences_updated_from_message_id",
        "user_preferences",
        ["updated_from_message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_preferences_updated_from_message_id", table_name="user_preferences")
    op.drop_index("ix_user_preferences_profile_key", table_name="user_preferences")
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
