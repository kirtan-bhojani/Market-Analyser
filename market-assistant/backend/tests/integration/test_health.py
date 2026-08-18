import pytest


@pytest.mark.asyncio
async def test_health_endpoint(test_client):
    response = await test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": True, "redis": True}
