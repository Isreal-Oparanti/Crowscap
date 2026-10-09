"""source summary markdown

Adds `summary_markdown` to sources: a holistic, LLM-written, organized
markdown write-up of the whole source, produced once by extraction
(CaptureExtraction.source_overview_markdown) and served by
GET /sources/{id} as the "Original" tab's content in place of the raw,
often unpunctuated `raw_text` transcript/article dump. `raw_text` itself
is unchanged by this migration and stays the only thing extraction,
content-hash dedup, and re-extraction read from.

Revision ID: 0011_source_summary_markdown
Revises: 0010_memory_list_fields
Create Date: 2026-10-09 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0011_source_summary_markdown"
down_revision = "0010_memory_list_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("summary_markdown", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sources", "summary_markdown")
