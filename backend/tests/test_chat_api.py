def test_chat_missing_api_key(monkeypatch, client, board_url) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    response = client.post(f"{board_url}/chat", json={"message": "2+2"})
    assert response.status_code == 500
    assert response.json() == {"detail": "OPENROUTER_API_KEY not configured"}
