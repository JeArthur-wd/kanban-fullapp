import pytest
from fastapi.testclient import TestClient

from app.accounts import ensure_demo_account
from app.database import connect_db, init_db
from app.main import app
from app.routes.auth import login_limiter, signup_limiter
from app.routes.chat import chat_limiter

CREDENTIALS = {"username": "user", "password": "password"}


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    login_limiter.reset()
    signup_limiter.reset()
    chat_limiter.reset()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "test.db"
    monkeypatch.setenv("PM_DB_PATH", str(path))
    init_db()
    conn = connect_db()
    ensure_demo_account(conn)
    conn.close()
    return path


@pytest.fixture
def anon_client(db_path):
    return TestClient(app)


@pytest.fixture
def client(anon_client):
    response = anon_client.post("/api/login", json=CREDENTIALS)
    assert response.status_code == 200
    return anon_client


@pytest.fixture
def board_url(client) -> str:
    """The demo user's first board, which holds the sample columns and cards."""
    return f"/api/boards/{client.get('/api/boards').json()[0]['id']}"


@pytest.fixture
def make_user(db_path):
    """Sign up another account and return a client signed in as it."""

    def _make(username: str, password: str = "another-pass") -> TestClient:
        other = TestClient(app)
        response = other.post("/api/register", json={"username": username, "password": password})
        assert response.status_code == 200, response.text
        return other

    return _make
