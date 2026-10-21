import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from app import board_ops
from app.ai import apply_actions, build_structured_messages, call_openrouter, parse_structured_output
from app.board_ops import NotFoundError
from app.config import CHAT_RATE_LIMIT
from app.database import fetch_board
from app.dependencies import get_db, get_user_id
from app.models import ChatRequest, ChatResponse
from app.ratelimit import RateLimiter

router = APIRouter()

chat_limiter = RateLimiter(CHAT_RATE_LIMIT)


@router.post("/api/boards/{board_id}/chat", response_model=ChatResponse)
def chat(
    board_id: int,
    payload: ChatRequest,
    user_id: int = Depends(get_user_id),
    conn: sqlite3.Connection = Depends(get_db),
) -> ChatResponse:
    try:
        board_ops.require_board(conn, user_id, board_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    chat_limiter.check(str(user_id), "Too many messages. Please wait a moment before sending more.")
    board = fetch_board(conn, board_id)
    messages = build_structured_messages(board, payload.history, payload.message)
    content, model = call_openrouter(messages)
    structured = parse_structured_output(content)

    reply = structured.reply
    actions = structured.actions
    skipped = []
    if payload.apply_updates and actions:
        actions, skipped = apply_actions(conn, board_id, actions)
        board = fetch_board(conn, board_id)
        if skipped:
            reasons = "; ".join(sorted({item.reason for item in skipped}))
            reply = f"{reply}\n\nNot applied ({len(skipped)} of {len(skipped) + len(actions)}): {reasons}."

    return ChatResponse(
        response=reply,
        actions=actions,
        skipped=skipped,
        board=board,
        model=model,
    )
