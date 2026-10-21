import sqlite3

from app.database import connect_db


def _titles(board: dict, column_id: str) -> list[str]:
    column = next(item for item in board["columns"] if item["id"] == column_id)
    return [board["cards"][card_id]["title"] for card_id in column["cardIds"]]


def _add_card(client, column_id: str, title: str) -> str:
    response = client.post("/api/cards", json={"column_id": int(column_id), "title": title})
    assert response.status_code == 200
    return response.json()["id"]


def test_get_board_returns_seeded_data(client, board_url) -> None:
    response = client.get(board_url)
    assert response.status_code == 200
    data = response.json()
    assert len(data["columns"]) == 5
    assert len(data["cards"]) >= 8


def test_create_and_rename_column(client, board_url) -> None:
    create = client.post(f"{board_url}/columns", json={"title": "New Column"})
    assert create.status_code == 200
    column_id = create.json()["id"]

    rename = client.patch(f"/api/columns/{column_id}", json={"title": "Renamed"})
    assert rename.status_code == 200

    board = client.get(board_url).json()
    titles = [column["title"] for column in board["columns"]]
    assert "Renamed" in titles


def test_move_column(client, board_url) -> None:
    board = client.get(board_url).json()
    first_id = board["columns"][0]["id"]
    client.patch(f"/api/columns/{first_id}", json={"position": 4})
    ids = [column["id"] for column in client.get(board_url).json()["columns"]]
    assert ids[-1] == first_id


def test_empty_column_title_is_rejected(client, board_url) -> None:
    board = client.get(board_url).json()
    column_id = board["columns"][0]["id"]
    response = client.patch(f"/api/columns/{column_id}", json={"title": ""})
    assert response.status_code == 422


def test_create_move_and_delete_card(client, board_url) -> None:
    board = client.get(board_url).json()
    first_column = board["columns"][0]
    second_column = board["columns"][1]

    create = client.post(
        "/api/cards",
        json={
            "column_id": int(first_column["id"]),
            "title": "New Card",
            "details": "Details",
        },
    )
    assert create.status_code == 200
    card_id = create.json()["id"]

    move = client.patch(
        f"/api/cards/{card_id}",
        json={"column_id": int(second_column["id"]), "position": 0},
    )
    assert move.status_code == 200

    updated = client.get(board_url).json()
    assert updated["columns"][1]["cardIds"][0] == card_id

    delete = client.delete(f"/api/cards/{card_id}")
    assert delete.status_code == 200

    final = client.get(board_url).json()
    assert card_id not in final["cards"]


def test_update_card_title_and_details(client, board_url) -> None:
    board = client.get(board_url).json()
    card_id = board["columns"][0]["cardIds"][0]
    response = client.patch(f"/api/cards/{card_id}", json={"title": "T", "details": "D"})
    assert response.status_code == 200
    card = client.get(board_url).json()["cards"][card_id]
    assert (card["title"], card["details"]) == ("T", "D")


def test_move_card_down_within_column(client, board_url) -> None:
    board = client.get(board_url).json()
    column_id = board["columns"][2]["id"]
    _add_card(client, column_id, "Third")
    board = client.get(board_url).json()
    first = board["columns"][2]["cardIds"][0]
    before = _titles(board, column_id)
    assert len(before) == 3

    response = client.patch(
        f"/api/cards/{first}", json={"column_id": int(column_id), "position": 2}
    )
    assert response.status_code == 200

    after = _titles(client.get(board_url).json(), column_id)
    assert after == [before[1], before[2], before[0]]


def test_move_card_up_within_column(client, board_url) -> None:
    board = client.get(board_url).json()
    column_id = board["columns"][2]["id"]
    _add_card(client, column_id, "Third")
    board = client.get(board_url).json()
    last = board["columns"][2]["cardIds"][2]
    before = _titles(board, column_id)

    client.patch(f"/api/cards/{last}", json={"column_id": int(column_id), "position": 0})

    after = _titles(client.get(board_url).json(), column_id)
    assert after == [before[2], before[0], before[1]]


