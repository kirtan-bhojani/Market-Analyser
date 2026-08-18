async def test_create_and_list_sessions_scoped_to_user(client, auth_headers, other_user_headers):
    resp = await client.post("/api/chat/sessions", headers=auth_headers)
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    resp_a = await client.get("/api/chat/sessions", headers=auth_headers)
    assert any(s["id"] == session_id for s in resp_a.json())

    resp_b = await client.get("/api/chat/sessions", headers=other_user_headers)
    assert all(s["id"] != session_id for s in resp_b.json())


async def test_get_messages_empty_for_new_session(client, auth_headers):
    resp = await client.post("/api/chat/sessions", headers=auth_headers)
    session_id = resp.json()["id"]
    msgs = await client.get(f"/api/chat/sessions/{session_id}/messages", headers=auth_headers)
    assert msgs.json() == []
