import sqlite3

from fastapi import APIRouter, Depends

from app.ai import apply_actions, build_structured_messages, call_openrouter, parse_structured_output
from app.database import fetch_board, get_or_create_user
from app.dependencies import get_db, get_username
from app.models import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/api/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    username: str = Depends(get_username),
    conn: sqlite3.Connection = Depends(get_db),
) -> ChatResponse:
    user_id = get_or_create_user(conn, username)
    board = fetch_board(conn, user_id)
    messages = build_structured_messages(board, payload.history, payload.message)
    content, model = call_openrouter(messages)
    structured = parse_structured_output(content)

    reply = structured.reply
    actions = structured.actions
    skipped = []
    if payload.apply_updates and actions:
        actions, skipped = apply_actions(conn, user_id, actions)
        board = fetch_board(conn, user_id)
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
