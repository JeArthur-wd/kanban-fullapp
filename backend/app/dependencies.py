import sqlite3
from typing import Generator

from fastapi import HTTPException, Request

from app.auth import SESSION_COOKIE, read_session_token
from app.database import connect_db


def get_db() -> Generator[sqlite3.Connection, None, None]:
    conn = connect_db()
    try:
        yield conn
    finally:
        conn.close()


def get_username(request: Request) -> str:
    username = read_session_token(request.cookies.get(SESSION_COOKIE))
    if username is None:
        raise HTTPException(status_code=401, detail="Not signed in")
    return username
