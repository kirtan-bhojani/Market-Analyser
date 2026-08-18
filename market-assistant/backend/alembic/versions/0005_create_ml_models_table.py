"""create ml_models table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-11
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ml_models",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("instrument_group", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("strategy", sa.Text(), nullable=False, server_default="ml_lgbm_v1"),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=True),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("ml_models")
