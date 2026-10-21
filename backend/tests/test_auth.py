import json

import app.ai.client as ai_module
from app.accounts import ensure_demo_account
from app.auth import create_session_token, hash_password, read_session_token, verify_password
from app.config import (
    CHAT_HISTORY_MAX_ITEMS,
    CHAT_MESSAGE_MAX_CHARS,
    CHAT_RATE_LIMIT,
    LOGIN_RATE_LIMIT,
)
from app.database import connect_db
from app.ratelimit import RateLimiter
from app.routes.auth import login_limiter


def test_api_requires_sign_in(anon_client) -> None:
    assert anon_client.get("/api/boards").status_code == 401
    assert anon_client.get("/api/boards/1").status_code == 401
    assert anon_client.get("/api/session").status_code == 401
    assert anon_client.get("/api/me").status_code == 401
    assert anon_client.post("/api/boards/1/chat", json={"message": "hi"}).status_code == 401
    assert anon_client.post("/api/cards", json={"column_id": 1, "title": "x"}).status_code == 401
    assert anon_client.delete("/api/cards/1").status_code == 401


def test_x_user_header_does_not_grant_access(anon_client) -> None:
    response = anon_client.get("/api/boards", headers={"X-User": "user"})
    assert response.status_code == 401


def test_login_sets_http_only_cookie(anon_client) -> None:
    response = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200
    assert response.json()["username"] == "user"
    cookie = response.headers["set-cookie"].lower()
    assert "pm_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    session = anon_client.get("/api/session").json()
    assert session["username"] == "user"
    assert set(session) == {"id", "username", "displayName", "createdAt"}


def test_login_ignores_username_case_and_spaces(anon_client) -> None:
    response = anon_client.post("/api/login", json={"username": " User ", "password": "password"})
    assert response.status_code == 200


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
        assert response.json()["detail"] == "Incorrect username or password."
        assert "pm_session" not in response.headers.get("set-cookie", "")
    assert anon_client.get("/api/boards").status_code == 401


def test_login_is_rate_limited(anon_client) -> None:
    for _ in range(LOGIN_RATE_LIMIT):
        bad = anon_client.post("/api/login", json={"username": "u", "password": "x"})
        assert bad.status_code == 401
    response = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 429


def test_successful_sign_ins_do_not_use_up_the_limit(anon_client) -> None:
    for _ in range(LOGIN_RATE_LIMIT + 5):
        response = anon_client.post("/api/login", json={"username": "user", "password": "password"})
        assert response.status_code == 200
    for _ in range(LOGIN_RATE_LIMIT):
        assert anon_client.post("/api/login", json={"username": "u", "password": "x"}).status_code == 401
    # Once failures use the budget up, even the right password waits.
    response = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 429


def test_rate_limiter_check_without_record_leaves_no_key_behind(monkeypatch) -> None:
    clock = [1000.0]
    monkeypatch.setattr("app.ratelimit.time.monotonic", lambda: clock[0])
    limiter = RateLimiter(limit=1, window_seconds=60)
    limiter.ensure_allowed("probe", "no")
    clock[0] += 61
    limiter.check("other", "no")
    assert len(limiter) == 1


def test_fly_client_ip_is_ignored_when_not_behind_fly(anon_client, monkeypatch) -> None:
    # Review M1: rotating the header used to give every attempt a fresh budget.
    monkeypatch.delenv("FLY_APP_NAME", raising=False)
    for attempt in range(LOGIN_RATE_LIMIT):
        anon_client.post(
            "/api/login",
            json={"username": "u", "password": "x"},
            headers={"Fly-Client-IP": f"10.0.0.{attempt}"},
        )
    response = anon_client.post(
        "/api/login",
        json={"username": "u", "password": "x"},
        headers={"Fly-Client-IP": "10.0.1.1"},
    )
    assert response.status_code == 429
    assert len(login_limiter) == 1


def test_fly_client_ip_is_the_key_behind_fly(anon_client, monkeypatch) -> None:
    monkeypatch.setenv("FLY_APP_NAME", "kanban-studio")
    for _ in range(LOGIN_RATE_LIMIT):
        anon_client.post(
            "/api/login", json={"username": "u", "password": "x"}, headers={"Fly-Client-IP": "1.1.1.1"}
        )
    blocked = anon_client.post(
        "/api/login", json={"username": "u", "password": "x"}, headers={"Fly-Client-IP": "1.1.1.1"}
    )
    other_client = anon_client.post(
        "/api/login", json={"username": "u", "password": "x"}, headers={"Fly-Client-IP": "2.2.2.2"}
    )
    assert blocked.status_code == 429
    assert other_client.status_code == 401


