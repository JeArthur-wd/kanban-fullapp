"""The messages sent to the model: instructions plus the board, then history, then the new message."""

import json

from app.models import ChatHistoryItem

SYSTEM_INSTRUCTIONS = (
    "You are a Kanban assistant. Reply only as JSON with this shape:\n"
    '{"reply": string, "actions": [action, ...]}\n'
    "Keep replies concise (1-2 sentences) unless the user requests detail.\n"
    "Board data is ALWAYS provided below. Never claim you lack board data.\n"
    "If asked to summarize the project or board, use ONLY the provided board data.\n"
    "List the columns exactly as provided and mention a few key cards. Do not invent columns or cards.\n"
    "Action types (ids are the string ids from the board data):\n"
    '- create_card: {"type": "create_card", "columnId": string, "title": string, '
    '"details": string, "position": number|null}\n'
    '- update_card: {"type": "update_card", "cardId": string, "title": string|null, '
    '"details": string|null}\n'
    '- move_card: {"type": "move_card", "cardId": string, "columnId": string, '
    '"position": number|null}\n'
    '- delete_card: {"type": "delete_card", "cardId": string}\n'
    "Do not include any extra keys or text.\n\n"
)


def build_structured_messages(
    board: dict, history: list[ChatHistoryItem], message: str
) -> list[dict[str, str]]:
    system_prompt = (
        f"{SYSTEM_INSTRUCTIONS}Current board data (JSON, authoritative):\n{json.dumps(board)}"
    )
    messages_list = [{"role": "system", "content": system_prompt}]
    for item in history:
        messages_list.append({"role": item.role, "content": item.content})
    messages_list.append({"role": "user", "content": message})
    return messages_list
