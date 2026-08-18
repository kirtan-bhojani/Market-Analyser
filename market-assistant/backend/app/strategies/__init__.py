"""Strategy presets package.

Importing this package eagerly imports every preset module so each strategy
self-registers into ``app.strategies.registry``. Any consumer that does
``import app.strategies`` (or imports the registry, which imports this parent
package) therefore sees the full set of presets without a separate wiring step.
"""

from app.strategies import (  # noqa: F401  (imported for registry side effects)
    bb_rsi_revert,
    breakout_retest,
    ema_vwap_trend,
    funding_extreme,
    grid_range,
    orb,
    pullback_trend,
    vwap_revert,
)
