from fastapi.testclient import TestClient

from app import __version__
from app.api.app import create_app


def test_ws_hello_envelope(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "engine.hello"
        assert isinstance(msg["ts"], int)
        assert msg["payload"]["version"] == __version__


def test_ws_ping_pong(client: TestClient) -> None:
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # hello
        ws.send_text("ping")
        assert ws.receive_json()["type"] == "pong"


def test_ws_requires_token_when_secured(db_path: str) -> None:
    with TestClient(create_app(db_path, token="secret-token")) as client:
        with client.websocket_connect("/ws?token=secret-token") as ws:
            assert ws.receive_json()["type"] == "engine.hello"
