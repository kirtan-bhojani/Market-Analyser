"""add nullable user_id to backtests"""
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("backtests", sa.Column("user_id", UUID(as_uuid=True), nullable=True))


def downgrade() -> None:
    op.drop_column("backtests", "user_id")
