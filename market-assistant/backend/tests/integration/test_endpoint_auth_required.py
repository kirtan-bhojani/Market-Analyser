"""H1: write/compute endpoints must require auth; correlation limit must be bounded.

These endpoints accepted anonymous writes/compute (no ``get_current_user_id``
dependency), and ``GET /api/analytics/correlation`` took an unbounded ``limit``
(a single caller could ask for arbitrarily many rows per instrument).

Auth is proven by overriding ``get_current_user_id`` to reject: the override
only fires for a route that actually depends on it, so a route missing the
dependency returns its success code instead of 401. Bodies are valid so the
only possible failure is the auth rejection (never a 422 masking it).
"""

import pytest
from fastapi import HTTPException, status

from app.core.auth import get_current_user_id
from app.core.deps import get_arq_pool


class _FakePool:
    async def enqueue_job(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return None


def _reject() -> None:
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no auth")


@pytest.fixture
def no_auth(app):
    app.dependency_overrides[get_current_user_id] = _reject
    app.dependency_overrides[get_arq_pool] = lambda: _FakePool()
    yield
    app.dependency_overrides.pop(get_current_user_id, None)
    app.dependency_overrides.pop(get_arq_pool, None)


_VALID_BACKTEST = {
    "strategy": "sma_cross",
    "params": {"fast": 3, "slow": 8},
    "universe": {"symbol": "BTC/USDT", "tf": "1h"},
    "start_ts": "2024-01-01T00:00:00Z",
    "end_ts": "2024-06-01T00:00:00Z",
    "fees_bps": 10,
    "slippage_bps": 5,
}


@pytest.mark.asyncio
async def test_post_backtests_requires_auth(client, no_auth):
    resp = await client.post("/backtests", json=_VALID_BACKTEST)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_post_instruments_requires_auth(client, no_auth):
    resp = await client.post(
        "/api/instruments",
        json={"symbol": "AUTH/TEST", "asset_class": "crypto", "exchange": "e2e"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_seed_nifty50_requires_auth(client, no_auth):
    resp = await client.post("/api/instruments/seed-nifty50")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_patch_instrument_requires_auth(client, no_auth):
    resp = await client.patch("/api/instruments/1", json={"active": False})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mini_backtest_requires_auth(client, no_auth):
    resp = await client.post(
        "/api/strategies/sma_cross/backtest",
        json={"instrument_id": 1, "tf": "5m"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_correlation_limit_is_bounded(client):
    resp = await client.get(
        "/api/analytics/correlation", params={"asset_class": "crypto", "limit": 1_000_000}
    )
    assert resp.status_code == 422
