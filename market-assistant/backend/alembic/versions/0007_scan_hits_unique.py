"""unique (rule_id, instrument_id, ts) on scan_hits"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_scan_hits_rule_instrument_ts",
        "scan_hits",
        ["rule_id", "instrument_id", "ts"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_scan_hits_rule_instrument_ts", "scan_hits", type_="unique"
    )
