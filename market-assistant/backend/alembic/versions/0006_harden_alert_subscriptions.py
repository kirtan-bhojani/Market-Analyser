"""harden alert_subscriptions: NOT NULL, FK to scan_rules, index on user_id

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-11
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN user_id SET NOT NULL;")
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN rule_id SET NOT NULL;")
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN channel SET NOT NULL;")
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN target SET NOT NULL;")
    op.execute(
        "ALTER TABLE alert_subscriptions "
        "ADD CONSTRAINT fk_alert_subscriptions_rule "
        "FOREIGN KEY (rule_id) REFERENCES scan_rules(id) ON DELETE CASCADE;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_alert_subscriptions_user_id "
        "ON alert_subscriptions(user_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_alert_subscriptions_user_id;")
    op.execute(
        "ALTER TABLE alert_subscriptions DROP CONSTRAINT IF EXISTS fk_alert_subscriptions_rule;"
    )
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN user_id DROP NOT NULL;")
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN rule_id DROP NOT NULL;")
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN channel DROP NOT NULL;")
    op.execute("ALTER TABLE alert_subscriptions ALTER COLUMN target DROP NOT NULL;")
