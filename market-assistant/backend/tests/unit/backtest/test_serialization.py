import pandas as pd

from app.backtest.serialization import serialize_equity_curve, stats_hash


def test_serialize_equity_curve_round_trips_timestamps_and_values():
    idx = pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC")
    equity = pd.Series([10_000.0, 10_050.0, 9_980.0], index=idx)

    serialized = serialize_equity_curve(equity)

    assert serialized == [
        {"ts": "2024-01-01T00:00:00+00:00", "value": 10_000.0},
        {"ts": "2024-01-01T01:00:00+00:00", "value": 10_050.0},
        {"ts": "2024-01-01T02:00:00+00:00", "value": 9_980.0},
    ]

def test_stats_hash_is_deterministic_and_order_independent():
    stats_a = {
        "sharpe": 1.234, "max_dd": -0.05, "win_rate": 0.6, "net_return": 0.12, "trade_count": 5,
    }
    stats_b = {
        "trade_count": 5, "net_return": 0.12, "win_rate": 0.6, "max_dd": -0.05, "sharpe": 1.234,
    }

    assert stats_hash(stats_a) == stats_hash(stats_b)

def test_stats_hash_differs_for_different_stats():
    stats_a = {
        "sharpe": 1.234, "max_dd": -0.05, "win_rate": 0.6, "net_return": 0.12, "trade_count": 5,
    }
    stats_c = {
        "sharpe": 1.235, "max_dd": -0.05, "win_rate": 0.6, "net_return": 0.12, "trade_count": 5,
    }

    assert stats_hash(stats_a) != stats_hash(stats_c)
