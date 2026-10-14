import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setenv("PM_DB_PATH", str(path))
    init_db()
    return path


@pytest.fixture
def anon_client(db_path):
    return TestClient(app)


@pytest.fixture
def client(anon_client):
    return anon_client
