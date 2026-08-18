import numpy as np
import pandas as pd
import pytest

from app.ml.baseline import (
    buy_and_hold_return,
    passes_baseline_gate,
    random_baseline_return,
)
from app.ml.evaluate import simulate_directional_returns


def test_buy_and_hold_return_matches_hand_computed_cost_fixture():
    # Same numbers as Phase 5's apply_costs fixture: entry 100 -> exit 110,
    # 10bps fees + 5bps slippage => net_pnl = 9.685005 => net_return = 0.09685005.
    idx = pd.date_range("2024-01-01", periods=2, freq="1h", tz="UTC")
    candles = pd.DataFrame({"c": [100.0, 110.0]}, index=idx)

    result = buy_and_hold_return(candles, fees_bps=10.0, slippage_bps=5.0)
    assert result == pytest.approx(0.09685005, abs=1e-9)


def test_random_baseline_return_is_deterministic_given_fixed_seed():
    idx = pd.date_range("2024-01-01", periods=50, freq="1h", tz="UTC")
    close = 100.0 + np.cumsum(np.sin(np.linspace(0, 10, 50)))
    candles = pd.DataFrame({"c": close}, index=idx)

    first = random_baseline_return(candles, fees_bps=10.0, slippage_bps=5.0, n_trials=50, seed=42)
    second = random_baseline_return(candles, fees_bps=10.0, slippage_bps=5.0, n_trials=50, seed=42)
    assert first == second


def test_baseline_gate_requires_beating_both_buy_hold_and_random():
    # Fails: model <= buy_hold, even though model > random.
    assert (
        passes_baseline_gate(model_net_return=0.05, buy_hold_return=0.08, random_return=0.02)
        is False
    )
    # Fails: model <= random, even though model > buy_hold.
    assert (
        passes_baseline_gate(model_net_return=0.03, buy_hold_return=0.01, random_return=0.05)
        is False
    )
    # Passes: model strictly beats both.
    assert (
        passes_baseline_gate(model_net_return=0.10, buy_hold_return=0.08, random_return=0.02)
        is True
    )
    # Fails on exact tie (spec requires strictly better, not "at least as good").
    assert (
        passes_baseline_gate(model_net_return=0.08, buy_hold_return=0.08, random_return=0.02)
        is False
    )


def test_simulate_directional_returns_matches_hand_computation_for_single_entry():
    close = np.array([100.0, 110.0, 105.0])
    entries_mask = np.array([True, False, False])
    # Only bar0 enters; horizon=1 -> trade closes at bar1 (100 -> 110), same
    # cost fixture as above => net_return contribution = 0.09685005.
    result = simulate_directional_returns(
        close, entries_mask, horizon=1, fees_bps=10.0, slippage_bps=5.0
    )
    assert result == pytest.approx(0.09685005, abs=1e-9)
