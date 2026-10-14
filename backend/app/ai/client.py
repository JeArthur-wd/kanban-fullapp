"""The OpenRouter HTTP call. Upstream failures become HTTPException with a user-facing detail."""

import httpx
from fastapi import HTTPException

from app.config import (
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_TEMPERATURE,
    get_openrouter_api_key,
)

REQUEST_TIMEOUT_SECONDS = 20


def upstream_error(status_code: int) -> HTTPException:
    if status_code == 429:
        return HTTPException(
            status_code=429,
            detail="The AI service is busy right now. Please try again in a moment.",
        )
    if status_code in (401, 402, 403):
        return HTTPException(
            status_code=502,
            detail="The AI service rejected the request. Check the API key and account credits.",
        )
    return HTTPException(status_code=502, detail="OpenRouter returned an error")


def call_openrouter(messages: list[dict[str, str]]) -> tuple[str, str | None]:
    """Send the messages and return (reply text, model name)."""
    api_key = get_openrouter_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENROUTER_API_KEY not configured")

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": OPENROUTER_TEMPERATURE,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="The AI service took too long to respond") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="OpenRouter request failed") from exc

    if response.status_code >= 400:
        raise upstream_error(response.status_code)

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="OpenRouter returned an invalid response") from exc
    choices = data.get("choices", []) if isinstance(data, dict) else []
    if not choices:
        raise HTTPException(status_code=502, detail="OpenRouter response missing choices")
    message_data = choices[0].get("message")
    if not message_data or "content" not in message_data:
        raise HTTPException(status_code=502, detail="OpenRouter response missing content")
    return str(message_data["content"]).strip(), data.get("model")
