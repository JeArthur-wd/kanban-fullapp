"""Board, column and card operations shared by the REST routes and the AI actions.

Board-level functions take the user id and check the user may use the board; the
`board_for_*` helpers resolve a column or card to a board the user may use. Column and card
functions take that board id and check the column or card belongs to it.
None of them commit; the caller does.
"""

import sqlite3

from app.config import BASIC_COLUMNS, INITIAL_COLUMNS
from app.database import ordered_ids, resequence_positions

CARD_FIELDS = ("title", "details", "priority", "due_date")


class NotFoundError(Exception):
    """The board, column or card does not exist, or the user may not use it."""


def require_board(conn: sqlite3.Connection, user_id: int, board_id: int) -> None:
    row = conn.execute(
        "SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id)
    ).fetchone()
    if row is None:
        raise NotFoundError("Board not found")


def board_for_column(conn: sqlite3.Connection, user_id: int, column_id: int) -> int:
    row = conn.execute(
        """
        SELECT boards.id FROM columns JOIN boards ON columns.board_id = boards.id
        WHERE columns.id = ? AND boards.user_id = ?
        """,
        (column_id, user_id),
    ).fetchone()
    if row is None:
        raise NotFoundError("Column not found")
    return int(row["id"])


def board_for_card(conn: sqlite3.Connection, user_id: int, card_id: int) -> int:
    row = conn.execute(
        """
        SELECT boards.id FROM cards
        JOIN columns ON cards.column_id = columns.id
        JOIN boards ON columns.board_id = boards.id
        WHERE cards.id = ? AND boards.user_id = ?
        """,
        (card_id, user_id),
    ).fetchone()
    if row is None:
        raise NotFoundError("Card not found")
    return int(row["id"])


def list_boards(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT boards.id, boards.title, boards.description, boards.created_at,
            (SELECT COUNT(*) FROM columns WHERE columns.board_id = boards.id) AS column_count,
            (SELECT COUNT(*) FROM cards JOIN columns ON cards.column_id = columns.id
             WHERE columns.board_id = boards.id AND cards.archived = 0) AS card_count
        FROM boards WHERE boards.user_id = ? ORDER BY boards.id
        """,
        (user_id,),
    ).fetchall()
    return [
        {
            "id": str(row["id"]),
            "title": row["title"],
            "description": row["description"],
            "createdAt": row["created_at"],
            "columnCount": row["column_count"],
            "cardCount": row["card_count"],
        }
        for row in rows
    ]


def create_board(
    conn: sqlite3.Connection, user_id: int, title: str, description: str, template: str
) -> int:
    """Create a board. `template` is "sample" (demo columns and cards) or "basic"."""
    cursor = conn.execute(
        "INSERT INTO boards (user_id, title, description) VALUES (?, ?, ?)",
        (user_id, title, description),
    )
    board_id = int(cursor.lastrowid)
    columns = INITIAL_COLUMNS if template == "sample" else [(name, []) for name in BASIC_COLUMNS]
    for column_index, (column_title, cards) in enumerate(columns):
        column_cursor = conn.execute(
            "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
            (board_id, column_title, column_index),
        )
        for card_index, (card_title, details) in enumerate(cards):
            conn.execute(
                "INSERT INTO cards (column_id, title, details, position) VALUES (?, ?, ?, ?)",
                (column_cursor.lastrowid, card_title, details, card_index),
            )
    return board_id


def update_board(
    conn: sqlite3.Connection,
    user_id: int,
    board_id: int,
    title: str | None,
    description: str | None,
) -> None:
    require_board(conn, user_id, board_id)
    for column, value in (("title", title), ("description", description)):
        if value is not None:
            conn.execute(
                f"UPDATE boards SET {column} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (value, board_id),
            )


def delete_board(conn: sqlite3.Connection, user_id: int, board_id: int) -> None:
    require_board(conn, user_id, board_id)
    conn.execute("DELETE FROM boards WHERE id = ?", (board_id,))


def _clamp(position: int | None, length: int) -> int:
    if position is None or position > length:
        return length
    return max(position, 0)


def _column_exists(conn: sqlite3.Connection, board_id: int, column_id: int) -> bool:
    row = conn.execute(
        "SELECT id FROM columns WHERE id = ? AND board_id = ?", (column_id, board_id)
    ).fetchone()
    return row is not None


def _require_column(conn: sqlite3.Connection, board_id: int, column_id: int) -> None:
    if not _column_exists(conn, board_id, column_id):
        raise NotFoundError("Column not found")


def _require_card(conn: sqlite3.Connection, board_id: int, card_id: int) -> sqlite3.Row:
    card = conn.execute(
        """
        SELECT cards.id, cards.column_id
        FROM cards
        JOIN columns ON cards.column_id = columns.id
        WHERE cards.id = ? AND columns.board_id = ?
        """,
        (card_id, board_id),
    ).fetchone()
    if card is None:
        raise NotFoundError("Card not found")
    return card


def _column_ids(conn: sqlite3.Connection, board_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM columns WHERE board_id = ? ORDER BY position", (board_id,)
    ).fetchall()
    return ordered_ids(rows)


def _card_ids(conn: sqlite3.Connection, column_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM cards WHERE column_id = ? AND archived = 0 ORDER BY position",
        (column_id,),
    ).fetchall()
    return ordered_ids(rows)


def _resequence_columns(conn: sqlite3.Connection, board_id: int, ids: list[int]) -> None:
    resequence_positions(conn, "columns", ids, "AND board_id = ?", (board_id,))


def _resequence_cards(conn: sqlite3.Connection, column_id: int, ids: list[int]) -> None:
    resequence_positions(conn, "cards", ids, "AND column_id = ?", (column_id,))


def create_column(
    conn: sqlite3.Connection, board_id: int, title: str, position: int | None
) -> int:
    ids = _column_ids(conn, board_id)
    insert_at = _clamp(position, len(ids))
    cursor = conn.execute(
        "INSERT INTO columns (board_id, title, position) VALUES (?, ?, ?)",
        (board_id, title, insert_at),
    )
    column_id = int(cursor.lastrowid)
    ids.insert(insert_at, column_id)
    _resequence_columns(conn, board_id, ids)
    return column_id


def update_column(
    conn: sqlite3.Connection,
    board_id: int,
    column_id: int,
    title: str | None,
    position: int | None,
) -> None:
    _require_column(conn, board_id, column_id)
    if title is not None:
        conn.execute(
            "UPDATE columns SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (title, column_id),
        )
    if position is not None:
        ids = [item for item in _column_ids(conn, board_id) if item != column_id]
        ids.insert(_clamp(position, len(ids)), column_id)
        _resequence_columns(conn, board_id, ids)


def delete_column(conn: sqlite3.Connection, board_id: int, column_id: int) -> None:
    _require_column(conn, board_id, column_id)
    conn.execute("DELETE FROM cards WHERE column_id = ?", (column_id,))
    conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))
    _resequence_columns(conn, board_id, _column_ids(conn, board_id))


def create_card(
    conn: sqlite3.Connection,
    board_id: int,
    column_id: int,
    title: str,
    details: str,
    position: int | None,
    priority: str = "none",
    due_date: str | None = None,
) -> int:
    _require_column(conn, board_id, column_id)
    ids = _card_ids(conn, column_id)
    insert_at = _clamp(position, len(ids))
    cursor = conn.execute(
        """
        INSERT INTO cards (column_id, title, details, priority, due_date, position)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (column_id, title, details, priority, due_date, insert_at),
    )
    card_id = int(cursor.lastrowid)
    ids.insert(insert_at, card_id)
    _resequence_cards(conn, column_id, ids)
    return card_id


