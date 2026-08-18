async def test_rate_limit_blocks_after_cap(client, auth_headers, monkeypatch):
    resp = await client.post("/api/chat/sessions", headers=auth_headers)
    session_id = resp.json()["id"]

    import app.api.chat as chat_api

    async def always_over(user_id, **kwargs):
        return False

    monkeypatch.setattr(chat_api, "check_rate_limit", always_over)

    resp = await client.post(
        f"/api/chat/sessions/{session_id}/turns",
        json={"message": "hi"},
        headers=auth_headers,
    )
    assert resp.status_code == 429
    assert "rate limit" in resp.json()["detail"].lower()


async def test_check_rate_limit_counts_and_expires(redis_client):
    import uuid

    from app.chat.rate_limit import check_rate_limit

    # Unique user id per run so the fixed-window key can't collide with a stale
    # key left in the shared Redis instance by a prior run within the window.
    user = f"ratelimit-test-{uuid.uuid4()}"
    for _ in range(3):
        assert await check_rate_limit(user, limit=3, window_seconds=60) is True
    assert await check_rate_limit(user, limit=3, window_seconds=60) is False
