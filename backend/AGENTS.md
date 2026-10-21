# Backend overview

## Stack
- FastAPI
- Uvicorn
- SQLite
- Pytest for unit and integration tests

## Package Structure
```
app/
├── __init__.py
├── main.py          # create_app() factory and the `app` instance; lifespan, static mounts, routers
├── config.py        # Environment config, constants, seed data and board templates
├── models/          # Pydantic models: account.py, board.py (REST), chat.py (chat + AI actions)
├── database.py      # DB connection (foreign keys, WAL), migrations, fetch_board
├── board_ops.py     # Board/column/card create, move, delete and board access checks
├── accounts.py      # Create user, demo account, profile, password, delete
├── ai/              # client.py (OpenRouter), prompts.py, parsing.py, actions.py (apply to board)
├── dependencies.py  # FastAPI dependencies (get_db, get_current_user, get_user_id)
├── auth.py          # scrypt passwords, signed session cookie
├── ratelimit.py     # In-memory sliding-window limiter
└── routes/
    ├── __init__.py  # Router aggregation
    ├── health.py    # /health and /api/hello
    ├── board.py     # Board, column, card CRUD endpoints
    ├── auth.py      # Login, sign-up, logout, session
    ├── account.py   # Profile, password, delete account
    ├── chat.py      # Chat endpoint with AI
    └── static.py    # Static file serving
```

## Entry point
- app/main.py exposes the FastAPI application instance as `app` (built by `create_app()`).

## Routes
- GET /health: JSON status
- GET /api/hello: JSON example endpoint
- POST /api/login, POST /api/register, POST /api/logout, GET /api/session: sign-in and sign-up with a session cookie. All routes below need the cookie (401 without it).
- GET/PATCH/DELETE /api/me, POST /api/me/password: account settings (password needed to delete or change it)
- GET/POST /api/boards, GET/PATCH/DELETE /api/boards/{id}: boards (404 for boards the user may not use)
- POST /api/boards/{id}/columns, PATCH/DELETE /api/columns/{id}: columns
- POST /api/cards, PATCH/DELETE /api/cards/{id}: cards (title, details, priority, due_date, column, position)
- POST /api/boards/{id}/chat: AI chat with structured output
- GET /: Serves frontend or fallback HTML; unknown /api paths are JSON 404s

## Tests
- Unit tests: tests/test_*.py. `tests/conftest.py` gives each test a temporary migrated database with the demo account, a signed-in `client`, `board_url` (the demo user's first board) and `make_user` (another signed-in account). test_migrations.py builds an MVP-era database by hand and migrates it.
- Integration tests (live target): tests/test_integration.py
	- Uses PM_BASE_URL to target a running backend

## Container
- Dockerfile at repo root builds a Python 3.12 image and installs dependencies with uv.
- Runs as non-root user `appuser`
- Includes HEALTHCHECK directive
