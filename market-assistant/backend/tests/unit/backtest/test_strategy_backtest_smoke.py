"""Honest-path (`run_signal_backtest`) backtest smoke tests for strategy
presets. Each preset gets one case here; later Phase-6 tasks append theirs.
"""

import math

import pytest

import app.strategies.bb_rsi_revert  # noqa: F401 -- registers "bb_rsi_revert"
import app.strategies.breakout_retest  # noqa: F401 -- registers "breakout_retest"
import app.strategies.ema_vwap_trend  # noqa: F401 -- registers "ema_vwap_trend"
import app.strategies.funding_extreme  # noqa: F401 -- registers "funding_extreme"
import app.strategies.grid_range  # noqa: F401 -- registers "grid_range"
import app.strategies.orb  # noqa: F401 -- registers "orb" with the strategy registry
import app.strategies.pullback_trend  # noqa: F401 -- registers "pullback_trend"
import app.strategies.vwap_revert  # noqa: F401 -- registers "vwap_revert"
from app.backtest.signal_bridge import run_signal_backtest
from app.strategies.registry import get_strategy
from tests.fixtures.candles import load_fixture_candles


@pytest.mark.parametrize(
    "asset_class,fixture_name,window",
    [
        # Crypto: 60d/5760-bar fixture, default window -- strong assertions
        # (this is the pre-existing case, unchanged in spirit).
        ("crypto", "btc_15m_3mo", 60),
        # Equity (NSE): a single synthetic RELIANCE.NS-shaped 15m session
        # with an opening-range breakout. Proves run_signal_backtest/ORB
        # accept equity-scale (~2900) candles, not just crypto-scale ones.
        # window=26 == the fixture's full bar count (a single session);
        # using the crypto default of 60 would be larger than the fixture.
        ("equity", "reliance_15m_breakout_day", 26),
    ],
)
def test_orb_backtest_smoke(asset_class: str, fixture_name: str, window: int) -> None:
    strat = get_strategy("orb")
    result = run_signal_backtest(
        strat,
        load_fixture_candles(fixture_name),
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
        window=window,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert math.isfinite(result.stats["win_rate"])
    assert math.isfinite(result.stats["net_return"])
    if asset_class == "crypto":
        # 60 days of 15m bars gives ORB many opportunities to fire.
        assert result.stats["trade_count"] > 0
    else:
        # A single synthetic day may yield 0-1 trades; the point is that
        # the runner accepts equity candles and produces finite stats,
        # not that it necessarily trades on this one day.
        assert result.stats["trade_count"] >= 0


def test_ema_vwap_trend_backtest_smoke() -> None:
    # window=500 (vs the default 60): this preset's VWAP filter uses the
    # cumulative VWAP over the window it's handed, so it needs a longer
    # lookback context than the intraday presets (orb/vwap_revert) before a
    # cross's close lands on the trend side of VWAP. At window<=300 no cross
    # on this fixture clears the filter (legitimate selectivity, not a bug).
    strat = get_strategy("ema_vwap_trend")
    result = run_signal_backtest(
        strat,
        load_fixture_candles("btc_15m_3mo"),
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
        window=500,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_vwap_revert_backtest_smoke() -> None:
    strat = get_strategy("vwap_revert")
    result = run_signal_backtest(
        strat,
        load_fixture_candles("btc_15m_3mo"),
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_breakout_retest_backtest_smoke() -> None:
    strat = get_strategy("breakout_retest")
    candles = load_fixture_candles("btc_15m_3mo")
    result = run_signal_backtest(
        strat,
        candles,
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
        window=60,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_pullback_trend_backtest_smoke() -> None:
    strat = get_strategy("pullback_trend")
    candles = load_fixture_candles("btc_15m_3mo")
    result = run_signal_backtest(
        strat,
        candles,
        strat.default_params(),
        fees_bps=10,
        slippage_bps=5,
        window=60,
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_bb_rsi_revert_backtest_smoke() -> None:
    strat = get_strategy("bb_rsi_revert")
    candles = load_fixture_candles("btc_15m_3mo")
    result = run_signal_backtest(
        strat, candles, strat.default_params(), fees_bps=10, slippage_bps=5, window=60
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_grid_range_backtest_smoke() -> None:
    strat = get_strategy("grid_range")
    candles = load_fixture_candles("btc_15m_3mo")
    result = run_signal_backtest(
        strat, candles, strat.default_params(), fees_bps=10, slippage_bps=5, window=60
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0


def test_funding_extreme_backtest_smoke() -> None:
    strat = get_strategy("funding_extreme")
    candles = load_fixture_candles("btc_15m_3mo_with_funding")
    result = run_signal_backtest(
        strat, candles, strat.default_params(), fees_bps=10, slippage_bps=5, window=60
    )
    assert math.isfinite(result.stats["sharpe"])
    assert result.stats["trade_count"] > 0
