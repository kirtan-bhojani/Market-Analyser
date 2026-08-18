import pytest


@pytest.mark.acceptance
async def test_health_reports_db_and_redis_up(test_client):
    response = await test_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] is True
    assert body["redis"] is True
