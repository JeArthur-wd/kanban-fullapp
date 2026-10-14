import json

import httpx
import pytest

import app.ai.client as ai_module


class _DummyResponse:
    def __init__(self, content: str, status_code: int = 200) -> None:
        self.status_code = status_code
        self._content = content

    def json(self) -> dict:
        return {"choices": [{"message": {"content": self._content}}]}


class _BadBodyResponse:
    status_code = 200

    def json(self) -> dict:
        raise ValueError("not json")


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")


def _model_says(monkeypatch, content: str) -> None:
    monkeypatch.setattr(ai_module.httpx, "post", lambda *_a, **_k: _DummyResponse(content))


def test_chat_applies_actions(monkeypatch, client) -> None:
    board = client.get("/api/board").json()
    column_id = board["columns"][0]["id"]

    _model_says(
        monkeypatch,
        json.dumps(
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
        ),
    )

    response = client.post("/api/chat", json={"message": "Add a card."})
    assert response.status_code == 200

    payload = response.json()
    assert payload["response"] == "Created a card."
    assert payload["actions"][0]["type"] == "create_card"
    assert payload["skipped"] == []
    assert any(card["title"] == "AI created" for card in payload["board"]["cards"].values())


def test_chat_reports_actions_that_were_not_applied(monkeypatch, client) -> None:
    _model_says(
        monkeypatch,
        json.dumps({"reply": "Deleted the card.", "actions": [{"type": "delete_card", "cardId": "99999"}]}),
    )
    before = client.get("/api/board").json()

    response = client.post("/api/chat", json={"message": "delete it"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["actions"] == []
    assert payload["skipped"] == [{"type": "delete_card", "reason": "Card not found"}]
    assert payload["response"].startswith("Deleted the card.")
    assert "Not applied (1 of 1): Card not found" in payload["response"]
    assert payload["board"] == before


def test_chat_non_numeric_id_is_skipped_not_a_server_error(monkeypatch, client) -> None:
    _model_says(
        monkeypatch,
        json.dumps(
            {
                "reply": "Added.",
                "actions": [{"type": "create_card", "columnId": "Backlog", "title": "x"}],
            }
        ),
    )
    response = client.post("/api/chat", json={"message": "add"})
    assert response.status_code == 200
    assert len(response.json()["skipped"]) == 1


def test_chat_without_apply_updates_returns_proposed_actions(monkeypatch, client) -> None:
    _model_says(
        monkeypatch,
        json.dumps({"reply": "Would delete.", "actions": [{"type": "delete_card", "cardId": "1"}]}),
    )
    before = client.get("/api/board").json()
    response = client.post("/api/chat", json={"message": "x", "apply_updates": False})
    assert response.status_code == 200
    assert len(response.json()["actions"]) == 1
    assert client.get("/api/board").json() == before


def test_chat_accepts_json_wrapped_in_text(monkeypatch, client) -> None:
    _model_says(monkeypatch, 'Sure! {"reply": "Done.", "actions": []} Hope that helps.')
    response = client.post("/api/chat", json={"message": "Do something."})
    assert response.status_code == 200
    assert response.json()["response"] == "Done."


def test_chat_rejects_non_json(monkeypatch, client) -> None:
    _model_says(monkeypatch, "no json here")
    assert client.post("/api/chat", json={"message": "Do something."}).status_code == 502


def test_chat_rejects_schema_invalid_output(monkeypatch, client) -> None:
    _model_says(monkeypatch, json.dumps({"reply": "Hi", "actions": [{"type": "explode_board"}]}))
    assert client.post("/api/chat", json={"message": "Do something."}).status_code == 502


@pytest.mark.parametrize(
    ("upstream_status", "expected_status", "expected_text"),
    [
        (429, 429, "busy"),
        (402, 502, "credits"),
        (401, 502, "API key"),
        (500, 502, "OpenRouter returned an error"),
    ],
)
def test_chat_maps_upstream_errors(
    monkeypatch, client, upstream_status, expected_status, expected_text
) -> None:
    monkeypatch.setattr(
        ai_module.httpx,
        "post",
        lambda *_a, **_k: httpx.Response(
            upstream_status, json={"error": {"message": "x"}}, request=httpx.Request("POST", "http://x")
        ),
    )
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == expected_status
    assert expected_text in response.json()["detail"]


def test_chat_handles_non_json_upstream_body(monkeypatch, client) -> None:
    monkeypatch.setattr(ai_module.httpx, "post", lambda *_a, **_k: _BadBodyResponse())
    response = client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 502
    assert response.json()["detail"] == "OpenRouter returned an invalid response"


def test_chat_timeout_is_a_gateway_timeout(monkeypatch, client) -> None:
    def _raise(*_a, **_k):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(ai_module.httpx, "post", _raise)
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 504


def test_chat_network_error_is_bad_gateway(monkeypatch, client) -> None:
    def _raise(*_a, **_k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(ai_module.httpx, "post", _raise)
    assert client.post("/api/chat", json={"message": "hi"}).status_code == 502
