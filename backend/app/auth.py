"""Passwords and the signed session cookie.

Passwords are stored as scrypt hashes. The cookie holds the user id, the user's session epoch
and an expiry, signed with HMAC. Bumping a user's epoch (password change) ends every other
session; deleting the user ends all of them.
"""

import base64
import hashlib
import hmac
import secrets
import sqlite3
import time

from app.config import SESSION_TTL_SECONDS, get_session_secret

SESSION_COOKIE = "pm_session"

_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    try:
        scheme, n, r, p, salt, digest = (stored or "").split("$")
        if scheme != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p)
        )
    except ValueError:
        return False
    return hmac.compare_digest(candidate.hex(), digest)


# Checked when the username does not exist, so a miss takes as long as a wrong password.
_DUMMY_HASH = hash_password(secrets.token_hex(8))


def authenticate(conn: sqlite3.Connection, username: str, password: str) -> sqlite3.Row | None:
    user = conn.execute(
        "SELECT id, password_hash, session_epoch FROM users WHERE username = ?", (username,)
    ).fetchone()
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return user if verify_password(password, user["password_hash"]) else None


def _sign(payload: str) -> str:
    return hmac.new(get_session_secret(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token(user_id: int, epoch: int, now: float | None = None) -> str:
    expires = int((time.time() if now is None else now) + SESSION_TTL_SECONDS)
    payload = f"{user_id}|{epoch}|{expires}"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    return f"{encoded}.{_sign(payload)}"


def read_session_token(token: str | None, now: float | None = None) -> tuple[int, int] | None:
    """Return (user id, epoch) for a valid, unexpired token, otherwise None."""
    if not token or "." not in token:
        return None
    encoded, signature = token.rsplit(".", 1)
    try:
        payload = base64.urlsafe_b64decode(encoded.encode()).decode()
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    parts = payload.split("|")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return None
    user_id, epoch, expires = (int(part) for part in parts)
    if expires < (time.time() if now is None else now):
        return None
    return user_id, epoch
