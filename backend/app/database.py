import sqlite3
from typing import Callable, Iterable, Literal

from app.config import get_db_path

VALID_TABLES = {"cards", "columns"}
BUSY_TIMEOUT_SECONDS = 10


def connect_db() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # FastAPI may open, use and close a request's connection on different threadpool threads.
    # Each connection still belongs to one request and is used by one thread at a time.
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_SECONDS, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migration_1_initial(conn: sqlite3.Connection) -> None:
    """The MVP schema: one board per user. Existing databases already have it."""
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


def _migration_2_accounts_and_boards(conn: sqlite3.Connection) -> None:
    """Many boards per user, account fields, card priority and due date.

    SQLite cannot drop a constraint or add AUTOINCREMENT, so all four tables are rebuilt (the
    documented create-copy-drop-rename procedure). Rows whose parent is missing are not copied.
    """
    # AUTOINCREMENT: a deleted user's id is never given to a new account, so an old session
    # cookie (which names the id) cannot sign in as someone else.
    conn.execute(
        """
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL DEFAULT '',
            password_hash TEXT,
            session_epoch INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO users_new (id, username, password_hash, created_at, updated_at)
        SELECT id, username, password_hash, created_at, updated_at FROM users
        """
    )
    conn.execute(
        """
        CREATE TABLE boards_new (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO boards_new (id, user_id, title, created_at, updated_at)
        SELECT id, user_id, title, created_at, updated_at FROM boards
        WHERE user_id IN (SELECT id FROM users_new)
        """
    )
    conn.execute(
        """
        CREATE TABLE columns_new (
            id INTEGER PRIMARY KEY,
            board_id INTEGER NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            position INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO columns_new (id, board_id, title, position, created_at, updated_at)
        SELECT id, board_id, title, position, created_at, updated_at FROM columns
        WHERE board_id IN (SELECT id FROM boards_new)
        """
    )
    conn.execute(
        """
        CREATE TABLE cards_new (
            id INTEGER PRIMARY KEY,
            column_id INTEGER NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            priority TEXT NOT NULL DEFAULT 'none'
                CHECK (priority IN ('none', 'low', 'medium', 'high')),
            due_date TEXT,
            position INTEGER NOT NULL,
            archived INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO cards_new
            (id, column_id, title, details, position, archived, created_at, updated_at)
        SELECT id, column_id, title, details, position, archived, created_at, updated_at
        FROM cards WHERE column_id IN (SELECT id FROM columns_new)
        """
    )
    for table in ("cards", "columns", "boards", "users"):
        conn.execute(f"DROP TABLE {table}")
    for table in ("users", "boards", "columns", "cards"):
        conn.execute(f"ALTER TABLE {table}_new RENAME TO {table}")

    conn.execute("CREATE INDEX idx_boards_user_id ON boards(user_id)")
    conn.execute("CREATE INDEX idx_columns_board_id ON columns(board_id)")
    conn.execute("CREATE INDEX idx_cards_column_id ON cards(column_id)")


MIGRATIONS: list[Callable[[sqlite3.Connection], None]] = [
    _migration_1_initial,
    _migration_2_accounts_and_boards,
]


def schema_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _broken_references(conn: sqlite3.Connection) -> set[tuple]:
    return {tuple(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()}


def migrate(conn: sqlite3.Connection) -> None:
    """Run each migration newer than the database's `user_version`, one transaction each."""
    for number in range(schema_version(conn) + 1, len(MIGRATIONS) + 1):
        # Rebuilding a table drops it, which would cascade with foreign keys on. The pragma
        # cannot change inside a transaction, so it is switched off around each migration.
        conn.execute("PRAGMA foreign_keys = OFF")
        try:
            conn.execute("BEGIN")
            # Databases from before foreign keys were on may already hold orphans; a migration
            # only fails if it adds new ones.
            before = _broken_references(conn)
            MIGRATIONS[number - 1](conn)
            added = _broken_references(conn) - before
            if added:
                raise RuntimeError(f"Migration {number} left broken references: {sorted(added)}")
            conn.execute(f"PRAGMA user_version = {number}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.execute("PRAGMA foreign_keys = ON")


def init_db() -> None:
    conn = connect_db()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        migrate(conn)
    finally:
        conn.close()


def fetch_board(conn: sqlite3.Connection, board_id: int) -> dict:
    """The board payload sent to the frontend and to the model."""
    board_row = conn.execute(
        "SELECT id, title, description FROM boards WHERE id = ?",
        (board_id,),
    ).fetchone()

    column_rows = conn.execute(
        "SELECT id, title, position FROM columns WHERE board_id = ? ORDER BY position",
        (board_id,),
    ).fetchall()

    card_rows = conn.execute(
        """
        SELECT id, column_id, title, details, priority, due_date, position
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
            "priority": row["priority"],
            "dueDate": row["due_date"],
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
        "board": {
            "id": str(board_row["id"]),
            "title": board_row["title"],
            "description": board_row["description"],
        },
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
