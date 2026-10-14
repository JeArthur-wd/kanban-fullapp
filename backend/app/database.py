import sqlite3
from typing import Iterable, Literal

from app.config import DEFAULT_BOARD_TITLE, INITIAL_COLUMNS, get_db_path

VALID_TABLES = {"cards", "columns"}
BUSY_TIMEOUT_SECONDS = 10


def connect_db() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_SECONDS)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect_db()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'My Board',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (user_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS columns (
            id INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id) REFERENCES boards(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY,
            column_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (column_id) REFERENCES columns(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_boards_user_id ON boards(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_columns_board_id ON columns(board_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cards_column_id ON cards(column_id)")
    conn.commit()
    conn.close()


def get_or_create_user(conn: sqlite3.Connection, username: str) -> int:
    conn.execute("INSERT INTO users (username) VALUES (?) ON CONFLICT(username) DO NOTHING", (username,))
    conn.commit()
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    return int(row["id"])


def get_or_create_board(conn: sqlite3.Connection, user_id: int) -> int:
    """Return the user's board id. A new board is created together with its seed columns."""
    cursor = conn.execute(
        "INSERT INTO boards (user_id, title) VALUES (?, ?) ON CONFLICT(user_id) DO NOTHING",
        (user_id, DEFAULT_BOARD_TITLE),
    )
    created = cursor.rowcount == 1
    board_id = int(
        conn.execute("SELECT id FROM boards WHERE user_id = ?", (user_id,)).fetchone()["id"]
    )
    if created:
        _seed_board(conn, board_id)
    conn.commit()
    return board_id


def _seed_board(conn: sqlite3.Connection, board_id: int) -> None:
    for column_index, (column_title, cards) in enumerate(INITIAL_COLUMNS):
        column_cursor = conn.execute(
            "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
            (board_id, column_title, column_index),
        )
        column_id = int(column_cursor.lastrowid)
        for card_index, (title, details) in enumerate(cards):
            conn.execute(
                "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
                (column_id, title, details, card_index),
            )


def fetch_board(conn: sqlite3.Connection, user_id: int) -> dict:
    board_id = get_or_create_board(conn, user_id)
    board_row = conn.execute(
        "SELECT id, title FROM boards WHERE id = ?",
        (board_id,),
    ).fetchone()

    column_rows = conn.execute(
        "SELECT id, title, position FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    card_rows = conn.execute(
        """
        SELECT id, column_id, title, details, position
        FROM cards
        WHERE archived = 0 AND column_id IN (
            SELECT id FROM columns WHERE board_id = ?
        )
        ORDER BY column_id, position
        """,
        (board_id,),
    ).fetchall()

    cards_by_id = {
        str(row["id"]): {
            "id": str(row["id"]),
            "title": row["title"],
            "details": row["details"],
        }
        for row in card_rows
    }

    cards_by_column: dict[int, list[str]] = {int(row["id"]): [] for row in column_rows}
    for row in card_rows:
        cards_by_column[int(row["column_id"])].append(str(row["id"]))

    columns_payload = [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "position": row["position"],
            "cardIds": cards_by_column.get(int(row["id"]), []),
        }
        for row in column_rows
    ]

    return {
        "board": {"id": str(board_row["id"]), "title": board_row["title"]},
        "columns": columns_payload,
        "cards": cards_by_id,
    }


def ordered_ids(rows: Iterable[sqlite3.Row]) -> list[int]:
    return [int(row["id"]) for row in rows]


def resequence_positions(
    conn: sqlite3.Connection,
    table: Literal["cards", "columns"],
    ids: list[int],
    extra_where: str,
    extra_params: tuple,
) -> None:
    if table not in VALID_TABLES:
        raise ValueError(f"Invalid table: {table}")
    for index, item_id in enumerate(ids):
        conn.execute(
            f"UPDATE {table} SET position = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? {extra_where}",
            (index, item_id, *extra_params),
        )
