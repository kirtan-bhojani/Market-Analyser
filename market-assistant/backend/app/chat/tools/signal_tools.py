"""Signal / scan-hit / quick-backtest chat tools.

``run_quick_backtest`` is bounded (recent bars only, ~1y cap by timeframe) and
cached in Redis for an hour, wrapping the honest TP/SL-resolved
``run_signal_backtest`` used by the mini-backtest API.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.backtest.serialization import serialize_equity_curve
from app.backtest.signal_bridge import run_signal_backtest
from app.chat.tools.market_tools import _resolve_instrument
from app.chat.tools.router import TOOL_IMPLS
from app.models.candle import CandleRow
from app.scanner.history import load_recent_candles
from app.strategies.registry import get_strategy

# ~1 year of bars per timeframe, capping how much history a quick backtest scans.
_MAX_BARS_BY_TF = {
    "1m": 8760,
    "5m": 8760,
    "15m": 8760,
    "30m": 8760,
    "1h": 8760,
    "4h": 2190,
    "1d": 366,
}
_DEFAULT_MAX_BARS = 8760


async def get_recent_signals(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    from app.models.signal import Signal

    db: AsyncSession = ctx["db"]
    symbol = args.get("symbol")
    stmt = select(Signal)
    if symbol:
        instrument_id = await _resolve_instrument(db, symbol)
        if instrument_id is None:
            return {"symbol": symbol, "available": False}
        stmt = stmt.where(Signal.instrument_id == instrument_id)
    stmt = stmt.order_by(Signal.ts.desc()).limit(10)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "signals": [
            {
                "strategy": r.strategy,
                "direction": r.direction,
                "ts": r.ts.isoformat(),
                "ref_entry": float(r.ref_entry) if r.ref_entry is not None else None,
                "confidence": float(r.confidence) if r.confidence is not None else None,
            }
            for r in rows
        ]
    }


async def get_scan_hits(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    from app.models.scan_hit import ScanHit
    from app.models.scan_rule import ScanRule

    db: AsyncSession = ctx["db"]
    rule = args.get("rule")
    stmt = select(ScanHit)
    if rule:
        stmt = stmt.join(ScanRule, ScanRule.id == ScanHit.rule_id).where(ScanRule.name == rule)
    stmt = stmt.order_by(ScanHit.ts.desc()).limit(10)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "hits": [
            {
                "rule_id": r.rule_id,
                "instrument_id": r.instrument_id,
                "ts": r.ts.isoformat(),
                "payload": r.payload,
            }
            for r in rows
        ]
    }


def _cache_key(strategy: str, symbol: str, tf: str, params: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
    return f"quick_backtest:{strategy}:{symbol}:{tf}:{digest}"


async def _cache_get(key: str) -> dict[str, Any] | None:
    from app.core.deps import get_redis

    raw = await get_redis().get(key)
    return json.loads(raw) if raw else None


async def _cache_set(key: str, value: dict[str, Any]) -> None:
    from app.core.deps import get_redis

    await get_redis().set(key, json.dumps(value), ex=3600)


def _f(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _candles_to_df(rows: list[CandleRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts": r.ts,
                "o": _f(r.o),
                "h": _f(r.h),
                "l": _f(r.l),
                "c": _f(r.c),
                "v": _f(r.v),
            }
            for r in rows
        ]
    )


async def run_quick_backtest(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    db: AsyncSession = ctx["db"]
    strategy_name, symbol = args["strategy"], args["symbol"]
    tf = args.get("tf", "1h")
    try:
        strat = get_strategy(strategy_name)
    except KeyError:
        return {"strategy": strategy_name, "available": False, "error": "unknown strategy"}
    params = args.get("params") or strat.default_params()

    key = _cache_key(strategy_name, symbol, tf, params)
    try:
        cached = await _cache_get(key)
    except Exception:
        cached = None
    if cached is not None:
        return cached

    instrument_id = await _resolve_instrument(db, symbol)
    if instrument_id is None:
        return {"symbol": symbol, "available": False}

    max_bars = _MAX_BARS_BY_TF.get(tf, _DEFAULT_MAX_BARS)
    rows = await load_recent_candles(db, instrument_id, tf, limit=max_bars)
    if len(rows) < 60:
        return {"strategy": strategy_name, "symbol": symbol, "tf": tf, "available": False}
    df = _candles_to_df(rows)
    # Pass the tf/asset_class so the window is floored to the asset's session
    # length (session-anchored presets need the full session in view) rather
    # than relying on the stale 60-bar default.
    asset_class = "equity" if symbol.endswith(".NS") else "crypto"
    result = await asyncio.to_thread(
        run_signal_backtest, strat, df, params, 10, 5, tf=tf, asset_class=asset_class
    )
    payload = {
        "strategy": strategy_name,
        "symbol": symbol,
        "tf": tf,
        "stats": {k: float(v) for k, v in result.stats.items()},
        "equity_curve": serialize_equity_curve(result.equity_curve),
        "n_candles": len(rows),
    }
    try:
        await _cache_set(key, payload)
    except Exception:
        pass
    return payload


TOOL_IMPLS.update(
    {
        "get_recent_signals": get_recent_signals,
        "get_scan_hits": get_scan_hits,
        "run_quick_backtest": run_quick_backtest,
    }
)
