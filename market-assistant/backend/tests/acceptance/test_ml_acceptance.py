import time
import uuid

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from app.ml.baseline import passes_baseline_gate
from app.ml.registry import save_artifact
from app.ml.train import train_model
from app.models.instrument import Instrument
from app.models.ml_model import MLModel
from app.models.signal import Signal
from app.workers.ml_inference_worker import run_ml_inference_job


def _twelve_months_hourly_btc_like_series(seed=11):
    n = 24 * 365  # 1h bars for 12 months
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.default_rng(seed)
    drift = np.linspace(0, 15, n)  # mild uptrend, like a real 12-month BTC window
    noise = np.cumsum(rng.normal(0, 1.0, n))
    close = 30_000.0 + drift * 100 + noise * 50
    return pd.DataFrame(
        {
            "o": close,
            "h": close + 20,
            "l": close - 20,
            "c": close,
            "v": 100.0 + rng.normal(0, 10, n),
        },
        index=idx,
    )


class _AlwaysUpModel:
    def predict_proba(self, X):
        n = len(X)
        return np.column_stack([np.zeros(n), np.ones(n)])


class _AlwaysDownModel:
    def predict_proba(self, X):
        n = len(X)
        return np.column_stack([np.ones(n), np.zeros(n)])


@pytest.mark.acceptance
def test_twelve_month_btc_1h_train_end_to_end_completes_and_gates_correctly(tmp_path):
    candles = _twelve_months_hourly_btc_like_series()

    start = time.monotonic()
    result = train_model(
        candles=candles,
        regime=None,
        instrument_group="crypto_majors",
        version="acceptance-v1",
        horizon=4,
        n_splits=6,
        test_size=200,
        purge=4,
        fees_bps=10.0,
        slippage_bps=5.0,
        threshold=0.55,
        artifact_base_dir=tmp_path,
    )
    elapsed = time.monotonic() - start

    assert (
        elapsed < 300.0
    )  # 12 months of 1h LightGBM CV must finish well inside a free-tier CI budget
    assert len(result.fold_metrics) == 6
    assert result.published == passes_baseline_gate(
        result.model_net_return, result.buy_hold_return, result.random_return
    )


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_unpublished_model_stays_silent_in_replay(db_session, tmp_path):
    artifact_path = save_artifact(
        {"model": _AlwaysDownModel(), "calibrator": None},
        "crypto_majors",
        "silent",
        base_dir=tmp_path,
    )
    ml_model = MLModel(
        id=uuid.uuid4(),
        instrument_group="crypto_majors",
        version="silent",
        artifact_path=artifact_path,
        metrics={"threshold": 0.55},
        published=False,
    )
    db_session.add(ml_model)
    await db_session.commit()

    candles = _twelve_months_hourly_btc_like_series().iloc[-50:]
    await run_ml_inference_job(
        {"db_session": db_session}, str(ml_model.id), instrument_id=1, candles_window=candles
    )

    result = await db_session.execute(select(Signal).where(Signal.strategy == "ml_lgbm_v1"))
    assert result.scalars().all() == []


@pytest.mark.acceptance
@pytest.mark.asyncio
async def test_published_model_emits_in_replay_with_confidence_shown(db_session, tmp_path):
    artifact_path = save_artifact(
        {"model": _AlwaysUpModel(), "calibrator": None}, "crypto_majors", "live", base_dir=tmp_path
    )
    ml_model = MLModel(
        id=uuid.uuid4(),
        instrument_group="crypto_majors",
        version="live",
        artifact_path=artifact_path,
        metrics={
            "threshold": 0.55,
            "model_net_return": 0.2,
            "buy_hold_return": 0.05,
            "random_return": 0.01,
        },
        published=True,
    )
    instrument = Instrument(
        symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()
    db_session.add(ml_model)
    await db_session.commit()

    candles = _twelve_months_hourly_btc_like_series().iloc[-50:]
    await run_ml_inference_job(
        {"db_session": db_session},
        str(ml_model.id),
        instrument_id=instrument.id,
        candles_window=candles,
    )

    result = await db_session.execute(select(Signal).where(Signal.strategy == "ml_lgbm_v1"))
    signals = result.scalars().all()
    assert len(signals) == 1
    assert signals[0].confidence is not None
    assert 0.0 <= float(signals[0].confidence) <= 1.0
    assert signals[0].meta["baseline"]["buy_hold_return"] == pytest.approx(0.05)
