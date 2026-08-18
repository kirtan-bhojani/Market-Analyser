import contextlib
import json
import time
import uuid

from fastapi.testclient import TestClient

from app.main import create_app

# Number of simultaneous browser clients on the same scan_hits channel.
N_CLIENTS = 10
# Generous wall-clock bound (publish -> last client receives). Redis pub/sub
# fan-out to 10 local sockets is milliseconds; 2s leaves huge CI headroom yet
# still trips if fan-out regresses to serialized/blocking delivery.
LATENCY_BOUND_S = 2.0


def test_scanner_hits_ws_fans_out_to_n_concurrent_clients(redis_sync_client):
    # Fresh user id -> collision-free channel across runs. In test env the WS
    # token is accepted as a raw user UUID (get_current_user_id_from_ws_token).
    user_id = uuid.uuid4()
    channel = f"scan_hits:{user_id}"
    url = f"/ws/scanner/hits?token={user_id}"

    hit = {
        "rule_id": 42,
        "instrument_id": 7,
        "symbol": "BTC/USDT",
        "tf": "1m",
        "bar_ts": "2024-01-01T00:01:00Z",
        "rule_name": "rsi_dip_volume_spike",
    }

    with TestClient(create_app()) as client:
        with contextlib.ExitStack() as stack:
            # Open N simultaneous websockets. Starlette's TestClient runs each
            # websocket in its own portal thread, so all N are held open and
            # subscribed at once (each connection opens its own redis.pubsub()
            # and SUBSCRIBEs to the shared channel).
            sockets = [
                stack.enter_context(client.websocket_connect(url))
                for _ in range(N_CLIENTS)
            ]

            # Let every server-side connection complete its SUBSCRIBE before we
            # publish, otherwise a socket could miss the (fire-and-forget) event.
            time.sleep(0.5)

            # Confirm the fan-out sees all N subscribers before publishing, so
            # the test genuinely exercises N concurrent sockets (not fewer).
            subscribers = redis_sync_client.execute_command(
                "PUBSUB", "NUMSUB", channel
            )
            assert subscribers[1] == N_CLIENTS, (
                f"expected {N_CLIENTS} subscribers on {channel}, got {subscribers[1]}"
            )

            # One PUBLISH; Redis natively delivers it to every subscriber.
            start = time.perf_counter()
            delivered = redis_sync_client.publish(channel, json.dumps(hit))
            assert delivered == N_CLIENTS

            # Every client must receive the exact payload.
            for ws in sockets:
                received = json.loads(ws.receive_text())
                assert received == hit
            elapsed = time.perf_counter() - start

    assert elapsed < LATENCY_BOUND_S, (
        f"fan-out to {N_CLIENTS} clients took {elapsed:.3f}s (>{LATENCY_BOUND_S}s)"
    )
