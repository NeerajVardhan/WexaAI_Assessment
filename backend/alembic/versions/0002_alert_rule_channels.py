"""Add email_recipients and webhook_url to alert_rules.

Revision ID: 0002_alert_rule_channels
Revises: 0001_initial
Create Date: 2026-05-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_alert_rule_channels"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE alert_rules
        ADD COLUMN IF NOT EXISTS email_recipients JSON DEFAULT '[]',
        ADD COLUMN IF NOT EXISTS webhook_url VARCHAR(500)
    """)


def downgrade() -> None:
    op.drop_column("alert_rules", "webhook_url")
    op.drop_column("alert_rules", "email_recipients")
