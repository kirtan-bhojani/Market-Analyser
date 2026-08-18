import uuid

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import select

from app.ml.registry import save_artifact
from app.models.instrument import Instrument
from app.models.ml_model import MLModel
from app.models.signal import Signal
from app.workers.ml_inference_worker import run_ml_inference_job


async def _seed_instrument(db_session) -> int:
    instrument = Instrument(
        symbol="BTC/USDT", asset_class="crypto", exchange="binance", active=True
    )
    db_session.add(instrument)
    await db_session.flush()
    return instrument.id


class _AlwaysUpModel:
    def predict_proba(self, X):
        n = len(X)
        return np.column_stack([np.zeros(n), np.ones(n)])


def _candles_window(n=40, seed=3):
    idx = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    rng = np.random.default_rng(seed)
    close = 100.0 + np.cumsum(rng.normal(0.1, 1.0, n))
    return pd.DataFrame(
        {
            "o": close,
            "h": close + 0.5,
            "l": close - 0.5,
            "c": close,
            "v": 100.0 + rng.normal(0, 5, n),
        },
        index=idx,
    )


@pytest.mark.asyncio
async def test_unpublished_model_emits_no_signal(db_session, tmp_path):
    artifact_path = save_artifact(
        {"model": _AlwaysUpModel(), "calibrator": None}, "crypto_majors", "unpub", base_dir=tmp_path
    )
    ml_model = MLModel(
        id=uuid.uuid4(),
        instrument_group="crypto_majors",
        version="unpub",
        artifact_path=artifact_path,
        metrics={"threshold": 0.55},
        published=False,
    )
    db_session.add(ml_model)
    await db_session.commit()

    ctx = {"db_session": db_session}
    await run_ml_inference_job(
        ctx, str(ml_model.id), instrument_id=1, candles_window=_candles_window()
    )

    result = await db_session.execute(select(Signal).where(Signal.strategy == "ml_lgbm_v1"))
    assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_published_model_emits_signal_with_calibrated_confidence(db_session, tmp_path):
    artifact_path = save_artifact(
        {"model": _AlwaysUpModel(), "calibrator": None}, "crypto_majors", "pub", base_dir=tmp_path
    )
    ml_model = MLModel(
        id=uuid.uuid4(),
        instrument_group="crypto_majors",
        version="pub",
        artifact_path=artifact_path,
        metrics={"threshold": 0.55},
        published=True,
    )
    instrument_id = await _seed_instrument(db_session)
    db_session.add(ml_model)
    await db_session.commit()

    ctx = {"db_session": db_session}
    await run_ml_inference_job(
        ctx, str(ml_model.id), instrument_id=instrument_id, candles_window=_candles_window()
    )

    result = await db_session.execute(select(Signal).where(Signal.strategy == "ml_lgbm_v1"))
    signals = result.scalars().all()
    assert len(signals) == 1
    assert float(signals[0].confidence) == pytest.approx(1.0)
    assert signals[0].instrument_id == instrument_id
