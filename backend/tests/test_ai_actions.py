import json

import pytest
from pydantic import TypeAdapter

from app.ai import apply_actions, build_structured_messages, parse_structured_output
from app.database import connect_db, fetch_board, get_or_create_user
from app.models import (
    ChatAction,
    ChatHistoryItem,
    CreateCardAction,
    DeleteCardAction,
    MoveCardAction,
    UpdateCardAction,
)


@pytest.fixture
def conn(db_path):
    connection = connect_db()
    yield connection
    connection.close()


def _titles(board: dict, column_id: str) -> list[str]:
    column = next(item for item in board["columns"] if item["id"] == column_id)
    return [board["cards"][card_id]["title"] for card_id in column["cardIds"]]


def test_parse_structured_output() -> None:
    content = json.dumps(
        {
            "reply": "All set.",
            "actions": [
                {
                    "type": "create_card",
                    "columnId": "1",
                    "title": "New card",
                    "details": "Details",
                    "position": 0,
                }
            ],
        }
    )

    parsed = parse_structured_output(content)
    assert parsed.reply == "All set."
    assert parsed.actions
    assert parsed.actions[0].type == "create_card"


def test_numeric_ids_from_the_model_are_accepted() -> None:
    action = TypeAdapter(ChatAction).validate_python(
        {"type": "move_card", "cardId": 4, "columnId": 2, "position": 0}
    )
    assert (action.cardId, action.columnId) == ("4", "2")


def test_apply_actions_updates_board(conn) -> None:
    user_id = get_or_create_user(conn, "user")
    board = fetch_board(conn, user_id)

    first_column = board["columns"][0]
    second_column = board["columns"][1]
    first_card_id = board["columns"][0]["cardIds"][0]

    actions = [
        CreateCardAction(
            type="create_card",
            columnId=first_column["id"],
            title="AI card",
            details="",
            position=0,
        ),
        MoveCardAction(
            type="move_card",
            cardId=first_card_id,
            columnId=second_column["id"],
            position=0,
        ),
        UpdateCardAction(
            type="update_card",
            cardId=first_card_id,
            title="Updated title",
        ),
    ]

    applied, skipped = apply_actions(conn, user_id, actions)
    assert len(applied) == 3
    assert skipped == []
    updated = fetch_board(conn, user_id)
    assert updated["cards"][first_card_id]["title"] == "Updated title"
    assert updated["columns"][1]["cardIds"][0] == first_card_id
    assert _titles(updated, first_column["id"])[0] == "AI card"

    applied, skipped = apply_actions(
        conn, user_id, [DeleteCardAction(type="delete_card", cardId=first_card_id)]
    )
    assert len(applied) == 1
    assert first_card_id not in fetch_board(conn, user_id)["cards"]


def test_move_card_action_down_within_column(conn) -> None:
    user_id = get_or_create_user(conn, "user")
    board = fetch_board(conn, user_id)
    column = board["columns"][2]
    first = column["cardIds"][0]
    before = _titles(board, column["id"])
    assert len(before) == 2

    apply_actions(
        conn,
        user_id,
        [MoveCardAction(type="move_card", cardId=first, columnId=column["id"], position=1)],
    )

    assert _titles(fetch_board(conn, user_id), column["id"]) == [before[1], before[0]]


def test_invalid_actions_are_skipped_and_reported(conn) -> None:
    user_id = get_or_create_user(conn, "user")
    board = fetch_board(conn, user_id)
    column_id = board["columns"][0]["id"]
    card_id = board["columns"][0]["cardIds"][0]

    actions = [
        CreateCardAction(type="create_card", columnId="Backlog", title="x"),
        CreateCardAction(type="create_card", columnId="99999", title="x"),
        CreateCardAction(type="create_card", columnId=column_id, title=""),
        UpdateCardAction(type="update_card", cardId=card_id, title=""),
        UpdateCardAction(type="update_card", cardId="not-a-number", title="x"),
        MoveCardAction(type="move_card", cardId=card_id, columnId="99999"),
        DeleteCardAction(type="delete_card", cardId="99999"),
        UpdateCardAction(type="update_card", cardId=card_id, title="Kept"),
    ]
    applied, skipped = apply_actions(conn, user_id, actions)

    assert len(applied) == 1
    assert len(skipped) == 7
    assert {item.type for item in skipped} == {
        "create_card",
        "update_card",
        "move_card",
        "delete_card",
    }
    updated = fetch_board(conn, user_id)
    assert updated["cards"][card_id]["title"] == "Kept"
    assert len(updated["cards"]) == len(board["cards"])


def test_actions_cannot_touch_another_users_board(conn) -> None:
    owner = get_or_create_user(conn, "owner")
    other = get_or_create_user(conn, "other")
    owner_board = fetch_board(conn, owner)
    other_board = fetch_board(conn, other)
    foreign_card = owner_board["columns"][0]["cardIds"][0]
    foreign_column = owner_board["columns"][0]["id"]

    applied, skipped = apply_actions(
        conn,
        other,
        [
            DeleteCardAction(type="delete_card", cardId=foreign_card),
            UpdateCardAction(type="update_card", cardId=foreign_card, title="hacked"),
            MoveCardAction(
                type="move_card",
                cardId=other_board["columns"][0]["cardIds"][0],
                columnId=foreign_column,
            ),
        ],
    )

    assert applied == []
    assert len(skipped) == 3
    assert fetch_board(conn, owner)["cards"][foreign_card]["title"] != "hacked"


def test_prompt_contains_the_board_once() -> None:
    board = {
        "board": {"id": "1", "title": "My Board"},
        "columns": [{"id": "1", "title": "Backlog", "position": 0, "cardIds": ["7"]}],
        "cards": {"7": {"id": "7", "title": "Unique card title", "details": ""}},
    }
    messages = build_structured_messages(
        board, [ChatHistoryItem(role="user", content="earlier")], "now"
    )
    assert messages[0]["role"] == "system"
    assert messages[0]["content"].count("Unique card title") == 1
    assert [m["content"] for m in messages[1:]] == ["earlier", "now"]
