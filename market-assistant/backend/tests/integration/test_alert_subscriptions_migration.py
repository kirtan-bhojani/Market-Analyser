from sqlalchemy import inspect

from app.core.deps import get_engine


async def test_alert_subscriptions_hardened():
    engine = get_engine()
    async with engine.connect() as conn:
        def _inspect(sync_conn):
            insp = inspect(sync_conn)
            cols = {c["name"]: c for c in insp.get_columns("alert_subscriptions")}
            fks = insp.get_foreign_keys("alert_subscriptions")
            idxs = insp.get_indexes("alert_subscriptions")
            return cols, fks, idxs

        cols, fks, idxs = await conn.run_sync(_inspect)

    assert set(cols) == {"id", "user_id", "rule_id", "channel", "target"}
    for c in ("user_id", "rule_id", "channel", "target"):
        assert cols[c]["nullable"] is False
    assert any(fk["referred_table"] == "scan_rules" for fk in fks)
    assert any("user_id" in ix["column_names"] for ix in idxs)
