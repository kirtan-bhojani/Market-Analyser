from dataclasses import dataclass
from typing import Literal

Side = Literal["long", "short"]


@dataclass(frozen=True)
class TradeCosts:
    gross_pnl: float
    fees_paid: float
    slippage_paid: float
    net_pnl: float


def apply_costs(
    entry_price: float,
    exit_price: float,
    fees_bps: float,
    slippage_bps: float,
    side: Side,
) -> TradeCosts:
    slippage_frac = slippage_bps / 10_000.0
    fees_frac = fees_bps / 10_000.0

    if side == "long":
        effective_entry = entry_price * (1 + slippage_frac)
        effective_exit = exit_price * (1 - slippage_frac)
        gross_pnl = effective_exit - effective_entry
    elif side == "short":
        effective_entry = entry_price * (1 - slippage_frac)
        effective_exit = exit_price * (1 + slippage_frac)
        gross_pnl = effective_entry - effective_exit
    else:
        raise ValueError(f"unknown side: {side!r}")

    entry_fee = effective_entry * fees_frac
    exit_fee = effective_exit * fees_frac
    fees_paid = entry_fee + exit_fee

    slippage_paid = abs(effective_entry - entry_price) + abs(effective_exit - exit_price)

    net_pnl = gross_pnl - fees_paid

    return TradeCosts(
        gross_pnl=gross_pnl,
        fees_paid=fees_paid,
        slippage_paid=slippage_paid,
        net_pnl=net_pnl,
    )
