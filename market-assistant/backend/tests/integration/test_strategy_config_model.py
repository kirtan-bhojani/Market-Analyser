import pytest

from app.models.instrument import Instrument
from app.models.strategy_config import StrategyConfig


@pytest.mark.asyncio
async def test_strategy_config_round_trip(db_session):
    instrument = Instrument(symbol="BTC/USDT", asset_class="crypto", exchange="binance")
    db_session.add(instrument)
    await db_session.flush()

    cfg = StrategyConfig(
        user_id="00000000-0000-0000-0000-000000000001",
        strategy="orb",
        instrument_id=instrument.id,
        tf="15m",
        params={"or_bars": 4, "rr": 2.0, "min_rel_volume": 1.5},
        enabled=True,
    )
    db_session.add(cfg)
    await db_session.commit()

    fetched = await db_session.get(StrategyConfig, cfg.id)
    assert fetched.strategy == "orb"
    assert fetched.params["rr"] == 2.0
    assert fetched.enabled is True
