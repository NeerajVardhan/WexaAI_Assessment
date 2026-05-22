"""Make report_schedules.dashboard_id nullable.

Revision ID: 0003_report_dashboard_nullable
Revises: 0002_alert_rule_channels
Create Date: 2026-05-21
"""

from alembic import op

revision = "0003_report_dashboard_nullable"
down_revision = "0002_alert_rule_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE report_schedules
        ALTER COLUMN dashboard_id DROP NOT NULL
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE report_schedules
        ALTER COLUMN dashboard_id SET NOT NULL
    """)
