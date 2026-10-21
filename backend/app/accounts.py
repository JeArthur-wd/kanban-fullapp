"""User accounts: create, profile, password, delete. None of these commit; the caller does."""

import sqlite3

from app import board_ops
from app.auth import hash_password
from app.config import DEFAULT_BOARD_TITLE, get_login_credentials


class UsernameTakenError(Exception):
    """Another account already uses this username."""


def normalize_username(username: str) -> str:
    return username.strip().lower()


def create_user(
    conn: sqlite3.Connection, username: str, password: str, display_name: str = ""
) -> int:
    """Create an account and its first board, which holds the sample content."""
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, display_name, password_hash) VALUES (?, ?, ?)",
            (username, display_name, hash_password(password)),
        )
    except sqlite3.IntegrityError as exc:
        raise UsernameTakenError("That username is taken.") from exc
    user_id = int(cursor.lastrowid)
    board_ops.create_board(conn, user_id, DEFAULT_BOARD_TITLE, "", "sample")
    return user_id


def ensure_demo_account(conn: sqlite3.Connection) -> None:
    """Create the configured demo account, or give it a password if it has none yet.

    Accounts from before passwords were stored have no hash. An existing password is left
    alone, so a password changed in the app survives a restart.
    """
    username, password = get_login_credentials()
    username = normalize_username(username)
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        create_user(conn, username, password)
    elif not row["password_hash"]:
        conn.execute(
            "UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (hash_password(password), row["id"]),
        )
    conn.commit()


def get_user(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT id, username, display_name, password_hash, session_epoch, created_at
        FROM users WHERE id = ?
        """,
        (user_id,),
    ).fetchone()


def update_profile(conn: sqlite3.Connection, user_id: int, display_name: str) -> None:
    conn.execute(
        "UPDATE users SET display_name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (display_name, user_id),
    )


def change_password(conn: sqlite3.Connection, user_id: int, new_password: str) -> int:
    """Store the new password and bump the session epoch. Returns the new epoch."""
    conn.execute(
        """
        UPDATE users SET password_hash = ?, session_epoch = session_epoch + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (hash_password(new_password), user_id),
    )
    return int(get_user(conn, user_id)["session_epoch"])


def delete_user(conn: sqlite3.Connection, user_id: int) -> None:
    """Delete the account; its boards, columns and cards go with it (foreign key cascade)."""
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
