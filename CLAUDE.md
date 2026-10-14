# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Project Management MVP web app with a Kanban board and AI chat assistant. Users sign in, view/manage a Kanban board with drag-and-drop, and interact with an AI that can create/edit/move/delete cards.

**Stack:** Next.js 16 frontend (React 19, TypeScript, Tailwind v4, @dnd-kit), statically exported and served by a Python FastAPI backend, SQLite database, all packaged in one Docker image. AI via OpenRouter (default model `openai/gpt-oss-120b`).

**MVP constraints:** One login (`user`/`password` by default, checked on the server), one board per user, fixed (renamable) columns. The DB schema supports multiple users.

## Commands

### Running the app (Docker)
Requires a `.env` in the repo root (copy `.env.example`, set `OPENROUTER_API_KEY`). Docker Desktop must be running first.
```bash
scripts/start-mac.sh   scripts/stop-mac.sh      # Mac
scripts/start-linux.sh scripts/stop-linux.sh    # Linux
scripts/start-windows.ps1  scripts/stop-windows.ps1   # Windows
```
App at http://localhost:8000. The start scripts rebuild the image every time (`docker build -t pm-app`), so frontend or backend changes only show up after a restart. The frontend is a static export baked into the image, not hot-reloaded.

For live tests, run detached so the terminal stays free:
```bash
docker build -t pm-app . && docker rm -f pm-app
docker run -d --name pm-app --env-file .env -p 8000:8000 pm-app
curl -sf http://127.0.0.1:8000/health
```

### Frontend (from `frontend/`)
```bash
npm run dev           # Dev server (needs the backend for API calls; set NEXT_PUBLIC_API_BASE)
npm run build         # Static export to frontend/out
npm run lint          # ESLint
npm run test:unit     # Vitest (jsdom), src/**/*.test.{ts,tsx}
npx vitest run src/lib/kanban.test.ts   # Single test file
npm run test:e2e      # Playwright (tests/kanban.spec.ts)
npm run test:all      # Unit + e2e
```
Playwright targets `http://127.0.0.1:8000` and runs the platform start script as its web server, with `reuseExistingServer: true`. If the container is already running it will test that build, not your working tree.

### Backend (from `backend/`)
Tests import `app.*`, so run pytest from `backend/`.
```bash
pytest                           # All tests (live tests skip without env)
pytest tests/test_board_api.py   # Single file
pytest -k "test_name"            # Single test
pytest --cov=app                 # Coverage
PM_BASE_URL=http://127.0.0.1:8000 pytest tests/test_integration.py   # Live tests against a running container
```
`test_integration.py` skips unless `PM_BASE_URL` is set; the live OpenRouter test also needs `OPENROUTER_API_KEY`. `docs/PLAN.md` runs these from the repo root with `PYTHONPATH=<repo root> pytest backend`.

## Architecture

**Backend (`backend/app/`):**
- `main.py` - `create_app()` factory (lifespan runs `init_db()`, mounts `_next` and `static` from the exported frontend, includes the routers) and the module-level `app` that uvicorn runs. No endpoints live here; `routes/health.py` has `/health` and `/api/hello`.
- `routes/auth.py` - `POST /api/login`, `POST /api/logout`, `GET /api/session`. `routes/board.py` - `GET /api/board`, plus POST/PATCH/DELETE for `/api/columns` and `/api/cards`. `routes/chat.py` - `POST /api/chat`. `routes/static.py` - serves the exported frontend at `/` with a catch-all fallback (registered last; resolves paths and refuses anything outside the static root).
- `board_ops.py` - the one place that creates, moves and deletes columns and cards (ordering, ownership checks). Both the REST routes and the AI actions call it; do not copy ordering code elsewhere.
- `database.py` - raw `sqlite3` (no ORM): schema, foreign keys on, WAL, seeding (`config.INITIAL_COLUMNS`, done when a board is first created), `fetch_board`, and `resequence_positions`. `dependencies.py` - `get_db` (per-request connection) and `get_username` (reads the session cookie, 401 if missing).
- `auth.py` - HMAC-signed session cookie. `ratelimit.py` - small in-memory limiter used for login and chat.
- `ai/` - the AI chat pieces: `client.py` (OpenRouter call and upstream error mapping), `prompts.py`, `parsing.py` (model text to validated output), `actions.py` (`apply_actions`, via `board_ops`). `models/` - Pydantic models: `board.py` (REST requests) and `chat.py` (chat request/response, AI actions). Both packages re-export their public names, so `from app.ai import ...` and `from app.models import ...` work.
- `config.py` - env config. Paths: `PM_DB_PATH` (default `backend/data/pm.db`), `PM_STATIC_DIR` (default `frontend/out`). Model: `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_TEMPERATURE`.

