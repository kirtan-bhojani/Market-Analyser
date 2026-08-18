"""Post-flush fan-out: turn freshly-persisted closed candles into candle-close
compute jobs.

The ingest flush loop persists closed candles and, once committed, calls
``dispatch_close_jobs`` to enqueue the downstream strategy / scanner jobs via
the arq pool. Enqueue is gated by what is actually active so a large universe
does not flood arq with jobs that would immediately no-op:

  * strategy job  -> only for an ``(instrument_id, tf)`` that has an enabled
    ``StrategyConfig``.
  * scanner job   -> only when an enabled ``ScanRule`` references this ``tf``
    (rules are global, not per-instrument; the job itself re-filters + dedups).

Both downstream jobs are idempotent (per-bar Redis dedup keys), so a re-flushed
or retried candle re-enqueuing the same job never double-emits a signal/hit.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Protocol

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingest.candle import Candle
from app.ml.grouping import instrument_group_for
from app.models.ml_model import MLModel
from app.models.scan_rule import ScanRule
from app.models.strategy_config import StrategyConfig
from app.scanner.dsl import parse_rule_definition
from app.scanner.evaluator import compile_rule
from app.scanner.history import load_recent_candles

logger = logging.getLogger(__name__)

# ML models are trained on 1h bars (see app/ml/train.py + tests), and MLModel
# carries no tf column, so inference is triggered on 1h closes only.
ML_INFERENCE_TF = "1h"
ML_WINDOW_BARS = 250
# Below this many 1h bars build_features drops everything (warmup windows), so
# don't bother shipping a window that would immediately no-op.
MIN_ML_BARS = 30


class SupportsEnqueue(Protocol):
    async def enqueue_job(self, function: str, *args: Any) -> Any: ...

    async def aclose(self) -> None: ...


def _candle_dict(candle: Candle) -> dict[str, Any]:
    """Serialize a Candle for the scanner job (same shape as the WS payload)."""
    return {
        "ts": candle.ts.isoformat(),
        "o": float(candle.o),
        "h": float(candle.h),
        "l": float(candle.l),
        "c": float(candle.c),
        "v": float(candle.v),
    }


async def _active_strategy_scopes(session: AsyncSession) -> set[tuple[int, str]]:
    result = await session.execute(
        select(StrategyConfig.instrument_id, StrategyConfig.tf).where(
            StrategyConfig.enabled.is_(True)
        )
    )
    return {(iid, tf) for iid, tf in result.all()}


async def _active_scan_tfs(session: AsyncSession) -> set[str]:
    result = await session.execute(select(ScanRule).where(ScanRule.enabled.is_(True)))
    tfs: set[str] = set()
    for rule in result.scalars().all():
        try:
            compiled = compile_rule(parse_rule_definition(rule.definition))
        except Exception:
            # A malformed rule must not sink the whole flush fan-out; skip it.
            logger.warning("dispatch: skipping unparseable scan rule id=%s", rule.id)
            continue
        tfs.update(tf for _, tf in compiled.required_indicators())
    return tfs


async def _published_models_by_group(session: AsyncSession) -> dict[str, list[str]]:
    result = await session.execute(select(MLModel).where(MLModel.published.is_(True)))
    by_group: dict[str, list[str]] = defaultdict(list)
    for model in result.scalars().all():
        by_group[model.instrument_group].append(str(model.id))
    return by_group


async def _ml_window(
    session: AsyncSession, instrument_id: int
) -> pd.DataFrame | None:
    rows = await load_recent_candles(
        session, instrument_id, ML_INFERENCE_TF, ML_WINDOW_BARS
    )
    if len(rows) < MIN_ML_BARS:
        return None
    return pd.DataFrame(
        {
            "o": [float(r.o or 0) for r in rows],
            "h": [float(r.h or 0) for r in rows],
            "l": [float(r.l or 0) for r in rows],
            "c": [float(r.c or 0) for r in rows],
            "v": [float(r.v or 0) for r in rows],
        },
        index=pd.DatetimeIndex([r.ts for r in rows]),
    )


async def dispatch_close_jobs(
    arq_pool: SupportsEnqueue,
    session: AsyncSession,
    batch: dict[str, list[Candle]],
    symbol_to_instrument_id: dict[str, int],
) -> int:
    """Enqueue candle-close jobs for each closed candle in ``batch``.

    Returns the number of jobs enqueued (for logging / tests).
    """
    strategy_scopes = await _active_strategy_scopes(session)
    scan_tfs = await _active_scan_tfs(session)
    # Loaded lazily: only pay for the model query when a 1h candle is present.
    models_by_group: dict[str, list[str]] | None = None

    enqueued = 0
    for symbol, candles in batch.items():
        instrument_id = symbol_to_instrument_id.get(symbol)
        if instrument_id is None:
            continue
        for candle in candles:
            tf = candle.tf
            if (instrument_id, tf) in strategy_scopes:
                await arq_pool.enqueue_job("on_candle_close_job", instrument_id, tf)
                enqueued += 1
            if tf in scan_tfs:
                await arq_pool.enqueue_job(
                    "scan_on_candle_close_job",
                    instrument_id,
                    tf,
                    _candle_dict(candle),
                )
                enqueued += 1
            if tf == ML_INFERENCE_TF:
                if models_by_group is None:
                    models_by_group = await _published_models_by_group(session)
                model_ids = models_by_group.get(instrument_group_for(symbol), [])
                if model_ids:
                    window = await _ml_window(session, instrument_id)
                    if window is not None:
                        for model_id in model_ids:
                            await arq_pool.enqueue_job(
                                "run_ml_inference_job",
                                model_id,
                                instrument_id,
                                window,
                            )
                            enqueued += 1
    return enqueued
