from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth import SESSION_COOKIE, check_credentials, create_session_token
from app.config import LOGIN_RATE_LIMIT, SESSION_TTL_SECONDS
from app.dependencies import get_username
from app.ratelimit import RateLimiter

router = APIRouter()

login_limiter = RateLimiter(LOGIN_RATE_LIMIT)


class LoginRequest(BaseModel):
    username: str = Field(..., max_length=200)
    password: str = Field(..., max_length=200)


def _client_key(request: Request) -> str:
    # Fly's proxy sets Fly-Client-IP; otherwise the socket peer is the client.
    forwarded = request.headers.get("fly-client-ip")
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


@router.post("/api/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    login_limiter.check(_client_key(request), "Too many sign-in attempts. Try again in a minute.")
    username = payload.username.strip()
    if not check_credentials(username, payload.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    secure = (
        request.url.scheme == "https"
        or request.headers.get("x-forwarded-proto") == "https"
    )
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(username),
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=secure,
    )
    return {"username": username}


@router.post("/api/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}


@router.get("/api/session")
def session(username: str = Depends(get_username)) -> dict:
    return {"username": username}
