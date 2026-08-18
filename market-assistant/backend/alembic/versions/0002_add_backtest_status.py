"""add status column to backtests"""
from alembic import op

revision = "0002_add_backtest_status"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE backtests ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'")


def downgrade() -> None:
    op.execute("ALTER TABLE backtests DROP COLUMN status")
