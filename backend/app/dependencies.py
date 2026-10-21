import sqlite3
from typing import Generator

from fastapi import Depends, HTTPException, Request

from app.accounts import get_user
from app.auth import SESSION_COOKIE, read_session_token
from app.database import connect_db


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect_db()
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(
    request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> sqlite3.Row:
    """The signed-in user. 401 when the cookie is missing, invalid, or no longer current."""
    session = read_session_token(request.cookies.get(SESSION_COOKIE))
    user = get_user(conn, session[0]) if session else None
    if user is None or int(user["session_epoch"]) != session[1]:
        raise HTTPException(status_code=401, detail="Not signed in")
    return user


def get_user_id(user: sqlite3.Row = Depends(get_current_user)) -> int:
    return int(user["id"])
