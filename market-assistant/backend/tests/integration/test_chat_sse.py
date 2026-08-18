import json


async def test_sse_endpoint_streams_incremental_tokens(client, auth_headers, monkeypatch):
    resp = await client.post("/api/chat/sessions", headers=auth_headers)
    session_id = resp.json()["id"]

    from app.chat import orchestrator

    class FakeResult:
        answer = (
            "BTC is trading sideways. Educational analysis. Not investment advice. "
            "Past performance ≠ future results."
        )
        tool_events = []
        regenerated = False

    async def fake_run_chat_turn(db, sid, message, provider=None, quota_guard=None):
        return FakeResult()

    monkeypatch.setattr(orchestrator, "run_chat_turn", fake_run_chat_turn)

    async with client.stream(
        "POST",
        f"/api/chat/sessions/{session_id}/turns",
        json={"message": "how is BTC?"},
        headers=auth_headers,
    ) as stream_resp:
        assert stream_resp.status_code == 200
        assert stream_resp.headers["content-type"].startswith("text/event-stream")
        events = [
            json.loads(line[len("data: "):])
            async for line in stream_resp.aiter_lines()
            if line.startswith("data: ")
        ]
    assert events[-1]["type"] == "done"
    assert any(e["type"] == "token" for e in events)


async def test_turn_forbidden_for_non_owner(client, auth_headers, other_user_headers):
    resp = await client.post("/api/chat/sessions", headers=auth_headers)
    session_id = resp.json()["id"]
    forbidden = await client.post(
        f"/api/chat/sessions/{session_id}/turns",
        json={"message": "hi"},
        headers=other_user_headers,
    )
    assert forbidden.status_code == 404
