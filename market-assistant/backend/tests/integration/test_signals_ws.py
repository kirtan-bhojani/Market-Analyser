import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import create_app

# In the test env the WS token is accepted as a raw user UUID
# (get_current_user_id_from_ws_token non-prod fallback). Channels are keyed by
# symbol:tf, so any valid token admits the connection.
TOKEN = uuid.uuid4()
SIGNALS_URL = f"/ws/signals?token={TOKEN}"


def test_ws_subscribe_receives_published_signal(redis_sync_client):
    with TestClient(create_app()) as client:
        with client.websocket_connect(SIGNALS_URL) as ws:
            ws.send_json({"subscribe": "signals:BTC/USDT:15m"})
            time.sleep(0.2)  # let the server complete SUBSCRIBE before we publish

            signal = {
                "id": 1,
                "instrument_id": 1,
                "strategy": "orb",
                "direction": "long",
                "ts": "2024-01-01T10:15:00Z",
                "confidence": None,
                "ref_entry": 107.0,
                "ref_sl": 100.0,
                "ref_tp": 121.0,
                "backtest_ref": None,
                "meta": {"or_high": 105, "or_low": 100},
            }
            redis_sync_client.publish("signals:BTC/USDT:15m", json.dumps(signal))

            received = json.loads(ws.receive_text())
            assert received == signal


def test_ws_resubscribe_stops_forwarding_old_channel(redis_sync_client):
    with TestClient(create_app()) as client:
        with client.websocket_connect(SIGNALS_URL) as ws:
            ws.send_json({"subscribe": "signals:BTC/USDT:15m"})
            time.sleep(0.2)
            ws.send_json({"subscribe": "signals:ETH/USDT:15m"})
            time.sleep(0.2)

            redis_sync_client.publish("signals:BTC/USDT:15m", json.dumps({"stale": True}))
            eth_signal = {"id": 2, "strategy": "orb", "direction": "short"}
            redis_sync_client.publish("signals:ETH/USDT:15m", json.dumps(eth_signal))

            received = json.loads(ws.receive_text())
            assert received == eth_signal


def test_ws_rejects_missing_token():
    # No ?token= -> FastAPI's required Query(...) rejects the handshake before
    # accept(); Starlette's TestClient surfaces that as WebSocketDisconnect.
    with TestClient(create_app()) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/signals"):
                pass


def test_ws_rejects_invalid_token():
    # A non-UUID token fails both JWT verification and the raw-UUID fallback, so
    # authenticate_ws closes the handshake (1008) before accept().
    with TestClient(create_app()) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/signals?token=not-a-valid-token"):
                pass


def test_ws_rejects_foreign_channel_subscribe(redis_sync_client):
    # C3: the /ws/signals route may only subscribe to `signals:*`. A subscribe to
    # another user's private `scan_hits:<uuid>` (or any non-signals channel) must
    # be rejected — else any authed client could tap another user's scan feed.
    other_user = uuid.uuid4()
    with TestClient(create_app()) as client:
        with client.websocket_connect(SIGNALS_URL) as ws:
            ws.send_json({"subscribe": f"scan_hits:{other_user}"})
            with pytest.raises(WebSocketDisconnect):
                ws.receive_text()
