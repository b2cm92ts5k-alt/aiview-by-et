from fastapi.testclient import TestClient


def test_settings_empty_by_default(client: TestClient) -> None:
    assert client.get("/settings").json() == {}


def test_put_and_get_roundtrip(client: TestClient) -> None:
    res = client.put("/settings", json={"theme": "dark", "tf": "15m"})
    assert res.status_code == 200
    assert res.json() == {"theme": "dark", "tf": "15m"}
    assert client.get("/settings").json() == {"theme": "dark", "tf": "15m"}


def test_put_merges_not_replaces(client: TestClient) -> None:
    client.put("/settings", json={"theme": "dark"})
    client.put("/settings", json={"tf": "15m"})
    assert client.get("/settings").json() == {"theme": "dark", "tf": "15m"}


def test_null_deletes_key(client: TestClient) -> None:
    client.put("/settings", json={"theme": "dark"})
    client.put("/settings", json={"theme": None})
    assert client.get("/settings").json() == {}


def test_nested_json_values(client: TestClient) -> None:
    payload = {"layout": {"panels": ["chart", "signals"], "width": 320}}
    client.put("/settings", json=payload)
    assert client.get("/settings").json() == payload
