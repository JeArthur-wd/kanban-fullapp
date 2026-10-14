import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import board_ops
from app.board_ops import NotFoundError
from app.database import fetch_board, get_or_create_board, get_or_create_user
from app.dependencies import get_db, get_username
from app.models import CardCreate, CardUpdate, ColumnCreate, ColumnUpdate

router = APIRouter()


def get_board_id(
    username: str = Depends(get_username),
    conn: sqlite3.Connection = Depends(get_db),
) -> int:
    return get_or_create_board(conn, get_or_create_user(conn, username))


def _not_found(exc: NotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/api/board")
def get_board(
    username: str = Depends(get_username),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return fetch_board(conn, get_or_create_user(conn, username))


@router.post("/api/columns")
def create_column(
    payload: ColumnCreate,
    board_id: int = Depends(get_board_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    column_id = board_ops.create_column(conn, board_id, payload.title, payload.position)
    conn.commit()
    return {"id": str(column_id)}


@router.patch("/api/columns/{column_id}")
def update_column(
    column_id: int,
    payload: ColumnUpdate,
    board_id: int = Depends(get_board_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_ops.update_column(conn, board_id, column_id, payload.title, payload.position)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.delete("/api/columns/{column_id}")
def delete_column(
    column_id: int,
    board_id: int = Depends(get_board_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_ops.delete_column(conn, board_id, column_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.post("/api/cards")
def create_card(
    payload: CardCreate,
    board_id: int = Depends(get_board_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        card_id = board_ops.create_card(
            conn, board_id, payload.column_id, payload.title, payload.details, payload.position
        )
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"id": str(card_id)}


@router.patch("/api/cards/{card_id}")
def update_card(
    card_id: int,
    payload: CardUpdate,
    board_id: int = Depends(get_board_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_ops.update_card_fields(conn, board_id, card_id, payload.title, payload.details)
        if payload.column_id is not None or payload.position is not None:
            board_ops.move_card(conn, board_id, card_id, payload.column_id, payload.position)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}


@router.delete("/api/cards/{card_id}")
def delete_card(
    card_id: int,
    board_id: int = Depends(get_board_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        board_ops.delete_card(conn, board_id, card_id)
    except NotFoundError as exc:
        raise _not_found(exc) from exc
    conn.commit()
    return {"status": "ok"}
