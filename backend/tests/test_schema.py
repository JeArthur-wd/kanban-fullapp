import json
from pathlib import Path


def test_schema_json_structure() -> None:
    schema_path = Path(__file__).resolve().parents[2] / "docs" / "kanban-schema.json"
    data = json.loads(schema_path.read_text())

    assert data["db"] == "sqlite"
    assert data["schemaVersion"]

    tables = {table["name"]: table for table in data["tables"]}
    assert {"users", "boards", "columns", "cards"}.issubset(tables.keys())

    users_columns = {col["name"] for col in tables["users"]["columns"]}
    assert {"id", "username", "created_at"}.issubset(users_columns)

    boards_columns = {col["name"] for col in tables["boards"]["columns"]}
    assert {"id", "user_id", "title"}.issubset(boards_columns)

    columns_columns = {col["name"] for col in tables["columns"]["columns"]}
    assert {"id", "board_id", "title", "position"}.issubset(columns_columns)

    cards_columns = {col["name"] for col in tables["cards"]["columns"]}
    assert {"id", "column_id", "title", "details", "priority", "due_date", "position"}.issubset(
        cards_columns
    )


def test_schema_json_matches_the_database(db_path) -> None:
    """The documented columns are exactly the ones the migrations create."""
    from app.database import connect_db

    schema_path = Path(__file__).resolve().parents[2] / "docs" / "kanban-schema.json"
    documented = {
        table["name"]: {col["name"] for col in table["columns"]}
        for table in json.loads(schema_path.read_text())["tables"]
    }
    conn = connect_db()
    actual = {
        name: {row["name"] for row in conn.execute(f"PRAGMA table_info({name})")}
        for name in documented
    }
    conn.close()
    assert actual == documented
