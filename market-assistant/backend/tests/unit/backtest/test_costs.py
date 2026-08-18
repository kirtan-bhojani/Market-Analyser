import pytest

from app.backtest.costs import apply_costs


def test_round_trip_long_10bps_fee_5bps_slippage_exact_net_pnl():
    # Long entry 100.0 -> exit 110.0, size 1 unit.
    # Slippage widens entry up and exit down by 5bps each:
    #   effective_entry = 100.0 * (1 + 0.0005) = 100.05
    #   effective_exit  = 110.0 * (1 - 0.0005) = 109.945
    # Fees charged on both legs' notional at 10bps:
    #   entry_fee = 100.05 * 0.0010 = 0.10005
    #   exit_fee  = 109.945 * 0.0010 = 0.109945
    # gross_pnl (on effective prices) = 109.945 - 100.05 = 9.895
    # net_pnl = gross_pnl - entry_fee - exit_fee = 9.895 - 0.10005 - 0.109945 = 9.685005
    result = apply_costs(
        entry_price=100.0,
        exit_price=110.0,
        fees_bps=10.0,
        slippage_bps=5.0,
        side="long",
    )
    assert result.gross_pnl == pytest.approx(9.895, abs=1e-9)
    assert result.fees_paid == pytest.approx(0.10005 + 0.109945, abs=1e-9)
    assert result.slippage_paid == pytest.approx(0.05 + 0.055, abs=1e-9)
    assert result.net_pnl == pytest.approx(9.685005, abs=1e-9)


def test_round_trip_short_10bps_fee_5bps_slippage_exact_net_pnl():
    # Short entry 100.0 -> exit 90.0, size 1 unit.
    # Slippage works against the short: entry filled lower, exit filled higher.
    #   effective_entry = 100.0 * (1 - 0.0005) = 99.95
    #   effective_exit  = 90.0 * (1 + 0.0005) = 90.045
    # entry_fee = 99.95 * 0.0010 = 0.09995
    # exit_fee  = 90.045 * 0.0010 = 0.090045
    # gross_pnl (short) = effective_entry - effective_exit = 99.95 - 90.045 = 9.905
    # net_pnl = 9.905 - 0.09995 - 0.090045 = 9.715005
    result = apply_costs(
        entry_price=100.0,
        exit_price=90.0,
        fees_bps=10.0,
        slippage_bps=5.0,
        side="short",
    )
    assert result.gross_pnl == pytest.approx(9.905, abs=1e-9)
    assert result.net_pnl == pytest.approx(9.715005, abs=1e-9)
