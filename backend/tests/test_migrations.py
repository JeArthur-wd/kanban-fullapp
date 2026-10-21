import sqlite3

import pytest

from app.database import MIGRATIONS, _migration_1_initial, connect_db, init_db, migrate, schema_version


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    path = tmp_path / "migrate.db"
    monkeypatch.setenv("PM_DB_PATH", str(path))
    return path


def _make_mvp_database(path) -> None:
    """A database as the single-board MVP left it: user_version 0, no password hashes."""
    conn = sqlite3.connect(path)
    _migration_1_initial(conn)
    conn.execute("INSERT INTO users (id, username) VALUES (1, 'user')")
    conn.execute("INSERT INTO boards (id, user_id, title) VALUES (10, 1, 'My Board')")
    conn.execute("INSERT INTO columns (id, board_id, title, position) VALUES (100, 10, 'Todo', 0)")
    conn.execute(
        "INSERT INTO cards (id, column_id, title, details, position) VALUES (1000, 100, 'Kept', 'd', 0)"
    )
    # MVP databases ran without foreign keys, so orphans could exist.
    conn.execute(
        "INSERT INTO cards (id, column_id, title, details, position) VALUES (1001, 999, 'Orphan', '', 0)"
    )
    conn.commit()
    conn.close()


def test_a_fresh_database_reaches_the_latest_version(db_env) -> None:
    init_db()
    conn = connect_db()
    assert schema_version(conn) == len(MIGRATIONS)
    conn.close()


def test_mvp_data_survives_the_migration(db_env) -> None:
    _make_mvp_database(db_env)
    init_db()

    conn = connect_db()
    assert schema_version(conn) == len(MIGRATIONS)
    user = conn.execute("SELECT username, display_name, session_epoch FROM users").fetchone()
    assert tuple(user) == ("user", "", 0)
    board = conn.execute("SELECT id, user_id, title, description FROM boards").fetchone()
    assert tuple(board) == (10, 1, "My Board", "")
    card = conn.execute("SELECT id, title, priority, due_date FROM cards").fetchone()
    assert tuple(card) == (1000, "Kept", "none", None)
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 1
    conn.close()


def test_migrated_database_allows_many_boards_and_cascades(db_env) -> None:
    _make_mvp_database(db_env)
    init_db()

    conn = connect_db()
    conn.execute("INSERT INTO boards (user_id, title) VALUES (1, 'Second')")
    assert conn.execute("SELECT COUNT(*) FROM boards WHERE user_id = 1").fetchone()[0] == 2
    conn.execute("DELETE FROM users WHERE id = 1")
    remaining = [
        conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("boards", "columns", "cards")
    ]
    conn.close()
    assert remaining == [0, 0, 0]


def test_migrated_cards_reject_unknown_priorities(db_env) -> None:
    init_db()
    conn = connect_db()
    conn.execute("INSERT INTO users (username) VALUES ('u')")
    conn.execute("INSERT INTO boards (user_id, title) VALUES (1, 'b')")
    conn.execute("INSERT INTO columns (board_id, title, position) VALUES (1, 'c', 0)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO cards (column_id, title, position, priority) VALUES (1, 'x', 0, 'urgent')"
        )
    conn.close()


def test_running_init_again_changes_nothing(db_env) -> None:
    _make_mvp_database(db_env)
    init_db()
    init_db()
    conn = connect_db()
    assert schema_version(conn) == len(MIGRATIONS)
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 1
    conn.close()


def test_a_failing_migration_is_rolled_back(db_env, monkeypatch) -> None:
    init_db()
    conn = connect_db()
    version = schema_version(conn)

    def _broken(connection):
        connection.execute("CREATE TABLE half_done (id INTEGER)")
        raise RuntimeError("boom")

    monkeypatch.setattr("app.database.MIGRATIONS", [*MIGRATIONS, _broken])
    with pytest.raises(RuntimeError, match="boom"):
        migrate(conn)
    assert schema_version(conn) == version
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "half_done" not in tables
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    conn.close()


def test_a_migration_that_breaks_references_is_refused(db_env, monkeypatch) -> None:
    init_db()
    conn = connect_db()
    version = schema_version(conn)

    def _orphan_maker(connection):
        connection.execute("INSERT INTO cards (column_id, title, position) VALUES (424242, 'x', 0)")

    monkeypatch.setattr("app.database.MIGRATIONS", [*MIGRATIONS, _orphan_maker])
    with pytest.raises(RuntimeError, match="broken references"):
        migrate(conn)
    assert schema_version(conn) == version
    assert conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 0
    conn.close()


def test_user_ids_are_never_reused(db_env) -> None:
    init_db()
    conn = connect_db()
    first = conn.execute("INSERT INTO users (username) VALUES ('a')").lastrowid
    conn.execute("DELETE FROM users WHERE id = ?", (first,))
    second = conn.execute("INSERT INTO users (username) VALUES ('b')").lastrowid
    conn.close()
    assert second != first
