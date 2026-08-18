import pandas as pd

from app.strategies.funding_extreme import FundingExtremeStrategy


def _day(i: int) -> pd.Timestamp:
    return pd.Timestamp("2024-01-01") + pd.Timedelta(days=i)


def _bar(
    ts: pd.Timestamp, o: float, h: float, l: float, c: float, v: float, funding_rate: float  # noqa: E741
) -> dict[str, object]:
    return {"ts": ts, "o": o, "h": h, "l": l, "c": c, "v": v, "funding_rate": funding_rate}


def test_funding_extreme_golden_crowded_long_fires_one_short_signal() -> None:
    bars = [_bar(_day(i), 100, 101, 99, 100, 500, 0.0005) for i in range(20)]
    # Funding spikes to +0.3% (crowded longs, historically mean-reverts).
    bars.append(_bar(_day(20), 100, 101, 99, 100, 500, 0.003))
    candles = pd.DataFrame(bars)
    strat = FundingExtremeStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert len(signals) == 1
    assert signals[0].direction == "short"


def test_funding_extreme_negative_normal_funding_fires_nothing() -> None:
    bars = [_bar(_day(i), 100, 101, 99, 100, 500, 0.0005) for i in range(21)]
    candles = pd.DataFrame(bars)
    strat = FundingExtremeStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