def test_move_card_to_middle_within_column(client, board_url) -> None:
    board = client.get(board_url).json()
    column_id = board["columns"][2]["id"]
    _add_card(client, column_id, "Third")
    _add_card(client, column_id, "Fourth")
    board = client.get(board_url).json()
    before = _titles(board, column_id)
    first = board["columns"][2]["cardIds"][0]

    client.patch(f"/api/cards/{first}", json={"column_id": int(column_id), "position": 2})

    after = _titles(client.get(board_url).json(), column_id)
    assert after == [before[1], before[2], before[0], before[3]]


def test_same_column_without_position_is_a_no_op(client, board_url) -> None:
    board = client.get(board_url).json()
    column_id = board["columns"][2]["id"]
    before = _titles(board, column_id)
    first = board["columns"][2]["cardIds"][0]
    client.patch(f"/api/cards/{first}", json={"column_id": int(column_id)})
    assert _titles(client.get(board_url).json(), column_id) == before


def test_move_card_keeps_positions_dense_in_both_columns(client, db_path, board_url) -> None:
    board = client.get(board_url).json()
    source, target = board["columns"][0], board["columns"][4]
    card_id = source["cardIds"][0]

    client.patch(f"/api/cards/{card_id}", json={"column_id": int(target["id"]), "position": 1})

    conn = connect_db()
    for column in (source, target):
        positions = [
            row["position"]
            for row in conn.execute(
                "SELECT position FROM cards WHERE column_id = ? ORDER BY position",
                (int(column["id"]),),
            )
        ]
        assert positions == list(range(len(positions)))
    conn.close()


def test_delete_column_removes_cards(client, board_url) -> None:
    board = client.get(board_url).json()
    target_column = board["columns"][0]
    column_id = target_column["id"]
    card_ids = list(target_column["cardIds"])

    delete = client.delete(f"/api/columns/{column_id}")
    assert delete.status_code == 200

    updated = client.get(board_url).json()
    assert column_id not in {column["id"] for column in updated["columns"]}
    for card_id in card_ids:
        assert card_id not in updated["cards"]


def test_deleting_every_column_does_not_reseed(client, board_url) -> None:
    board = client.get(board_url).json()
    for column in board["columns"]:
        assert client.delete(f"/api/columns/{column['id']}").status_code == 200
    assert client.get(board_url).json()["columns"] == []


def test_unknown_card_and_column_return_404(client) -> None:
    assert client.patch("/api/cards/99999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/cards/99999").status_code == 404
    assert client.patch("/api/columns/99999", json={"title": "x"}).status_code == 404
    assert client.delete("/api/columns/99999").status_code == 404
    assert client.post("/api/cards", json={"column_id": 99999, "title": "x"}).status_code == 404


def test_failed_move_does_not_leave_a_partial_update(client, board_url) -> None:
    board = client.get(board_url).json()
    card_id = board["columns"][0]["cardIds"][0]
    original = board["cards"][card_id]["title"]

    response = client.patch(
        f"/api/cards/{card_id}", json={"title": "Changed", "column_id": 99999}
    )
    assert response.status_code == 404
    assert client.get(board_url).json()["cards"][card_id]["title"] == original


def test_create_card_with_priority_and_due_date(client, board_url) -> None:
    column_id = client.get(board_url).json()["columns"][0]["id"]
    created = client.post(
        "/api/cards",
        json={
            "column_id": int(column_id),
            "title": "Ship it",
            "priority": "high",
            "due_date": "2026-11-02",
        },
    )
    assert created.status_code == 200
    card = client.get(board_url).json()["cards"][created.json()["id"]]
    assert (card["priority"], card["dueDate"]) == ("high", "2026-11-02")


def test_new_cards_default_to_no_priority_and_no_due_date(client, board_url) -> None:
    card_id = _add_card(client, client.get(board_url).json()["columns"][0]["id"], "Plain")
    card = client.get(board_url).json()["cards"][card_id]
    assert (card["priority"], card["dueDate"]) == ("none", None)


