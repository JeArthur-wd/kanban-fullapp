import os
from contextlib import contextmanager

import httpx
import pytest

BASE_URL = os.getenv("PM_BASE_URL", "")


def _can_run() -> bool:
    return bool(BASE_URL)


def _can_run_openrouter() -> bool:
    return bool(BASE_URL) and bool(os.getenv("OPENROUTER_API_KEY"))


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_health() -> None:
    response = httpx.get(f"{BASE_URL}/health", timeout=5)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_root() -> None:
    response = httpx.get(f"{BASE_URL}/", timeout=5)
    assert response.status_code == 200
    assert "Kanban Studio" in response.text


@contextmanager
def _signed_in_client():
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        response = client.post("/api/login", json={"username": "user", "password": "password"})
        assert response.status_code == 200
        yield client


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_api_requires_sign_in() -> None:
    assert httpx.get(f"{BASE_URL}/api/board", timeout=5).status_code == 401
    spoofed = httpx.get(f"{BASE_URL}/api/board", headers={"X-User": "user"}, timeout=5)
    assert spoofed.status_code == 401
    assert httpx.post(f"{BASE_URL}/api/chat", json={"message": "hi"}, timeout=5).status_code == 401


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_signed_in_board() -> None:
    with _signed_in_client() as client:
        response = client.get("/api/board")
        assert response.status_code == 200
        assert len(response.json()["columns"]) >= 1


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_static_path_traversal_is_blocked() -> None:
    for path in [
        "/%2e%2e/%2e%2e/%2e%2e/etc/passwd",
        "//etc/passwd",
        "/../../../etc/passwd",
        "/%2e%2e/%2e%2e/backend/app/main.py",
    ]:
        # --path-as-is behaviour: build the request so the client does not normalize the path.
        request = httpx.Request("GET", f"{BASE_URL}/")
        request.url = request.url.copy_with(raw_path=path.encode())
        with httpx.Client(timeout=5) as client:
            response = client.send(request)
        assert "root:" not in response.text, path
        assert "FastAPI" not in response.text, path


@pytest.mark.skipif(not _can_run_openrouter(), reason="PM_BASE_URL or OPENROUTER_API_KEY not set")
def test_live_chat_openrouter() -> None:
    with _signed_in_client() as client:
        response = client.post(
            "/api/chat",
            json={"message": "What is 2+2? Reply with only the number."},
        )
    assert response.status_code == 200
    payload = response.json()
    assert "response" in payload
    assert "4" in payload["response"]
