"""Models for /api/chat: request, response, and the structured output expected from the model."""

from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field

from app.config import CHAT_HISTORY_MAX_ITEMS, CHAT_MESSAGE_MAX_CHARS


def _id_to_str(value: object) -> object:
    # Models sometimes return numeric ids as JSON numbers.
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return value


ModelId = Annotated[str, BeforeValidator(_id_to_str)]


class ChatHistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., max_length=CHAT_MESSAGE_MAX_CHARS * 2)


class CreateCardAction(BaseModel):
    type: Literal["create_card"]
    columnId: ModelId
    title: str
    details: str = ""
    position: int | None = None


class UpdateCardAction(BaseModel):
    type: Literal["update_card"]
    cardId: ModelId
    title: str | None = None
    details: str | None = None


class MoveCardAction(BaseModel):
    type: Literal["move_card"]
    cardId: ModelId
    columnId: ModelId
    position: int | None = None


class DeleteCardAction(BaseModel):
    type: Literal["delete_card"]
    cardId: ModelId


ChatAction = Annotated[
    CreateCardAction | UpdateCardAction | MoveCardAction | DeleteCardAction,
    Field(discriminator="type"),
]


class StructuredChatOutput(BaseModel):
    reply: str
    actions: list[ChatAction] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=CHAT_MESSAGE_MAX_CHARS)
    history: list[ChatHistoryItem] = Field(default_factory=list, max_length=CHAT_HISTORY_MAX_ITEMS)
    apply_updates: bool = True


class SkippedAction(BaseModel):
    type: str
    reason: str


class ChatResponse(BaseModel):
    response: str
    actions: list[ChatAction] = Field(default_factory=list)
    skipped: list[SkippedAction] = Field(default_factory=list)
    board: dict | None = None
    model: str | None = None
