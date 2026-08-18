"""Stateful per-instrument-timeframe indicator cache.

Warms up once from a batch history callback, then advances incrementally as new
candles arrive. Each `update` appends the candle and recomputes the requested
indicators over the stored series, returning a flat snapshot keyed like
``"rsi:14"``, ``"ema:21"``, ``"bollinger_upper:20:2.0"``.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol

from app.scanner import indicators as ind

WARM_START_BARS = 200

NAN = float("nan")


class CandleLike(Protocol):
    ts: int
    o: float
    h: float
    l: float  # noqa: E741
    c: float
    v: float


LoadHistory = Callable[[int, str, int], Sequence[CandleLike]]


class InstrumentTfCache:
    def __init__(
        self,
        instrument_id: int,
        tf: str,
        load_history: LoadHistory,
        requested_indicators: list[str],
    ):
        self._instrument_id = instrument_id
        self._tf = tf
        self._load_history = load_history
        self._requested = requested_indicators
        self._opens: list[float] = []
        self._highs: list[float] = []
        self._lows: list[float] = []
        self._closes: list[float] = []
        self._volumes: list[float] = []
        self._warmed = False
        self._last_snapshot: dict[str, float] = {}

    def _warm_start(self) -> None:
        history = self._load_history(self._instrument_id, self._tf, WARM_START_BARS)
        # Cast to float: production candles carry Decimal OHLCV (see app.ingest.candle),
        # and the indicator arithmetic below assumes plain floats.
        self._opens = [float(c.o) for c in history]
        self._highs = [float(c.h) for c in history]
        self._lows = [float(c.l) for c in history]
        self._closes = [float(c.c) for c in history]
        self._volumes = [float(c.v) for c in history]
        self._warmed = True

    def update(self, candle: CandleLike) -> dict[str, float]:
        if not self._warmed:
            self._warm_start()
        self._opens.append(float(candle.o))
        self._highs.append(float(candle.h))
        self._lows.append(float(candle.l))
        self._closes.append(float(candle.c))
        self._volumes.append(float(candle.v))
        self._last_snapshot = self._recompute()
        return self._last_snapshot

    def recompute_from_history(self) -> dict[str, float]:
        """Warm-start (if needed) and compute the snapshot over the loaded rows
        as-is — the last row IS the just-closed bar. Use this when the closing
        candle is already persisted in history (the live path commits before
        dispatch); appending it again via ``update`` would double the last bar.
        """
        if not self._warmed:
            self._warm_start()
        self._last_snapshot = self._recompute()
        return self._last_snapshot

    def snapshot(self) -> dict[str, float]:
        return self._last_snapshot

    def _recompute(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for key in self._requested:
            parts = key.split(":")
            name = parts[0]
            if name == "rsi":
                period = int(parts[1])
                out[key] = ind.rsi(self._closes, period=period)[-1]
            elif name == "ema":
                period = int(parts[1])
                out[key] = ind.ema(self._closes, period=period)[-1]
            elif name == "sma":
                period = int(parts[1])
                out[key] = ind.sma(self._closes, period=period)[-1]
            elif name == "vwap":
                out[key] = ind.vwap(self._highs, self._lows, self._closes, self._volumes)[-1]
            elif name == "atr":
                period = int(parts[1])
                # Guard: atr() indexes tr[0] and raises IndexError on an empty
                # series, and yields no defined value until `period` bars exist.
                # Return NaN gracefully (matching bollinger/rel_volume) instead
                # of crashing on a newly-listed / thinly-warmed symbol.
                if len(self._closes) < period:
                    out[key] = NAN
                else:
                    out[key] = ind.atr(self._highs, self._lows, self._closes, period=period)[-1]
            elif name == "adx":
                period = int(parts[1])
                # Guard: adx() needs enough bars for the DX warm-up; short series
                # raise IndexError. Return NaN gracefully until warmed.
                if len(self._closes) < period:
                    out[key] = NAN
                else:
                    out[key] = ind.adx(self._highs, self._lows, self._closes, period=period)[-1]
            elif name == "rel_volume":
                period = int(parts[1])
                out[key] = ind.rel_volume(self._volumes, period=period)[-1]
            elif name == "gap_pct":
                prev_closes = [self._closes[0]] + self._closes[:-1]
                out[key] = ind.gap_pct(self._opens, prev_closes)[-1]
            elif name in ("bollinger_mid", "bollinger_upper", "bollinger_lower"):
                period, std_mult = int(parts[1]), float(parts[2])
                mid, upper, lower = ind.bollinger(
                    self._closes, period=period, std_mult=std_mult
                )
                out[key] = {
                    "bollinger_mid": mid,
                    "bollinger_upper": upper,
                    "bollinger_lower": lower,
                }[name][-1]
        return out


class IndicatorCache:
    def __init__(self, load_history: LoadHistory, requested_indicators: list[str]):
        self._load_history = load_history
        self._requested = requested_indicators
        self._instances: dict[tuple[int, str], InstrumentTfCache] = {}

    def get_or_create(self, instrument_id: int, tf: str) -> InstrumentTfCache:
        key = (instrument_id, tf)
        if key not in self._instances:
            self._instances[key] = InstrumentTfCache(
                instrument_id, tf, self._load_history, self._requested
            )
        return self._instances[key]
