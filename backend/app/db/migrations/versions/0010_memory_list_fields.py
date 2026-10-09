"""memory list fields

Adds list_group_id / list_position / list_total to memories, so a memory
extracted as one item of an explicit enumerated list in its source (e.g.
"13 Businesses for the Age of AI") can record its place in that list. See
the architecture review doc ("Fix 4") for why this exists: without it,
nothing in the schema could represent "this is item 7 of 13", so the
system could never detect or report that a capture's own list was cut
short at ingestion.

Revision ID: 0010_memory_list_fields
Revises: 0009_email_login_codes
Create Date: 2026-10-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_memory_list_fields"
down_revision = "0009_email_login_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: the app's startup schema self-heal may have added these already.
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS list_group_id VARCHAR(80)")
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS list_position INTEGER")
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS list_total INTEGER")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memories_list_group_id ON memories (list_group_id)")


def downgrade() -> None:
    op.drop_index("ix_memories_list_group_id", table_name="memories")
    op.drop_column("memories", "list_total")
    op.drop_column("memories", "list_position")
    op.drop_column("memories", "list_group_id")
