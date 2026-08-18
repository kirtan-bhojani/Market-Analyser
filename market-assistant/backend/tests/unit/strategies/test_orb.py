import pandas as pd

from app.strategies.orb import ORBStrategy


def _bar(
    ts: str, o: float, h: float, l: float, c: float, v: float  # noqa: E741
) -> dict[str, object]:
    return {"ts": pd.Timestamp(ts), "o": o, "h": h, "l": l, "c": c, "v": v}


def test_orb_golden_breakout_fires_one_long_signal() -> None:
    # First 4 bars (09:15-10:00) define the opening range: high=105, low=100.
    bars = [
        _bar("2024-01-01T09:15", 101, 103, 100, 102, 1000),
        _bar("2024-01-01T09:30", 102, 105, 101, 104, 1000),
        _bar("2024-01-01T09:45", 104, 104, 102, 103, 1000),
        _bar("2024-01-01T10:00", 103, 104, 102, 103, 1000),
        # breakout bar: closes above OR high 105, on 3x average volume
        _bar("2024-01-01T10:15", 104, 108, 104, 107, 3000),
    ]
    candles = pd.DataFrame(bars)
    strat = ORBStrategy()
    signals = strat.generate_signals(candles, strat.default_params())

    assert len(signals) == 1
    sig = signals[0]
    assert sig.direction == "long"
    assert sig.ref_entry == 107
    assert sig.ref_sl == 100  # opening range low
    assert sig.ref_tp == 107 + (107 - 100) * 2.0  # default rr=2.0


def _session(day: str, base: float, spike_at: int | None) -> list[dict[str, object]]:
    """Eight 15m bars for one UTC day. Bars 0..3 form the opening range
    (high=base+5, low=base). A `spike_at` bar closes above the OR high on 3x
    volume (a confirmed long breakout); pass None for a quiet, breakout-free
    session."""
    bars = []
    for i in range(8):
        c = base + 2.0
        v = 1000.0
        h, l = base + 5.0, base  # noqa: E741
        if spike_at is not None and i == spike_at:
            c, h, v = base + 12.0, base + 13.0, 3000.0
        ts = f"2024-01-0{day}T{9 + i // 4:02d}:{15 * (i % 4):02d}"
        bars.append(_bar(ts, c - 1.5, h, l, c, v))
    return bars


def test_orb_anchors_opening_range_to_latest_session_not_window_start() -> None:
    # A ~3-day rolling window (what the live worker feeds): day 1 breaks out
    # early, day 3 (the latest session) breaks out at its own bar 4. The signal
    # must be day 3's breakout -- anchoring the OR to the window's oldest bars
    # would instead emit day 1's ancient breakout (deduped forever in live).
    bars = _session("1", 100.0, spike_at=4) + _session("2", 100.0, None) + _session(
        "3", 200.0, spike_at=4
    )
    candles = pd.DataFrame(bars)
    signals = ORBStrategy().generate_signals(candles, ORBStrategy().default_params())

    assert len(signals) == 1
    day3_start = pd.Timestamp("2024-01-03T00:00")
    assert pd.Timestamp(signals[0].ts) >= day3_start
    assert signals[0].direction == "long"
    assert signals[0].meta["or_high"] == 205.0  # day 3's opening range, not day 1's


def test_orb_quiet_latest_session_fires_nothing_despite_earlier_breakout() -> None:
    # Day 1 breaks out but the latest session (day 3) is quiet: session
    # anchoring must not resurrect the stale day-1 breakout.
    bars = _session("1", 100.0, spike_at=4) + _session("2", 100.0, None) + _session(
        "3", 200.0, None
    )
    candles = pd.DataFrame(bars)
    signals = ORBStrategy().generate_signals(candles, ORBStrategy().default_params())
    assert signals == []


def test_orb_negative_breakout_without_volume_confirm_fires_nothing() -> None:
    bars = [
        _bar("2024-01-01T09:15", 101, 103, 100, 102, 1000),
        _bar("2024-01-01T09:30", 102, 105, 101, 104, 1000),
        _bar("2024-01-01T09:45", 104, 104, 102, 103, 1000),
        _bar("2024-01-01T10:00", 103, 104, 102, 103, 1000),
        # closes above OR high but volume is flat (no confirm)
        _bar("2024-01-01T10:15", 104, 106, 104, 106, 1000),
    ]
    candles = pd.DataFrame(bars)
    strat = ORBStrategy()
    signals = strat.generate_signals(candles, strat.default_params())
    assert signals == []
