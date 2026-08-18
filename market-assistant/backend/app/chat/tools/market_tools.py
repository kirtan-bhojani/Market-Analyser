"""Market-data chat tools: thin async wrappers over Phase 3/4 internals.

All tools take ``ctx["db"]`` (an ``AsyncSession``) and resolve a symbol to an
instrument id, then load recent candles via ``load_recent_candles`` and compute
indicators with the pure ``list[float]`` indicator library. There is no
DataFrame candle loader and no ``app/trend`` regime engine in this codebase, so
``get_regime``/``get_breadth`` are implemented here from the ADX/EMA primitives.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.tools.router import TOOL_IMPLS
from app.models.candle import CandleRow
from app.models.instrument import Instrument
from app.scanner import indicators as ind

_DEFAULT_LOOKBACK = 250


def _f(value: Any) -> float:
    return float(value) if value is not None else 0.0


async def _resolve_instrument(db: AsyncSession, symbol: str) -> int | None:
    row = (
        await db.execute(
            select(Instrument).where(
                Instrument.symbol == symbol, Instrument.active.is_(True)
            )
        )
    ).scalars().first()
    return row.id if row else None


async def _load(db: AsyncSession, instrument_id: int, tf: str, n: int) -> list[CandleRow]:
    from app.scanner.history import load_recent_candles

    return await load_recent_candles(db, instrument_id, tf, limit=n)


def _closes(rows: list[CandleRow]) -> list[float]:
    return [_f(r.c) for r in rows]


def _series(rows: list[CandleRow]) -> tuple[list[float], list[float], list[float], list[float]]:
    return (
        [_f(r.h) for r in rows],
        [_f(r.l) for r in rows],
        [_f(r.c) for r in rows],
        [_f(r.v) for r in rows],
    )


async def get_price(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    db = ctx["db"]
    symbol = args["symbol"]
    instrument_id = await _resolve_instrument(db, symbol)
    if instrument_id is None:
        return {"symbol": symbol, "available": False}
    tf = args.get("tf", "1m")
    rows = await _load(db, instrument_id, tf, 1)
    if not rows:
        # Fall back to any timeframe that has data.
        for alt in ("1m", "5m", "15m", "1h", "1d"):
            rows = await _load(db, instrument_id, alt, 1)
            if rows:
                tf = alt
                break
    if not rows:
        return {"symbol": symbol, "available": False}
    return {"symbol": symbol, "tf": tf, "price": _f(rows[-1].c)}


async def get_candles(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    db = ctx["db"]
    symbol, tf = args["symbol"], args["tf"]
    n = int(args.get("n", 100))
    instrument_id = await _resolve_instrument(db, symbol)
    if instrument_id is None:
        return {"symbol": symbol, "available": False}
    rows = await _load(db, instrument_id, tf, n)
    return {
        "symbol": symbol,
        "tf": tf,
        "candles": [
            {
                "ts": r.ts.isoformat(),
                "o": _f(r.o),
                "h": _f(r.h),
                "l": _f(r.l),
                "c": _f(r.c),
                "v": _f(r.v),
            }
            for r in rows
        ],
    }


async def get_indicators(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    db = ctx["db"]
    symbol, tf = args["symbol"], args["tf"]
    instrument_id = await _resolve_instrument(db, symbol)
    if instrument_id is None:
        return {"symbol": symbol, "tf": tf, "available": False}
    rows = await _load(db, instrument_id, tf, _DEFAULT_LOOKBACK)
    if len(rows) < 20:
        return {"symbol": symbol, "tf": tf, "available": False}
    highs, lows, closes, volumes = _series(rows)
    return {
        "symbol": symbol,
        "tf": tf,
        "rsi": round(ind.rsi(closes, period=14)[-1], 2),
        "ema_9": round(ind.ema(closes, 9)[-1], 2),
        "ema_21": round(ind.ema(closes, 21)[-1], 2),
        "vwap": round(ind.vwap(highs, lows, closes, volumes)[-1], 2),
        "atr": round(ind.atr(highs, lows, closes, period=14)[-1], 2),
        "adx": round(ind.adx(highs, lows, closes, period=14)[-1], 2),
    }


def _classify_regime(closes: list[float], adx_val: float) -> str:
    ema_fast = ind.ema(closes, 9)[-1]
    ema_slow = ind.ema(closes, 21)[-1]
    if adx_val >= 25.0:
        return "trend_up" if ema_fast >= ema_slow else "trend_down"
    return "range"


async def get_regime(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    db = ctx["db"]
    symbol = args["symbol"]
    tf = args.get("tf", "1h")
    instrument_id = await _resolve_instrument(db, symbol)
    if instrument_id is None:
        return {"symbol": symbol, "available": False}
    rows = await _load(db, instrument_id, tf, _DEFAULT_LOOKBACK)
    if len(rows) < 20:
        return {"symbol": symbol, "tf": tf, "available": False}
    highs, lows, closes, _ = _series(rows)
    adx_val = ind.adx(highs, lows, closes, period=14)[-1]
    atr_val = ind.atr(highs, lows, closes, period=14)[-1]
    last_close = closes[-1]
    atr_pct = round(atr_val / last_close * 100, 2) if last_close else 0.0
    return {
        "symbol": symbol,
        "tf": tf,
        "regime": _classify_regime(closes, adx_val),
        "adx": round(adx_val, 2),
        "atr_pct": atr_pct,
    }


async def get_breadth(args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Universe breadth: fraction of active instruments trading above their
    EMA(50) on the given timeframe, plus advancer/decliner counts by last-bar
    return. Bounded to active instruments with sufficient history."""
    db = ctx["db"]
    tf = args.get("tf", "1h")
    instruments = (
        await db.execute(select(Instrument).where(Instrument.active.is_(True)))
    ).scalars().all()
    above, advancers, decliners, counted = 0, 0, 0, 0
    for inst in instruments:
        rows = await _load(db, inst.id, tf, 60)
        if len(rows) < 51:
            continue
        counted += 1
        closes = _closes(rows)
        if closes[-1] >= ind.ema(closes, 50)[-1]:
            above += 1
        if closes[-1] >= closes[-2]:
            advancers += 1
        else:
            decliners += 1
    pct_above = round(above / counted * 100, 1) if counted else 0.0
    return {
        "tf": tf,
        "instruments_counted": counted,
        "pct_above_ema50": pct_above,
        "advancers": advancers,
        "decliners": decliners,
    }


TOOL_IMPLS.update(
    {
        "get_price": get_price,
        "get_candles": get_candles,
        "get_indicators": get_indicators,
        "get_regime": get_regime,
        "get_breadth": get_breadth,
    }
)
