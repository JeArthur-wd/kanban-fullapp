import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import board_ops
from app.board_ops import NotFoundError
from app.database import fetch_board
from app.dependencies import get_db, get_user_id
from app.models import (
    BoardCreate,
    BoardUpdate,
    CardCreate,
    CardUpdate,
    ColumnCreate,
    ColumnUpdate,
)

router = APIRouter()


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/api/boards")
def list_boards(
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return board_ops.list_boards(conn, user_id)


@router.post("/api/boards")
def create_board(
    payload: BoardCreate,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    board_id = board_ops.create_board(
        conn, user_id, payload.title.strip(), payload.description.strip(), payload.template
    )
    conn.commit()
    return {"id": str(board_id)}


@router.get("/api/boards/{board_id}")
def get_board(
    board_id: int,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_ops.require_board(conn, user_id, board_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    return fetch_board(conn, board_id)


@router.patch("/api/boards/{board_id}")
def update_board(
    board_id: int,
    payload: BoardUpdate,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    title = payload.title.strip() if payload.title is not None else None
    description = payload.description.strip() if payload.description is not None else None
    if title == "":
        raise HTTPException(status_code=422, detail="A board needs a title.")
    try:
        board_ops.update_board(conn, user_id, board_id, title, description)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.delete("/api/boards/{board_id}")
def delete_board(
    board_id: int,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_ops.delete_board(conn, user_id, board_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.post("/api/boards/{board_id}/columns")
def create_column(
    board_id: int,
    payload: ColumnCreate,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_ops.require_board(conn, user_id, board_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    column_id = board_ops.create_column(conn, board_id, payload.title, payload.position)
    conn.commit()
    return {"id": str(column_id)}


@router.patch("/api/columns/{column_id}")
def update_column(
    column_id: int,
    payload: ColumnUpdate,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_id = board_ops.board_for_column(conn, user_id, column_id)
        board_ops.update_column(conn, board_id, column_id, payload.title, payload.position)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.delete("/api/columns/{column_id}")
def delete_column(
    column_id: int,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_id = board_ops.board_for_column(conn, user_id, column_id)
        board_ops.delete_column(conn, board_id, column_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.post("/api/cards")
def create_card(
    payload: CardCreate,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_id = board_ops.board_for_column(conn, user_id, payload.column_id)
        card_id = board_ops.create_card(
            conn,
            board_id,
            payload.column_id,
            payload.title,
            payload.details,
            payload.position,
            payload.priority,
            payload.due_date.isoformat() if payload.due_date else None,
        )
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"id": str(card_id)}


@router.patch("/api/cards/{card_id}")
def update_card(
    card_id: int,
    payload: CardUpdate,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_id = board_ops.board_for_card(conn, user_id, card_id)
        board_ops.update_card_fields(conn, board_id, card_id, payload.field_changes())
        if payload.column_id is not None or payload.position is not None:
            board_ops.move_card(conn, board_id, card_id, payload.column_id, payload.position)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.delete("/api/cards/{card_id}")
def delete_card(
    card_id: int,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_id = board_ops.board_for_card(conn, user_id, card_id)
        board_ops.delete_card(conn, board_id, card_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}