def test_rate_limiter_drops_idle_keys(monkeypatch) -> None:
    clock = [1000.0]
    monkeypatch.setattr("app.ratelimit.time.monotonic", lambda: clock[0])
    limiter = RateLimiter(limit=2, window_seconds=60)
    for key in ("a", "b", "c"):
        limiter.check(key, "no")
    assert len(limiter) == 3
    clock[0] += 61
    limiter.check("d", "no")
    assert len(limiter) == 1


def test_logout_clears_the_session(client) -> None:
    assert client.get("/api/boards").status_code == 200
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/boards").status_code == 401


def test_tampered_or_expired_tokens_are_rejected() -> None:
    token = create_session_token(1, 0, now=1_000_000)
    assert read_session_token(token, now=1_000_001) == (1, 0)
    assert read_session_token(token, now=1_000_000 + 10 * 24 * 3600) is None
    flipped = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert read_session_token(flipped, now=1_000_001) is None
    assert read_session_token("garbage") is None
    assert read_session_token("not-base64.abc") is None
    assert read_session_token(None) is None
    other_payload = create_session_token(2, 0, now=1_000_000).split(".")[0]
    forged = other_payload + "." + token.split(".")[1]
    assert read_session_token(forged, now=1_000_001) is None


def test_old_username_tokens_are_rejected() -> None:
    # Cookies from before accounts were stored held "username|expires".
    import base64
    import hashlib
    import hmac

    from app.config import get_session_secret

    payload = "user|9999999999"
    signature = hmac.new(get_session_secret(), payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(payload.encode()).decode() + "." + signature
    assert read_session_token(token) is None


def test_session_secret_from_env_changes_signatures(monkeypatch) -> None:
    token = create_session_token(1, 0)
    monkeypatch.setenv("PM_SESSION_SECRET", "another-secret")
    assert read_session_token(token) is None


def test_password_hashes_are_salted_and_verifiable() -> None:
    first, second = hash_password("correct horse"), hash_password("correct horse")
    assert first != second
    assert first.startswith("scrypt$")
    assert "correct horse" not in first
    assert verify_password("correct horse", first)
    assert not verify_password("wrong horse", first)
    assert not verify_password("x", None)
    assert not verify_password("x", "")
    assert not verify_password("x", "md5$abc")
    assert not verify_password("x", "scrypt$bad$data")


def test_demo_account_comes_from_env(db_path, anon_client, monkeypatch) -> None:
    monkeypatch.setenv("PM_LOGIN_USER", "Alice")
    monkeypatch.setenv("PM_LOGIN_PASSWORD", "s3cret-pass")
    conn = connect_db()
    ensure_demo_account(conn)
    conn.close()
    response = anon_client.post("/api/login", json={"username": "alice", "password": "s3cret-pass"})
    assert response.status_code == 200
    assert len(anon_client.get("/api/boards").json()) == 1


def test_demo_account_password_is_kept_once_set(db_path, anon_client, monkeypatch) -> None:
    monkeypatch.setenv("PM_LOGIN_PASSWORD", "a-new-password")
    conn = connect_db()
    ensure_demo_account(conn)
    conn.close()
    old = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    new = anon_client.post("/api/login", json={"username": "user", "password": "a-new-password"})
    assert (old.status_code, new.status_code) == (200, 401)


def test_demo_account_without_a_password_gets_one(db_path, anon_client) -> None:
    # Accounts from before passwords were stored have password_hash NULL.
    conn = connect_db()
    conn.execute("UPDATE users SET password_hash = NULL WHERE username = 'user'")
    conn.commit()
    ensure_demo_account(conn)
    conn.close()
    response = anon_client.post("/api/login", json={"username": "user", "password": "password"})
    assert response.status_code == 200


def test_chat_rejects_oversized_input(client, board_url) -> None:
    url = f"{board_url}/chat"
    too_long = "a" * (CHAT_MESSAGE_MAX_CHARS + 1)
    assert client.post(url, json={"message": too_long}).status_code == 422
    assert client.post(url, json={"message": ""}).status_code == 422
    history = [{"role": "user", "content": "hi"}] * (CHAT_HISTORY_MAX_ITEMS + 1)
    assert client.post(url, json={"message": "hi", "history": history}).status_code == 422
    huge_item = [{"role": "user", "content": "b" * (CHAT_MESSAGE_MAX_CHARS * 2 + 1)}]
    assert client.post(url, json={"message": "hi", "history": huge_item}).status_code == 422


class _Reply:
    status_code = 200

    def json(self) -> dict:
        return {"choices": [{"message": {"content": json.dumps({"reply": "ok", "actions": []})}}]}


def test_chat_is_rate_limited(client, board_url, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.httpx, "post", lambda *_a, **_k: _Reply())
    for _ in range(CHAT_RATE_LIMIT):
        assert client.post(f"{board_url}/chat", json={"message": "hi"}).status_code == 200
    response = client.post(f"{board_url}/chat", json={"message": "hi"})
    assert response.status_code == 429
    assert "Too many" in response.json()["detail"]
