"""Add metric and event_type columns to alert_rules.

Revision ID: 0004_alert_rule_metric
Revises: 0003_report_dashboard_nullable
Create Date: 2026-05-21
"""

from alembic import op

revision = "0004_alert_rule_metric"
down_revision = "0003_report_dashboard_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE alert_rules
        ADD COLUMN IF NOT EXISTS metric VARCHAR(80) NOT NULL DEFAULT 'event_count',
        ADD COLUMN IF NOT EXISTS event_type VARCHAR(120)
    """)


def downgrade() -> None:
    op.drop_column("alert_rules", "event_type")
    op.drop_column("alert_rules", "metric")
