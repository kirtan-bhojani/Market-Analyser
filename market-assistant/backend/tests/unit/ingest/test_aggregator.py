from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from app.ingest.aggregator import aggregate_candles
from app.ingest.candle import Candle

TF_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600}


def _make_1m_series(n: int, ohlcv_values, start: datetime) -> list[Candle]:
    candles = []
    for i in range(n):
        o, h, l, c, v = ohlcv_values[i]  # noqa: E741
        candles.append(
            Candle(
                symbol="BTC/USDT",
                tf="1m",
                ts=start + timedelta(minutes=i),
                o=Decimal(str(o)),
                h=Decimal(str(h)),
                l=Decimal(str(l)),
                c=Decimal(str(c)),
                v=Decimal(str(v)),
            )
        )
    return candles


@st.composite
def ohlcv_bar(draw):
    base = draw(st.floats(min_value=1, max_value=100000, allow_nan=False))
    spread = draw(st.floats(min_value=0, max_value=1000, allow_nan=False))
    o = round(base, 2)
    c = round(base + draw(st.floats(min_value=-spread, max_value=spread, allow_nan=False)), 2)
    h = round(max(o, c) + draw(st.floats(min_value=0, max_value=spread, allow_nan=False)), 2)
    l = round(min(o, c) - draw(st.floats(min_value=0, max_value=spread, allow_nan=False)), 2)  # noqa: E741
    v = round(draw(st.floats(min_value=0, max_value=10000, allow_nan=False)), 4)
    return (o, h, l, c, v)


@given(
    bars=st.lists(ohlcv_bar(), min_size=5, max_size=60),
    target_tf=st.sampled_from(["5m", "15m", "1h"]),
)
def test_aggregation_preserves_ohlc_invariants_and_sums_volume(bars, target_tf):
    window = TF_SECONDS[target_tf] // 60
    n = (len(bars) // window) * window
    if n == 0:
        return
    bars = bars[:n]
    start = datetime(2024, 1, 1, tzinfo=UTC)
    candles_1m = _make_1m_series(n, bars, start)

    result = aggregate_candles(candles_1m, target_tf)

    assert len(result) == n // window
    for idx, bar in enumerate(result):
        assert bar.tf == target_tf
        assert bar.l <= bar.o
        assert bar.l <= bar.c
        assert bar.o <= bar.h
        assert bar.c <= bar.h
        assert bar.l <= bar.h

        chunk = candles_1m[idx * window:(idx + 1) * window]
        expected_volume = sum((c.v for c in chunk), Decimal("0"))
        assert bar.v == expected_volume
        assert bar.o == chunk[0].o
        assert bar.c == chunk[-1].c
        assert bar.h == max(c.h for c in chunk)
        assert bar.l == min(c.l for c in chunk)
        assert bar.ts == chunk[0].ts


def test_incomplete_trailing_window_is_dropped():
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars = [(100, 101, 99, 100, 1)] * 7  # 7 bars, target 5m -> 1 full window + 2 leftover
    candles_1m = _make_1m_series(7, bars, start)
    result = aggregate_candles(candles_1m, "5m")
    assert len(result) == 1


def test_unsupported_target_tf_raises_value_error():
    import pytest
    with pytest.raises(ValueError):
        aggregate_candles([], "3m")
