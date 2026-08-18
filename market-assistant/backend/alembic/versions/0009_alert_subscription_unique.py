"""unique (user_id, rule_id, channel, target) on alert_subscriptions"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_alert_sub_user_rule_channel_target",
        "alert_subscriptions",
        ["user_id", "rule_id", "channel", "target"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_alert_sub_user_rule_channel_target",
        "alert_subscriptions",
        type_="unique",
    )
