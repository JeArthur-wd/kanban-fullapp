"""Signed session cookie. The cookie holds the username and an expiry, signed with HMAC."""

import base64
import hashlib
import hmac
import time

from app.config import SESSION_TTL_SECONDS, get_login_credentials, get_session_secret

SESSION_COOKIE = "pm_session"


def _sign(payload: str) -> str:
    return hmac.new(get_session_secret(), payload.encode(), hashlib.sha256).hexdigest()


def check_credentials(username: str, password: str) -> bool:
    expected_user, expected_password = get_login_credentials()
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    password_ok = hmac.compare_digest(password.encode(), expected_password.encode())
    return user_ok and password_ok


def create_session_token(username: str, now: float | None = None) -> str:
    expires = int((time.time() if now is None else now) + SESSION_TTL_SECONDS)
    payload = f"{username}|{expires}"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    return f"{encoded}.{_sign(payload)}"


def read_session_token(token: str | None, now: float | None = None) -> str | None:
    """Return the username for a valid, unexpired token, otherwise None."""
    if not token or "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    try:
        payload = base64.urlsafe_b64decode(encoded.encode()).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    username, _, expires = payload.rpartition("|")
    if not username or not expires.isdigit():
        return None
    if int(expires) < (time.time() if now is None else now):
        return None
    return username
