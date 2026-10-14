import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import app, create_app
from app.config import resolve_static_dir
from app.routes import static as static_module
from app.routes.static import mount_static_assets

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_html_fallback_without_a_built_frontend(monkeypatch) -> None:
    monkeypatch.setattr(static_module, "STATIC_DIR", None)
    response = client.get("/")
    assert response.status_code == 200
    assert "PM MVP" in response.text


def test_api_hello() -> None:
    response = client.get("/api/hello")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello from FastAPI"}


def test_root_serves_static_index(tmp_path) -> None:
    original_static_dir = static_module.STATIC_DIR
    index_path = tmp_path / "index.html"
    index_path.write_text("Kanban Studio")

    static_module.STATIC_DIR = tmp_path
    response = client.get("/")
    assert response.status_code == 200
    assert "Kanban Studio" in response.text
    static_module.STATIC_DIR = original_static_dir


def test_static_fallback_serves_files(tmp_path) -> None:
    original_static_dir = static_module.STATIC_DIR
    index_path = tmp_path / "index.html"
    index_path.write_text("Index content")
    file_path = tmp_path / "hello.txt"
    file_path.write_text("Hello file")

    static_module.STATIC_DIR = tmp_path
    response = client.get("/hello.txt")
    assert response.status_code == 200
    assert response.text == "Hello file"
    static_module.STATIC_DIR = original_static_dir


def test_static_fallback_returns_index(tmp_path) -> None:
    original_static_dir = static_module.STATIC_DIR
    index_path = tmp_path / "index.html"
    index_path.write_text("Index content")

    static_module.STATIC_DIR = tmp_path
    response = client.get("/unknown/path")
    assert response.status_code == 200
    assert "Index content" in response.text
    static_module.STATIC_DIR = original_static_dir


def test_static_fallback_404_when_missing() -> None:
    original_static_dir = static_module.STATIC_DIR
    static_module.STATIC_DIR = None

    response = client.get("/missing")
    assert response.status_code == 404
    static_module.STATIC_DIR = original_static_dir


def test_resolve_static_dir_uses_env(tmp_path) -> None:
    original_env = os.environ.get("PM_STATIC_DIR")
    os.environ["PM_STATIC_DIR"] = str(tmp_path)
    try:
        resolved = resolve_static_dir()
        assert resolved == tmp_path
    finally:
        if original_env is None:
            os.environ.pop("PM_STATIC_DIR", None)
        else:
            os.environ["PM_STATIC_DIR"] = original_env


def test_mount_static_assets(tmp_path) -> None:
    (tmp_path / "_next").mkdir()
    (tmp_path / "_next" / "app.js").write_text("asset")
    (tmp_path / "static").mkdir()
    (tmp_path / "static" / "logo.txt").write_text("logo")
    fresh = FastAPI()
    mount_static_assets(fresh, tmp_path)
    fresh_client = TestClient(fresh)
    assert fresh_client.get("/_next/app.js").text == "asset"
    assert fresh_client.get("/static/logo.txt").text == "logo"


def test_mount_static_assets_skips_missing_folders(tmp_path) -> None:
    fresh = FastAPI()
    mount_static_assets(fresh, tmp_path)
    fresh_client = TestClient(fresh)
    assert fresh_client.get("/_next/app.js").status_code == 404
    assert fresh_client.get("/static/logo.txt").status_code == 404


def test_create_app_builds_independent_apps_with_all_routes() -> None:
    first, second = create_app(), create_app()
    assert first is not second
    paths = set(first.openapi()["paths"])
    for expected in ["/health", "/api/hello", "/api/login", "/api/board", "/api/chat"]:
        assert expected in paths
    assert TestClient(second).get("/health").json() == {"status": "ok"}


def test_static_fallback_directory_index(tmp_path) -> None:
    original_static_dir = static_module.STATIC_DIR
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "index.html").write_text("Nested index")
    (tmp_path / "index.html").write_text("Root index")

    static_module.STATIC_DIR = tmp_path
    response = client.get("/nested")
    assert response.status_code == 200
    assert "Nested index" in response.text
    static_module.STATIC_DIR = original_static_dir


def test_static_fallback_404_without_index(tmp_path) -> None:
    original_static_dir = static_module.STATIC_DIR
    static_module.STATIC_DIR = tmp_path

    response = client.get("/no-index")
    assert response.status_code == 404
    static_module.STATIC_DIR = original_static_dir


def _site(tmp_path):
    static_dir = tmp_path / "site" / "out"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("Index content")
    (tmp_path / "site" / "secret.txt").write_text("OUTSIDE")
    (tmp_path / "abs_secret.txt").write_text("ABSOLUTE")
    return static_dir


def test_static_fallback_blocks_path_traversal(tmp_path, monkeypatch) -> None:
    static_dir = _site(tmp_path)
    monkeypatch.setattr(static_module, "STATIC_DIR", static_dir)
    absolute = str(tmp_path / "abs_secret.txt").replace("\\", "/").lstrip("/")

    for path in [
        "../secret.txt",
        "../../abs_secret.txt",
        "a/../../secret.txt",
        "/" + absolute,
        str(tmp_path / "abs_secret.txt"),
    ]:
        response = static_module.static_fallback(path)
        assert response.status_code == 404, path
        assert b"OUTSIDE" not in bytes(response.body), path


def test_static_fallback_blocks_traversal_over_http(tmp_path, monkeypatch) -> None:
    static_dir = _site(tmp_path)
    monkeypatch.setattr(static_module, "STATIC_DIR", static_dir)
    absolute = str(tmp_path / "abs_secret.txt").replace("\\", "/").lstrip("/")

    for path in ["/%2e%2e/secret.txt", "/..%2fsecret.txt", "//" + absolute, "/../secret.txt"]:
        response = client.get(path)
        assert "OUTSIDE" not in response.text, path
        assert "ABSOLUTE" not in response.text, path


def test_static_fallback_still_serves_files_inside_root(tmp_path, monkeypatch) -> None:
    static_dir = _site(tmp_path)
    (static_dir / "assets").mkdir()
    (static_dir / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(static_module, "STATIC_DIR", static_dir)
    assert client.get("/assets/app.js").text == "console.log(1)"
    assert client.get("/some/client/route").text == "Index content"


def test_static_fallback_null_byte_does_not_error(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(static_module, "STATIC_DIR", _site(tmp_path))
    response = static_module.static_fallback("bad\x00name")
    assert response.status_code in (200, 404)
