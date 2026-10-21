import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app import accounts
from app.auth import SESSION_COOKIE, verify_password
from app.dependencies import get_current_user, get_db
from app.models import AccountDelete, PasswordChange, ProfileUpdate
from app.routes.auth import session_payload, set_session_cookie

router = APIRouter()


def _check_password(user: sqlite3.Row, password: str) -> None:
    if not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=403, detail="That password is not correct.")


@router.get("/api/me")
def read_account(user: sqlite3.Row = Depends(get_current_user)) -> dict:
    return session_payload(user)


@router.patch("/api/me")
def update_account(
    payload: ProfileUpdate,
    user: sqlite3.Row = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    accounts.update_profile(conn, int(user["id"]), payload.display_name.strip())
    conn.commit()
    return session_payload(accounts.get_user(conn, int(user["id"])))


@router.post("/api/me/password")
def change_password(
    payload: PasswordChange,
    request: Request,
    response: Response,
    user: sqlite3.Row = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    """Other sessions end; this one gets a fresh cookie and stays signed in."""
    _check_password(user, payload.current_password)
    epoch = accounts.change_password(conn, int(user["id"]), payload.new_password)
    conn.commit()
    set_session_cookie(request, response, int(user["id"]), epoch)
    return {"status": "ok"}


@router.delete("/api/me")
def delete_account(
    payload: AccountDelete,
    response: Response,
    user: sqlite3.Row = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    _check_password(user, payload.password)
    accounts.delete_user(conn, int(user["id"]))
    conn.commit()
    response.delete_cookie(SESSION_COOKIE)
    return {"status": "ok"}
