"""AI chat: the OpenRouter client, prompt building, output parsing and action application."""

from app.ai.actions import apply_actions
from app.ai.client import call_openrouter
from app.ai.parsing import parse_structured_output
from app.ai.prompts import build_structured_messages

__all__ = [
    "apply_actions",
    "build_structured_messages",
    "call_openrouter",
    "parse_structured_output",
]
