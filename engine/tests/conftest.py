from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.sqlite3")


@pytest.fixture()
def client(db_path: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_path)) as c:
        yield c


@pytest.fixture()
def secured_client(db_path: str) -> Iterator[TestClient]:
    with TestClient(create_app(db_path, token="secret-token")) as c:
        yield c