**Auth.** `POST /api/login` checks the credentials on the server (`PM_LOGIN_USER` / `PM_LOGIN_PASSWORD`, default `user` / `password`) and sets a signed, HTTP-only, SameSite=Lax session cookie (`pm_session`, 7 days). Every other `/api` route needs it (401 otherwise); the `X-User` header is no longer read. Set `PM_SESSION_SECRET` (a Fly secret in production) so sessions survive restarts; without it a random key is made per process. The user and a seeded board are created on first use. Every query is scoped by that user's board. Limits: `/api/login` 10 per minute per client, `/api/chat` 20 per minute per user, chat message 4000 characters, history 20 items.

**AI chat flow (`/api/chat`):** load the user's board, send board JSON + history + message to the model, parse the reply as structured JSON (`reply` + `actions`; may be wrapped in prose), apply actions (`create_card`, `update_card`, `move_card`, `delete_card`) when `apply_updates` is true, and return the reply plus the refreshed board. Unparseable or schema-invalid model output returns 502; a missing API key returns 500. Schemas are documented in `docs/ai-structured-output.json` and `docs/kanban-schema.json`.

**Frontend (`frontend/src/`):**
- `app/page.tsx` - login gate and board page.
- `components/KanbanBoard.tsx` - board state owner, drag-and-drop handling, optimistic updates, background re-fetch after drop/add/delete (the full-screen loading view appears only on the initial load). `ChatSidebar.tsx` - AI chat UI.
- `lib/api.ts` - API client (30s timeout, cookie session, `ApiError` carries the server's `detail`, a 401 anywhere returns the user to the login screen). `lib/kanban.ts` - types and ID helpers.

**ID prefixing:** the frontend prefixes backend numeric IDs with `col-` and `card-` for drag-and-drop stability and strips them before API calls (`toCardId`/`toColumnId` in `lib/kanban.ts`).

**Deployment:** Fly.io app `kanban-studio` (`fly.toml`), with a volume at `/data` and `PM_DB_PATH=/data/pm.db`. `docker-entrypoint.sh` chowns `/data`, then drops to the unprivileged `appuser`. `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are Fly secrets, not in the repo.

## Local environment notes

- The local `.env` may set `OPENROUTER_MODEL` to a free model because the account has no credits for `openai/gpt-oss-120b`. Free models can return 429 upstream. Remove that line to use the default.
- Docker builds download npm/pip packages; a flaky connection can fail `npm ci` (ECONNRESET). Re-run once the network is stable.

## Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)
- Dark Navy: `#032147` (headings)
- Gray Text: `#888888`

The UI was later restyled to a light look with one blue accent; see `DESIGN.md` and `PRODUCT.md` before changing visuals.

## Development Guidelines

- Keep it simple. No over-engineering or unnecessary defensive programming.
- No emojis anywhere (code, docs, UI).
- Identify root cause before fixing issues. Prove with evidence, then fix.
- Work incrementally with small steps. Validate each increment.
- Use latest library APIs.
- Use `uv` as Python package manager in Docker.
- Do not add a Co-Authored-By trailer or other attribution lines to commits or PRs (user preference).
- Planning docs are in `docs/` - review `docs/PLAN.md` for context, including its "Known follow-ups". Per-area notes are in `backend/AGENTS.md`, `frontend/AGENTS.md`, `scripts/AGENTS.md`.

## DETAILED PLAN

@docs/PLAN.md
