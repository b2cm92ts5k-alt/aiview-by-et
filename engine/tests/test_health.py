from fastapi.testclient import TestClient

from app import __version__


def test_health_ok(client: TestClient) -> None:
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


def test_health_needs_no_token(secured_client: TestClient) -> None:
    assert secured_client.get("/health").status_code == 200


def test_other_routes_require_token(secured_client: TestClient) -> None:
    assert secured_client.get("/settings").status_code == 401


def test_valid_token_passes(secured_client: TestClient) -> None:
    res = secured_client.get("/settings", headers={"X-Engine-Token": "secret-token"})
    assert res.status_code == 200


def test_wrong_token_rejected(secured_client: TestClient) -> None:
    res = secured_client.get("/settings", headers={"X-Engine-Token": "wrong"})
    assert res.status_code == 401
