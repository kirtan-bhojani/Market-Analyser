import uuid

import pytest


@pytest.mark.asyncio
async def test_get_ml_model_returns_fold_metrics_and_baseline_comparison(client, db_session):
    from app.models.ml_model import MLModel

    model_id = uuid.uuid4()
    model = MLModel(
        id=model_id,
        instrument_group="crypto_majors",
        version="v1",
        artifact_path="/data/ml_models/crypto_majors_v1.pkl",
        metrics={
            "fold_metrics": [{"fold": 0, "n_train": 100, "n_test": 20, "accuracy": 0.62}],
            "feature_importances": {"ret_1": 12.0, "rsi_14": 8.0},
            "model_net_return": 0.15,
            "buy_hold_return": 0.06,
            "random_return": 0.01,
            "threshold": 0.55,
        },
        published=True,
    )
    db_session.add(model)
    await db_session.commit()

    resp = await client.get(f"/ml/models/{model_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["published"] is True
    assert body["fold_metrics"][0]["accuracy"] == pytest.approx(0.62)
    assert body["model_net_return"] > body["buy_hold_return"]
    assert body["model_net_return"] > body["random_return"]


@pytest.mark.asyncio
async def test_get_ml_model_404_when_missing(client):
    resp = await client.get(f"/ml/models/{uuid.uuid4()}")
    assert resp.status_code == 404
