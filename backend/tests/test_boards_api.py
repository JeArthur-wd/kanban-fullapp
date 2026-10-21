from app.config import BASIC_COLUMNS, INITIAL_COLUMNS


def _boards(client) -> list[dict]:
    response = client.get("/api/boards")
    assert response.status_code == 200
    return response.json()


def test_a_new_account_has_one_sample_board(client) -> None:
    boards = _boards(client)
    assert len(boards) == 1
    assert boards[0]["title"] == "My Board"
    assert boards[0]["columnCount"] == len(INITIAL_COLUMNS)
    assert boards[0]["cardCount"] == sum(len(cards) for _, cards in INITIAL_COLUMNS)


def test_create_a_basic_board(client) -> None:
    created = client.post("/api/boards", json={"title": "  Launch  ", "description": "Q4 launch"})
    assert created.status_code == 200
    board_id = created.json()["id"]

    board = client.get(f"/api/boards/{board_id}").json()
    assert board["board"] == {"id": board_id, "title": "Launch", "description": "Q4 launch"}
    assert [column["title"] for column in board["columns"]] == BASIC_COLUMNS
    assert board["cards"] == {}
    assert [item["id"] for item in _boards(client)][-1] == board_id


def test_create_a_board_from_the_sample_template(client) -> None:
    board_id = client.post("/api/boards", json={"title": "Demo", "template": "sample"}).json()["id"]
    board = client.get(f"/api/boards/{board_id}").json()
    assert len(board["columns"]) == len(INITIAL_COLUMNS)
    assert len(board["cards"]) == sum(len(cards) for _, cards in INITIAL_COLUMNS)


def test_board_create_is_validated(client) -> None:
    assert client.post("/api/boards", json={"title": ""}).status_code == 422
    assert client.post("/api/boards", json={"title": "x" * 201}).status_code == 422
    assert client.post("/api/boards", json={"title": "x", "template": "huge"}).status_code == 422


def test_rename_and_describe_a_board(client, board_url) -> None:
    assert client.patch(board_url, json={"title": "Roadmap"}).status_code == 200
    assert client.patch(board_url, json={"description": "Plans"}).status_code == 200
    assert client.get(board_url).json()["board"]["title"] == "Roadmap"
    assert client.get(board_url).json()["board"]["description"] == "Plans"
    # A title of only spaces would be empty once trimmed.
    assert client.patch(board_url, json={"title": "   "}).status_code == 422
    assert client.get(board_url).json()["board"]["title"] == "Roadmap"


def test_boards_keep_their_own_columns_and_cards(client, board_url) -> None:
    second_id = client.post("/api/boards", json={"title": "Second"}).json()["id"]
    second = client.get(f"/api/boards/{second_id}").json()
    client.post(
        "/api/cards", json={"column_id": int(second["columns"][0]["id"]), "title": "Only here"}
    )

    first_titles = {card["title"] for card in client.get(board_url).json()["cards"].values()}
    second_titles = {
        card["title"] for card in client.get(f"/api/boards/{second_id}").json()["cards"].values()
    }
    assert second_titles == {"Only here"}
    assert "Only here" not in first_titles


def test_delete_a_board_removes_its_columns_and_cards(client, db_path) -> None:
    board_id = client.post("/api/boards", json={"title": "Temp", "template": "sample"}).json()["id"]
    assert client.delete(f"/api/boards/{board_id}").status_code == 200
    assert client.get(f"/api/boards/{board_id}").status_code == 404
    assert board_id not in {item["id"] for item in _boards(client)}

    from app.database import connect_db

    conn = connect_db()
    orphans = conn.execute(
        "SELECT COUNT(*) FROM columns WHERE board_id = ?", (int(board_id),)
    ).fetchone()[0]
    conn.close()
    assert orphans == 0


def test_the_last_board_can_be_deleted(client, board_url) -> None:
    assert client.delete(board_url).status_code == 200
    assert _boards(client) == []


def test_another_users_boards_are_invisible(client, board_url, make_user) -> None:
    other = make_user("eve")
    assert len(_boards(other)) == 1
    assert other.get(board_url).status_code == 404
    assert other.patch(board_url, json={"title": "Mine now"}).status_code == 404
    assert other.delete(board_url).status_code == 404
    assert client.get(board_url).json()["board"]["title"] == "My Board"


def test_unknown_board_is_404(client) -> None:
    assert client.get("/api/boards/99999").status_code == 404
    assert client.patch("/api/boards/99999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/boards/99999").status_code == 404
    assert client.post("/api/boards/99999/columns", json={"title": "x"}).status_code == 404


def test_board_card_count_ignores_archived_cards(client, board_url, db_path) -> None:
    from app.database import connect_db

    board = client.get(board_url).json()
    conn = connect_db()
    conn.execute("UPDATE cards SET archived = 1 WHERE id = ?", (int(board["columns"][0]["cardIds"][0]),))
    conn.commit()
    conn.close()
    assert _boards(client)[0]["cardCount"] == len(board["cards"]) - 1
