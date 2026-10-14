import json

import app.ai.client as ai_module
from app.auth import create_session_token, read_session_token
from app.config import (
    CHAT_HISTORY_MAX_ITEMS,
    CHAT_MESSAGE_MAX_CHARS,
    CHAT_RATE_LIMIT,
    LOGIN_RATE_LIMIT,
)


def test_api_requires_sign_in(anon_client) -> None:
    assert anon_client.get("/api/board").status_code == 401
    assert anon_client.get("/api/session").status_code == 401
    assert anon_client.post("/api/chat", json={"message": "hi"}).status_code == 401
    assert anon_client.post("/api/cards", json={"column_id": 1, "title": "x"}).status_code == 401
    assert anon_client.delete("/api/cards/1").status_code == 401


def test_x_user_header_no_longer_grants_access(anon_client) -> None:
    response = anon_client.get("/api/board", headers={"X-User": "someone-else"})
    assert response.status_code == 401


def test_login_sets_http_only_cookie(anon_client) -> None:
    response = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert response.json() == {"username": "user"}
    cookie = response.headers["set-cookie"].lower()
    assert "pm_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert anon_client.get("/api/session").json() == {"username": "user"}


def test_login_cookie_is_secure_behind_https_proxy(anon_client) -> None:
    response = anon_client.post(
        "/api/login",
        json={"username": "user", "password": "password"},
        headers={"X-Forwarded-Proto": "https"},
    )
    assert "secure" in response.headers["set-cookie"].lower()


def test_login_rejects_wrong_credentials(anon_client) -> None:
    for creds in [
        {"username": "user", "password": "wrong"},
        {"username": "other", "password": "password"},
    ]:
        response = anon_client.post("/api/login", json=creds)
        assert response.status_code == 401
        assert "pm_session" not in response.headers.get("set-cookie", "")
    assert anon_client.get("/api/board").status_code == 401


def test_login_is_rate_limited(anon_client) -> None:
    for _ in range(LOGIN_RATE_LIMIT):
        bad = anon_client.post("/api/login", json={"username": "u", "password": "x"})
        assert bad.status_code == 401
    response = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 429


def test_logout_clears_the_session(client) -> None:
    assert client.get("/api/board").status_code == 200
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/board").status_code == 401


def test_tampered_or_expired_tokens_are_rejected() -> None:
    token = create_session_token("user", now=1_000_000)
    assert read_session_token(token, now=1_000_001) == "user"
    assert read_session_token(token, now=1_000_000 + 10 * 24 * 3600) is None
    flipped = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert read_session_token(flipped, now=1_000_001) is None
    assert read_session_token("garbage") is None
    assert read_session_token("not-base64.abc") is None
    assert read_session_token(None) is None
    admin_payload = create_session_token("admin", now=1_000_000).split(".")[0]
    forged = admin_payload + "." + token.split(".")[1]
    assert read_session_token(forged, now=1_000_001) is None


def test_session_secret_from_env_changes_signatures(monkeypatch) -> None:
    token = create_session_token("user")
    monkeypatch.setenv("PM_SESSION_SECRET", "another-secret")
    assert read_session_token(token) is None


def test_credentials_can_be_overridden_by_env(anon_client, monkeypatch) -> None:
    monkeypatch.setenv("PM_LOGIN_USER", "alice")
    monkeypatch.setenv("PM_LOGIN_PASSWORD", "s3cret")
    old = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    assert old.status_code == 401
    new = anon_client.post("/api/login", json={"username": "alice", "password": "s3cret"})
    assert new.status_code == 200


def test_chat_rejects_oversized_input(client) -> None:
    too_long = "a" * (CHAT_MESSAGE_MAX_CHARS + 1)
    assert client.post("/api/chat", json={"message": too_long}).status_code == 422
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    history = [{"role": "user", "content": "hi"}] * (CHAT_HISTORY_MAX_ITEMS + 1)
    assert client.post("/api/chat", json={"message": "hi", "history": history}).status_code == 422
    huge_item = [{"role": "user", "content": "b" * (CHAT_MESSAGE_MAX_CHARS * 2 + 1)}]
    assert client.post("/api/chat", json={"message": "hi", "history": huge_item}).status_code == 422


class _Reply:
    status_code = 200

    def json(self) -> dict:
        return {"choices": [{"message": {"content": json.dumps({"reply": "ok", "actions": []})}}]}


def test_chat_is_rate_limited(client, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.httpx, "post", lambda *_a, **_k: _Reply())
    for _ in range(CHAT_RATE_LIMIT):
        assert client.post("/api/chat", json={"message": "hi"}).status_code == 200
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 429
    assert "Too many" in response.json()["detail"]
