"""Resolve an instrument symbol to its ML ``instrument_group``.

MLModels are keyed by a free-form ``instrument_group`` string chosen at train
time; there is no group column on Instrument and no training taxonomy in the
repo. This module is the single documented convention the live dispatcher uses
to find a published model for an instrument. It is deliberately conservative:
until a model with a matching group is published, ML enqueue is a no-op.
"""

from __future__ import annotations

_CRYPTO_MAJORS = {"BTC/USDT", "ETH/USDT"}


def instrument_group_for(symbol: str) -> str:
    if symbol in _CRYPTO_MAJORS:
        return "crypto_majors"
    if symbol.endswith("/USDT"):
        return "crypto_alts"
    return "nse_equities"
