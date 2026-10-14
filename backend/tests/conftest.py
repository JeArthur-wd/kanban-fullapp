import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from app.routes.auth import login_limiter
from app.routes.chat import chat_limiter

CREDENTIALS = {"username": "user", "password": "password"}


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    login_limiter.reset()
    chat_limiter.reset()


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
    response = anon_client.post("/api/login", json=CREDENTIALS)
    assert response.status_code == 200
    return anon_client
