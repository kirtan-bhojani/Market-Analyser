"""add strategy_configs table"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "0003"
down_revision = "0002_add_backtest_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "strategy_configs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("strategy", sa.Text, nullable=False),
        sa.Column("instrument_id", sa.Integer, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("tf", sa.Text, nullable=False),
        sa.Column("params", JSONB, nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_strategy_configs_lookup",
        "strategy_configs",
        ["strategy", "instrument_id", "tf", "enabled"],
    )


def downgrade() -> None:
    op.drop_index("ix_strategy_configs_lookup", table_name="strategy_configs")
    op.drop_table("strategy_configs")
