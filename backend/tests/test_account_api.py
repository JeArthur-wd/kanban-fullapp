from fastapi.testclient import TestClient

from app.auth import read_session_token
from app.database import connect_db
from app.main import app


def _register(client, username="newbie", password="long-enough", **extra):
    return client.post(
        "/api/register", json={"username": username, "password": password, **extra}
    )


def test_sign_up_signs_in_and_creates_a_sample_board(anon_client) -> None:
    response = _register(anon_client, "Newbie", display_name="  New Person ")
    assert response.status_code == 200
    assert response.json()["username"] == "newbie"
    assert response.json()["displayName"] == "New Person"

    session = anon_client.get("/api/session").json()
    assert (session["username"], session["displayName"]) == ("newbie", "New Person")
    boards = anon_client.get("/api/boards").json()
    assert len(boards) == 1 and boards[0]["cardCount"] > 0


def test_sign_up_then_sign_in_again(anon_client) -> None:
    _register(anon_client)
    anon_client.post("/api/logout")
    response = anon_client.post("/api/login", json={"username": "newbie", "password": "long-enough"})
    assert response.status_code == 200


def test_sign_up_rejects_taken_usernames_case_insensitively(anon_client) -> None:
    response = _register(anon_client, "USER")
    assert response.status_code == 409
    assert response.json()["detail"] == "That username is taken."


def test_sign_up_validates_username_and_password(anon_client) -> None:
    for bad in ["ab", "has space", "x" * 33, "-leading", "émile", ""]:
        assert _register(anon_client, bad).status_code == 422, bad
    assert _register(anon_client, "okname", "short").status_code == 422
    assert _register(anon_client, "okname", display_name="x" * 81).status_code == 422
    assert _register(anon_client, "ok.name-2_x").status_code == 200


def test_sign_up_can_be_turned_off(anon_client, monkeypatch) -> None:
    monkeypatch.setenv("PM_ALLOW_SIGNUP", "false")
    response = _register(anon_client)
    assert response.status_code == 403
    assert anon_client.get("/api/session").status_code == 401


def test_sign_up_is_rate_limited(anon_client) -> None:
    from app.config import LOGIN_RATE_LIMIT

    for index in range(LOGIN_RATE_LIMIT):
        _register(anon_client, f"user{index:03d}")
    assert _register(anon_client, "onemore").status_code == 429


def test_read_and_update_profile(client) -> None:
    me = client.get("/api/me").json()
    assert (me["username"], me["displayName"]) == ("user", "")

    updated = client.patch("/api/me", json={"display_name": "  Demo User "})
    assert updated.status_code == 200
    assert updated.json()["displayName"] == "Demo User"
    assert client.get("/api/session").json()["displayName"] == "Demo User"
    assert client.patch("/api/me", json={"display_name": "x" * 81}).status_code == 422


def test_change_password_keeps_this_session_and_ends_others(client, anon_client) -> None:
    other_device = TestClient(app)
    assert other_device.post(
        "/api/login", json={"username": "user", "password": "password"}
    ).status_code == 200

    response = client.post(
        "/api/me/password", json={"current_password": "password", "new_password": "better-pass"}
    )
    assert response.status_code == 200
    assert client.get("/api/boards").status_code == 200
    assert other_device.get("/api/boards").status_code == 401

    fresh = TestClient(app)
    assert fresh.post("/api/login", json={"username": "user", "password": "password"}).status_code == 401
    assert fresh.post(
        "/api/login", json={"username": "user", "password": "better-pass"}
    ).status_code == 200


def test_change_password_needs_the_current_password(client) -> None:
    response = client.post(
        "/api/me/password", json={"current_password": "nope", "new_password": "better-pass"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "That password is not correct."
    short = client.post("/api/me/password", json={"current_password": "password", "new_password": "x"})
    assert short.status_code == 422


def test_delete_account_removes_everything(make_user, db_path) -> None:
    other = make_user("leaving", "leaving-pass")
    other.post("/api/boards", json={"title": "Second", "template": "sample"})

    wrong = other.request("DELETE", "/api/me", json={"password": "nope"})
    assert wrong.status_code == 403
    response = other.request("DELETE", "/api/me", json={"password": "leaving-pass"})
    assert response.status_code == 200
    assert other.get("/api/session").status_code == 401

    conn = connect_db()
    counts = [
        conn.execute(
            "SELECT COUNT(*) FROM users WHERE username = 'leaving'"
        ).fetchone()[0],
        conn.execute(
            "SELECT COUNT(*) FROM boards WHERE user_id NOT IN (SELECT id FROM users)"
        ).fetchone()[0],
        conn.execute(
            "SELECT COUNT(*) FROM columns WHERE board_id NOT IN (SELECT id FROM boards)"
        ).fetchone()[0],
        conn.execute(
            "SELECT COUNT(*) FROM cards WHERE column_id NOT IN (SELECT id FROM columns)"
        ).fetchone()[0],
    ]
    conn.close()
    assert counts == [0, 0, 0, 0]


def test_a_deleted_accounts_cookie_does_not_come_back(make_user) -> None:
    other = make_user("ghost", "ghost-pass")
    cookie = other.cookies.get("pm_session").strip('"')
    other.request("DELETE", "/api/me", json={"password": "ghost-pass"})

    replay = TestClient(app)
    replay.cookies.set("pm_session", cookie)
    assert replay.get("/api/boards").status_code == 401

    # The newest id is not reused by the next account, so the old cookie stays dead.
    newcomer = TestClient(app)
    newcomer.post("/api/register", json={"username": "newcomer", "password": "newcomer-pass"})
    assert newcomer.get("/api/session").json()["id"] != str(read_session_token(cookie)[0])
    assert replay.get("/api/boards").status_code == 401
