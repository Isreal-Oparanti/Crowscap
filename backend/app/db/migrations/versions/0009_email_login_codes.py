"""email login codes

Revision ID: 0009_email_login_codes
Revises: 0008_notifications
Create Date: 2026-07-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_email_login_codes"
down_revision = "0008_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_login_codes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.String(length=128), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_login_codes_email", "email_login_codes", ["email"])
    op.create_index("ix_email_login_codes_expires_at", "email_login_codes", ["expires_at"])
    op.create_index("ix_email_login_codes_consumed_at", "email_login_codes", ["consumed_at"])


def downgrade() -> None:
    op.drop_index("ix_email_login_codes_consumed_at", table_name="email_login_codes")
    op.drop_index("ix_email_login_codes_expires_at", table_name="email_login_codes")
    op.drop_index("ix_email_login_codes_email", table_name="email_login_codes")
    op.drop_table("email_login_codes")
