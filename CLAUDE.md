# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Project Management MVP web app with a Kanban board and AI chat assistant. Users sign in, view/manage a Kanban board with drag-and-drop, and interact with an AI that can create/edit/move/delete cards.

**Stack:** Next.js 16 frontend (React 19, TypeScript, Tailwind v4, @dnd-kit), statically exported and served by a Python FastAPI backend, SQLite database, all packaged in one Docker image. AI via OpenRouter (default model `openai/gpt-oss-120b`).

**MVP constraints:** Hardcoded login (`user`/`password`), one board per user, fixed (renamable) columns. The DB schema supports multiple users.

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
- `main.py` - FastAPI app, lifespan (`init_db()`), `/health`, `/api/hello`, mounts `_next` and `static` from the exported frontend, includes the routers.
- `routes/board.py` - `GET /api/board`, plus POST/PATCH/DELETE for `/api/columns` and `/api/cards`. `routes/chat.py` - `POST /api/chat`. `routes/static.py` - serves the exported frontend at `/` with a catch-all fallback (registered last).
- `database.py` - raw `sqlite3` (no ORM): schema, seeding (`config.INITIAL_COLUMNS`), `fetch_board`, and `resequence_positions` for ordering. `dependencies.py` - `get_db` (per-request connection) and `get_username`.
- `ai.py` - OpenRouter call, prompt building, parsing, and `apply_actions`. `models.py` - Pydantic request/response and action models.
- `config.py` - env config. Paths: `PM_DB_PATH` (default `backend/data/pm.db`), `PM_STATIC_DIR` (default `frontend/out`). Model: `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_TEMPERATURE`.

**Identity is not real auth.** The frontend login is client-side only; the backend identifies the user from an `X-User` header (default `user`) and creates the user and a seeded board on first use. Every query is scoped by that user's board.

**AI chat flow (`/api/chat`):** load the user's board, send board JSON + history + message to the model, parse the reply as structured JSON (`reply` + `actions`; may be wrapped in prose), apply actions (`create_card`, `update_card`, `move_card`, `delete_card`) when `apply_updates` is true, and return the reply plus the refreshed board. Unparseable or schema-invalid model output returns 502; a missing API key returns 500. Schemas are documented in `docs/ai-structured-output.json` and `docs/kanban-schema.json`.

**Frontend (`frontend/src/`):**
- `app/page.tsx` - login gate and board page.
- `components/KanbanBoard.tsx` - board state owner, drag-and-drop handling, optimistic updates, background re-fetch after drop/add/delete (the full-screen loading view appears only on the initial load). `ChatSidebar.tsx` - AI chat UI.
- `lib/api.ts` - API client (30s timeout, sets `X-User`). `lib/kanban.ts` - types and ID helpers.

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
