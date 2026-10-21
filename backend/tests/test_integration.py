import os
import secrets
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
    assert httpx.get(f"{BASE_URL}/api/boards", timeout=5).status_code == 401
    spoofed = httpx.get(f"{BASE_URL}/api/boards", headers={"X-User": "user"}, timeout=5)
    assert spoofed.status_code == 401
    chat = httpx.post(f"{BASE_URL}/api/boards/1/chat", json={"message": "hi"}, timeout=5)
    assert chat.status_code == 401


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_unknown_api_path_is_404() -> None:
    response = httpx.get(f"{BASE_URL}/api/does-not-exist", timeout=5)
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_signed_in_board() -> None:
    with _signed_in_client() as client:
        boards = client.get("/api/boards")
        assert boards.status_code == 200
        board = client.get(f"/api/boards/{boards.json()[0]['id']}")
        assert board.status_code == 200
        assert len(board.json()["columns"]) >= 1


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_sign_up_boards_and_account_deletion() -> None:
    username = f"live-{secrets.token_hex(4)}"
    password = "live-test-pass"
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        assert client.post(
            "/api/register", json={"username": username, "password": password}
        ).status_code == 200
        created = client.post("/api/boards", json={"title": "Live board"})
        assert created.status_code == 200
        board = client.get(f"/api/boards/{created.json()['id']}").json()
        card = client.post(
            "/api/cards",
            json={"column_id": int(board["columns"][0]["id"]), "title": "Live", "priority": "high"},
        )
        assert card.status_code == 200
        assert len(client.get("/api/boards").json()) == 2

        assert client.request("DELETE", "/api/me", json={"password": password}).status_code == 200
        assert client.get("/api/boards").status_code == 401
        relogin = client.post("/api/login", json={"username": username, "password": password})
        assert relogin.status_code == 401


@pytest.mark.skipif(not _can_run(), reason="PM_BASE_URL not set")
def test_live_concurrent_requests_do_not_fail() -> None:
    import asyncio

    async def _burst() -> list[int]:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
            await client.post("/api/login", json={"username": "user", "password": "password"})
            board_id = (await client.get("/api/boards")).json()[0]["id"]
            responses = await asyncio.gather(
                *(client.get(f"/api/boards/{board_id}") for _ in range(100))
            )
        return [response.status_code for response in responses]

    assert set(asyncio.run(_burst())) == {200}


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
        board_id = client.get("/api/boards").json()[0]["id"]
        response = client.post(
            f"/api/boards/{board_id}/chat",
            json={"message": "What is 2+2? Reply with only the number."},
        )
    assert response.status_code == 200
    payload = response.json()
    assert "response" in payload
    assert "4" in payload["response"]
