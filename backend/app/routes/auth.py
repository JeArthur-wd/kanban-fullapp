import re
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.accounts import UsernameTakenError, create_user, get_user, normalize_username
from app.auth import SESSION_COOKIE, authenticate, create_session_token
from app.config import (
    SESSION_TTL_SECONDS,
    USERNAME_PATTERN,
    behind_fly_proxy,
    get_login_rate_limit,
    signup_enabled,
)
from app.dependencies import get_current_user, get_db
from app.models import LoginRequest, RegisterRequest
from app.ratelimit import RateLimiter

router = APIRouter()

# Sign-in counts failed attempts only, so signing in often is never blocked. Sign-up counts
# every attempt, since each success creates an account.
login_limiter = RateLimiter(get_login_rate_limit())
signup_limiter = RateLimiter(get_login_rate_limit())

TOO_MANY_ATTEMPTS = "Too many sign-in attempts. Try again in a minute."
TOO_MANY_SIGNUPS = "Too many sign-up attempts. Try again in a minute."


def _client_key(request: Request) -> str:
    # Behind Fly the proxy sets Fly-Client-IP and the socket peer is the proxy. Anywhere else
    # the header comes from the client, so it is ignored.
    if behind_fly_proxy():
        forwarded = request.headers.get("fly-client-ip")
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def set_session_cookie(request: Request, response: Response, user_id: int, epoch: int) -> None:
    secure = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
    )
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id, epoch),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
    )


def session_payload(user: sqlite3.Row) -> dict:
    return {
        "id": str(user["id"]),
        "username": user["username"],
        "displayName": user["display_name"],
        "createdAt": user["created_at"],
    }


@router.post("/api/login")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    client = _client_key(request)
    login_limiter.ensure_allowed(client, TOO_MANY_ATTEMPTS)
    user = authenticate(conn, normalize_username(payload.username), payload.password)
    if user is None:
        login_limiter.record(client)
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    set_session_cookie(request, response, int(user["id"]), int(user["session_epoch"]))
    return session_payload(get_user(conn, int(user["id"])))


@router.post("/api/register")
def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    if not signup_enabled():
        raise HTTPException(status_code=403, detail="Sign-up is turned off on this server.")
    signup_limiter.check(_client_key(request), TOO_MANY_SIGNUPS)
    username = normalize_username(payload.username)
    if not re.fullmatch(USERNAME_PATTERN, username):
        raise HTTPException(
            status_code=422,
            detail="Usernames are 3 to 32 characters: letters, numbers, dots, dashes, underscores.",
        )
    try:
        user_id = create_user(conn, username, payload.password, payload.display_name.strip())
    except UsernameTakenError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    conn.commit()
    set_session_cookie(request, response, user_id, 0)
    return session_payload(get_user(conn, user_id))


@router.post("/api/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/api/session")
def session(user: sqlite3.Row = Depends(get_current_user)) -> dict:
    return session_payload(user)