def test_update_card_sets_and_clears_due_date(client, board_url) -> None:
    card_id = client.get(board_url).json()["columns"][0]["cardIds"][0]
    client.patch(f"/api/cards/{card_id}", json={"due_date": "2026-12-01", "priority": "low"})
    card = client.get(board_url).json()["cards"][card_id]
    assert (card["priority"], card["dueDate"]) == ("low", "2026-12-01")

    # Sending other fields leaves the due date alone; an explicit null clears it.
    client.patch(f"/api/cards/{card_id}", json={"title": "Renamed"})
    assert client.get(board_url).json()["cards"][card_id]["dueDate"] == "2026-12-01"
    client.patch(f"/api/cards/{card_id}", json={"due_date": None})
    card = client.get(board_url).json()["cards"][card_id]
    assert (card["dueDate"], card["priority"], card["title"]) == (None, "low", "Renamed")


def test_card_fields_are_validated(client, board_url) -> None:
    card_id = client.get(board_url).json()["columns"][0]["cardIds"][0]
    assert client.patch(f"/api/cards/{card_id}", json={"priority": "urgent"}).status_code == 422
    assert client.patch(f"/api/cards/{card_id}", json={"due_date": "soon"}).status_code == 422
    assert client.patch(f"/api/cards/{card_id}", json={"due_date": "2026-02-30"}).status_code == 422


def test_columns_and_cards_of_another_user_are_not_found(client, board_url, make_user) -> None:
    board = client.get(board_url).json()
    column_id = board["columns"][0]["id"]
    card_id = board["columns"][0]["cardIds"][0]
    other = make_user("mallory")

    assert other.get(board_url).status_code == 404
    assert other.patch(f"/api/cards/{card_id}", json={"title": "x"}).status_code == 404
    assert other.delete(f"/api/cards/{card_id}").status_code == 404
    assert other.patch(f"/api/columns/{column_id}", json={"title": "x"}).status_code == 404
    assert other.delete(f"/api/columns/{column_id}").status_code == 404
    assert other.post(f"{board_url}/columns", json={"title": "x"}).status_code == 404
    response = other.post("/api/cards", json={"column_id": int(column_id), "title": "x"})
    assert response.status_code == 404
    assert client.get(board_url).json() == board


def test_a_card_cannot_move_to_a_column_on_another_board(client, board_url) -> None:
    card_id = client.get(board_url).json()["columns"][0]["cardIds"][0]
    other_id = client.post("/api/boards", json={"title": "Other"}).json()["id"]
    other_column = client.get(f"/api/boards/{other_id}").json()["columns"][0]["id"]

    response = client.patch(f"/api/cards/{card_id}", json={"column_id": int(other_column)})
    assert response.status_code == 404
    assert card_id in client.get(board_url).json()["cards"]


def test_concurrent_requests_do_not_fail(client, board_url) -> None:
    # Regression for review H1: a connection opened on one threadpool thread was used and
    # closed on another, and sqlite3 refused with ProgrammingError (a 500). TestClient runs
    # requests one at a time, so this drives the app concurrently on one event loop.
    import asyncio

    import httpx

    from app.main import app

    cookies = {"pm_session": client.cookies.get("pm_session").strip('"')}

    async def _burst() -> list[int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test", cookies=cookies
        ) as http:
            responses = await asyncio.gather(*(http.get(board_url) for _ in range(150)))
        return [response.status_code for response in responses]

    assert set(asyncio.run(_burst())) == {200}


def test_foreign_keys_are_enforced(db_path) -> None:
    conn = connect_db()
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    try:
        conn.execute("INSERT INTO cards (column_id, title, position) VALUES (9999, 'x', 0)")
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    conn.close()
    assert raised


def test_database_uses_wal(db_path) -> None:
    conn = connect_db()
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    conn.close()
    assert mode == "wal"
