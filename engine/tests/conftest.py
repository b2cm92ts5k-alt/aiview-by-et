from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.app import create_app
from app.data.service import DataService

from .fakes import FakeProvider


@pytest.fixture()
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test.sqlite3")


@pytest.fixture()
def fake_provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture()
def client(db_path: str, fake_provider: FakeProvider) -> Iterator[TestClient]:
    app = create_app(db_path, data_service=DataService([fake_provider]))
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def secured_client(db_path: str, fake_provider: FakeProvider) -> Iterator[TestClient]:
    app = create_app(db_path, token="secret-token", data_service=DataService([fake_provider]))
    with TestClient(app) as c:
        yield c
