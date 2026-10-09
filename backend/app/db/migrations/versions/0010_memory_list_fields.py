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
    op.add_column("memories", sa.Column("list_group_id", sa.String(length=80), nullable=True))
    op.add_column("memories", sa.Column("list_position", sa.Integer(), nullable=True))
    op.add_column("memories", sa.Column("list_total", sa.Integer(), nullable=True))
    op.create_index("ix_memories_list_group_id", "memories", ["list_group_id"])


def downgrade() -> None:
    op.drop_index("ix_memories_list_group_id", table_name="memories")
    op.drop_column("memories", "list_total")
    op.drop_column("memories", "list_position")
    op.drop_column("memories", "list_group_id")
