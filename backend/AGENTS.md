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
├── config.py        # Environment config, constants, seed data
├── models/          # Pydantic models: board.py (REST), chat.py (chat + AI actions)
├── database.py      # DB connection (foreign keys, WAL), init, seeding, queries
├── board_ops.py     # Column/card create, move, delete; shared by routes and AI actions
├── ai/              # client.py (OpenRouter), prompts.py, parsing.py, actions.py (apply to board)
├── dependencies.py  # FastAPI dependencies (get_db, get_username from the session cookie)
├── auth.py          # Signed session cookie, credential check
├── ratelimit.py     # In-memory sliding-window limiter
└── routes/
    ├── __init__.py  # Router aggregation
    ├── health.py    # /health and /api/hello
    ├── board.py     # Board, column, card CRUD endpoints
    ├── auth.py      # Login, logout, session
    ├── chat.py      # Chat endpoint with AI
    └── static.py    # Static file serving
```

## Entry point
- app/main.py exposes the FastAPI application instance as `app` (built by `create_app()`).

## Routes
- GET /health: JSON status
- GET /api/hello: JSON example endpoint
- POST /api/login, POST /api/logout, GET /api/session: server-side sign-in with a session cookie. All routes below need the cookie (401 without it).
- GET /api/board: Fetch user's board
- POST/PATCH/DELETE /api/columns/{id}: Column CRUD
- POST/PATCH/DELETE /api/cards/{id}: Card CRUD
- POST /api/chat: AI chat with structured output
- GET /: Serves frontend or fallback HTML

## Tests
- Unit tests: tests/test_main.py, test_board_api.py, test_auth.py, test_chat_api.py, test_chat_structured_api.py, test_ai_actions.py. `tests/conftest.py` gives each test a temporary database and a signed-in `client`.
- Integration tests (live target): tests/test_integration.py
	- Uses PM_BASE_URL to target a running backend

## Container
- Dockerfile at repo root builds a Python 3.12 image and installs dependencies with uv.
- Runs as non-root user `appuser`
- Includes HEALTHCHECK directive
