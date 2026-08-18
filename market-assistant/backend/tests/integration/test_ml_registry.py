import uuid

import pytest

from app.ml.registry import load_artifact, save_artifact
from app.models.ml_model import MLModel


def test_save_and_load_artifact_round_trips_on_tmp_volume(tmp_path):
    obj = {"weights": [1, 2, 3], "kind": "dummy"}

    path = save_artifact(obj, instrument_group="crypto_majors", version="v1", base_dir=tmp_path)

    assert path.startswith(str(tmp_path))
    loaded = load_artifact(path)
    assert loaded == obj


@pytest.mark.asyncio
async def test_ml_model_defaults_to_unpublished(db_session):
    model = MLModel(
        id=uuid.uuid4(),
        instrument_group="crypto_majors",
        version="v1",
        artifact_path="/data/ml_models/crypto_majors_v1.pkl",
        metrics={"fold_metrics": []},
    )
    db_session.add(model)
    await db_session.commit()

    fetched = await db_session.get(MLModel, model.id)
    assert fetched.published is False
    assert fetched.strategy == "ml_lgbm_v1"