def update_card_fields(
    conn: sqlite3.Connection, board_id: int, card_id: int, fields: dict[str, object]
) -> None:
    """Set the given card fields (keys from CARD_FIELDS). A None due_date clears it."""
    _require_card(conn, board_id, card_id)
    unknown = set(fields) - set(CARD_FIELDS)
    if unknown:
        raise ValueError(f"Unknown card fields: {sorted(unknown)}")
    if not fields:
        return
    assignments = ", ".join(f"{name} = ?" for name in fields)
    conn.execute(
        f"UPDATE cards SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (*fields.values(), card_id),
    )


def move_card(
    conn: sqlite3.Connection,
    board_id: int,
    card_id: int,
    column_id: int | None,
    position: int | None,
) -> None:
    """Move a card. `position` is the index the card ends up at in the target column.

    `column_id=None` keeps the card in its current column. `position=None` appends to the
    target column, or does nothing when the card is already in it.
    """
    card = _require_card(conn, board_id, card_id)
    source_id = int(card["column_id"])
    target_id = source_id if column_id is None else column_id
    if target_id == source_id and position is None:
        return
    if target_id != source_id:
        _require_column(conn, board_id, target_id)

    # Take the card out of its column first, then insert it into the target. For a
    # move inside one column the target list is the source list without the card.
    source_ids = [item for item in _card_ids(conn, source_id) if item != card_id]
    if target_id == source_id:
        target_ids = source_ids
    else:
        target_ids = _card_ids(conn, target_id)
    target_ids.insert(_clamp(position, len(target_ids)), card_id)

    conn.execute(
        "UPDATE cards SET column_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (target_id, card_id),
    )
    if target_id != source_id:
        _resequence_cards(conn, source_id, source_ids)
    _resequence_cards(conn, target_id, target_ids)


def delete_card(conn: sqlite3.Connection, board_id: int, card_id: int) -> None:
    card = _require_card(conn, board_id, card_id)
    column_id = int(card["column_id"])
    conn.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    _resequence_cards(conn, column_id, _card_ids(conn, column_id))
