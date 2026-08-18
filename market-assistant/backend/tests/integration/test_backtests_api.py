import pytest

from app.core.deps import get_arq_pool


class _FakePool:
    async def enqueue_job(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def _override_arq(app):
    app.dependency_overrides[get_arq_pool] = lambda: _FakePool()
    yield
    app.dependency_overrides.pop(get_arq_pool, None)


@pytest.mark.asyncio
async def test_post_backtests_rejects_zero_fees_bps(client):
    payload = {
        "strategy": "sma_cross",
        "params": {"fast": 3, "slow": 8},
        "universe": {"symbol": "BTC/USDT", "tf": "1h"},
        "start_ts": "2024-01-01T00:00:00Z",
        "end_ts": "2024-06-01T00:00:00Z",
        "fees_bps": 0,
        "slippage_bps": 5,
    }
    resp = await client.post("/backtests", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_backtests_rejects_missing_slippage_bps(client):
    payload = {
        "strategy": "sma_cross",
        "params": {"fast": 3, "slow": 8},
        "universe": {"symbol": "BTC/USDT", "tf": "1h"},
        "start_ts": "2024-01-01T00:00:00Z",
        "end_ts": "2024-06-01T00:00:00Z",
        "fees_bps": 10,
    }
    resp = await client.post("/backtests", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_backtests_valid_request_enqueues_job(client):
    payload = {
        "strategy": "sma_cross",
        "params": {"fast": 3, "slow": 8},
        "universe": {"symbol": "BTC/USDT", "tf": "1h"},
        "start_ts": "2024-01-01T00:00:00Z",
        "end_ts": "2024-06-01T00:00:00Z",
        "fees_bps": 10,
        "slippage_bps": 5,
    }
    resp = await client.post("/backtests", json=payload)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "pending"
    assert "id" in body

    get_resp = await client.get(f"/backtests/{body['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == body["id"]
