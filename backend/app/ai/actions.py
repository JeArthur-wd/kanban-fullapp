"""Apply the model's actions to the board through board_ops, skipping what cannot be applied."""

import sqlite3

from pydantic import ValidationError

from app import board_ops
from app.board_ops import NotFoundError
from app.models import (
    CardCreate,
    CardUpdate,
    ChatAction,
    CreateCardAction,
    DeleteCardAction,
    MoveCardAction,
    SkippedAction,
    UpdateCardAction,
)


def _to_int(value: str, label: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise NotFoundError(f"{label} id {value!r} is not valid") from exc


def _apply_one(conn: sqlite3.Connection, board_id: int, action: ChatAction) -> None:
    """Apply one action. Raises NotFoundError or ValidationError when it cannot run."""
    if isinstance(action, CreateCardAction):
        column_id = _to_int(action.columnId, "Column")
        card = CardCreate(
            column_id=column_id,
            title=action.title,
            details=action.details,
            position=action.position,
        )
        board_ops.create_card(
            conn, board_id, card.column_id, card.title, card.details, card.position
        )
    elif isinstance(action, UpdateCardAction):
        card_id = _to_int(action.cardId, "Card")
        fields = CardUpdate(title=action.title, details=action.details)
        board_ops.update_card_fields(conn, board_id, card_id, fields.field_changes())
    elif isinstance(action, MoveCardAction):
        card_id = _to_int(action.cardId, "Card")
        column_id = _to_int(action.columnId, "Column")
        board_ops.move_card(conn, board_id, card_id, column_id, action.position)
    elif isinstance(action, DeleteCardAction):
        board_ops.delete_card(conn, board_id, _to_int(action.cardId, "Card"))


def apply_actions(
    conn: sqlite3.Connection, board_id: int, actions: list[ChatAction]
) -> tuple[list[ChatAction], list[SkippedAction]]:
    """Apply what can be applied. Returns (applied, skipped) so the reply can say which."""
    applied: list[ChatAction] = []
    skipped: list[SkippedAction] = []

    for action in actions:
        try:
            _apply_one(conn, board_id, action)
        except NotFoundError as exc:
            skipped.append(SkippedAction(type=action.type, reason=str(exc)))
        except ValidationError:
            skipped.append(SkippedAction(type=action.type, reason="Invalid title or details"))
        else:
            applied.append(action)

    conn.commit()
    return applied, skipped
