"""unique (user_id, strategy, instrument_id, tf) on strategy_configs"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_strategy_configs_user_scope",
        "strategy_configs",
        ["user_id", "strategy", "instrument_id", "tf"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_strategy_configs_user_scope", "strategy_configs", type_="unique"
    )
