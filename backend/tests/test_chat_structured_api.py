import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.database import init_db
import app.ai as ai_module


class _DummyResponse:
    def __init__(self, content: str) -> None:
        self.status_code = 200
        self._content = content

    def json(self) -> dict:
        return {
            "choices": [
                {
                    "message": {
                        "content": self._content,
                    }
                }
            ]
        }


def _make_client(tmp_path: Path) -> TestClient:
    os.environ["PM_DB_PATH"] = str(tmp_path / "test.db")
    init_db()
    return TestClient(app)


def test_chat_applies_actions(monkeypatch, tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    board = client.get("/api/board").json()
    column_id = board["columns"][0]["id"]

    response_content = json.dumps(
        {
            "reply": "Created a card.",
            "actions": [
                {
                    "type": "create_card",
                    "columnId": column_id,
                    "title": "AI created",
                    "details": "",
                    "position": 0,
                }
            ],
        }
    )

    def _mock_post(*_args, **_kwargs):
        return _DummyResponse(response_content)

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.httpx, "post", _mock_post)

    response = client.post("/api/chat", json={"message": "Add a card."})
    assert response.status_code == 200

    payload = response.json()
    assert payload["response"] == "Created a card."
    assert payload["actions"][0]["type"] == "create_card"

    updated_board = payload["board"]
    assert any(card["title"] == "AI created" for card in updated_board["cards"].values())


def _post_with_model_content(monkeypatch, tmp_path: Path, content: str):
    client = _make_client(tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(ai_module.httpx, "post", lambda *_a, **_k: _DummyResponse(content))
    return client.post("/api/chat", json={"message": "Do something."})


def test_chat_accepts_json_wrapped_in_text(monkeypatch, tmp_path: Path) -> None:
    content = 'Sure! {"reply": "Done.", "actions": []} Hope that helps.'
    response = _post_with_model_content(monkeypatch, tmp_path, content)
    assert response.status_code == 200
    assert response.json()["response"] == "Done."


def test_chat_rejects_non_json(monkeypatch, tmp_path: Path) -> None:
    response = _post_with_model_content(monkeypatch, tmp_path, "no json here")
    assert response.status_code == 502


def test_chat_rejects_schema_invalid_output(monkeypatch, tmp_path: Path) -> None:
    content = json.dumps({"reply": "Hi", "actions": [{"type": "explode_board"}]})
    response = _post_with_model_content(monkeypatch, tmp_path, content)
    assert response.status_code == 502
