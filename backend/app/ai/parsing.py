"""Turn the model's text reply into a validated StructuredChatOutput."""

import json

from fastapi import HTTPException
from pydantic import ValidationError

from app.models import StructuredChatOutput


def parse_structured_output(content: str) -> StructuredChatOutput:
    """Accept bare JSON or JSON wrapped in prose. Anything else is a 502."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        trimmed = content.strip()
        start = trimmed.find("{")
        end = trimmed.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(trimmed[start : end + 1])
            except json.JSONDecodeError as inner_exc:
                raise HTTPException(
                    status_code=502, detail="OpenRouter returned invalid JSON"
                ) from inner_exc
        else:
            raise HTTPException(status_code=502, detail="OpenRouter returned invalid JSON") from exc
    try:
        return StructuredChatOutput.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=502, detail="OpenRouter returned an unexpected response shape"
        ) from exc
