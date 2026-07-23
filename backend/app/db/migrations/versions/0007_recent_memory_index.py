"""Add recent memory listing index.

Revision ID: 0007_recent_memory_index
Revises: 0006_pref_perspectives
Create Date: 2026-07-23
"""

from alembic import op


revision = "0007_recent_memory_index"
down_revision = "0006_pref_perspectives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_memories_user_status_created_at",
        "memories",
        ["user_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_memories_user_status_created_at", table_name="memories")
