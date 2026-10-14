# Project plan (detailed)

This plan is the single source of truth for the MVP. Each part includes a checklist, tests, and success criteria. The project should target roughly 80% unit test coverage when it is sensible and adds value, but quality and meaningful coverage come first; we should not add unnecessary tests only to chase a percentage.

## Part 1: Plan (current)

Checklist
- [x] Review root AGENTS.md and existing documentation.
- [x] Enrich this plan with detailed steps, tests, and success criteria.
- [x] Create frontend/AGENTS.md that documents the existing frontend code.
- [x] Get user approval before starting Part 2.

Tests
- None for this step.

Success criteria
- Plan is detailed, actionable, and approved by the user.
- frontend/AGENTS.md accurately reflects current frontend architecture.

## Part 2: Scaffolding (Docker + FastAPI + scripts)

Checklist
- [x] Define Dockerfile and any compose config needed for local containerized development.
- [x] Create backend FastAPI app in backend/ with a health endpoint and a simple API endpoint.
- [x] Serve a minimal static HTML response at / to validate serving.
- [x] Add scripts in scripts/ for start and stop on Mac, PC, Linux.
- [x] Ensure uv is used as the Python package manager inside the container.
- [x] Add minimal README notes for running locally.

Tests
- [x] Backend unit test for health endpoint.
- [x] Integration test that hits / and the example API endpoint in the running container.

Success criteria
- Container starts with a single command and serves both HTML at / and JSON at the API endpoint.
- Start/stop scripts work on Mac, PC, and Linux (PC/Linux not verified; user approved skip).
- Unit coverage for backend modules at or above 80% (verified at 98%).

## Part 3: Add in Frontend (static build served by backend)

Checklist
- [x] Configure frontend build output for static export compatible with FastAPI serving.
- [x] Update backend to serve the built frontend at /.
- [x] Ensure the Kanban board renders correctly at / in the container.

Tests
- [x] Frontend unit tests continue to pass with coverage targets where sensible.
- [x] Integration test to verify / serves the Kanban UI and key elements exist.

Success criteria
- The app loads the existing Kanban demo at / via the backend.
- All unit and integration tests pass; coverage targets are applied where sensible.

## Part 4: Fake user sign-in experience

Checklist
- [x] Add a simple login screen on / when unauthenticated.
- [x] Hardcode credentials to user/password for MVP.
- [x] Add a logout control that returns to the login screen.
- [x] Preserve Kanban data in memory for the session.

Tests
- [x] Unit tests for login form behavior and validation.
- [x] Integration tests for login, viewing Kanban, and logout flows.

Success criteria
- Unauthenticated users see login screen; authenticated users see Kanban.
- Login and logout flows function reliably with tests covering the flow.

## Part 5: Database modeling

Checklist
- [x] Propose SQLite schema for users, boards, columns, cards, and ordering.
- [x] Save schema proposal as JSON in docs/.
- [x] Document rationale and migration approach in docs/.
- [x] Get user sign-off before implementation.

Tests
- [x] Validate schema JSON structure with a simple unit test.

Success criteria
- Schema proposal is clear, normalized, and approved by the user.

## Part 6: Backend API (persistent Kanban)

Checklist
- [x] Create SQLite DB if missing on startup.
- [x] Implement CRUD endpoints for board, columns, and cards.
- [x] Scope all operations to the signed-in user.
- [x] Add request/response validation and error handling.

Tests
- [x] Unit tests for each endpoint handler (coverage targets where sensible).
- [x] Integration tests for create/read/update/delete card and column flows.

Success criteria
- API persists data to SQLite and passes all tests.
- Coverage targets are applied where sensible for backend units.

## Part 7: Frontend + Backend integration

Checklist
- [x] Replace in-memory Kanban data with backend API calls.
- [x] Add optimistic UI where appropriate.
- [x] Handle error states gracefully.
- [x] Align drag-and-drop identifiers with backend numeric ids via client-side prefixing.
- [x] Route Playwright integration tests through the backend-served frontend.

Tests
- [x] Frontend unit tests updated for API-driven data (coverage targets where sensible).
- [x] Integration tests covering UI + API flows end-to-end.

Success criteria
- Kanban data persists across reloads using the backend.
- Full flow passes integration tests reliably.

Design decisions (Part 7)
- Frontend prefixes backend numeric ids for drag-and-drop stability and strips them before API calls.
- Drag-and-drop uses card/column metadata to resolve drop targets across columns.
- Playwright runs against the backend-served static build to reflect production behavior.
- After a drop, card add or card delete, the page re-fetches the board as a background refresh. The full-screen "Loading your board" view is shown only on the initial load (no board yet), so the board is not unmounted and rebuilt after every action. The `isLoading` state was removed.

## Part 8: AI connectivity (OpenRouter)

Checklist
- [x] Add backend client that calls OpenRouter with model openai/gpt-oss-120b.
- [x] Read OPENROUTER_API_KEY from .env.
- [x] Implement a simple /api/chat endpoint to verify AI connectivity.
- [x] Hardcode OpenRouter base URL for now.

Notes (Part 8 decisions)
- Use /api/chat for the connectivity endpoint.
- Run a live call to OpenRouter for testing (no mocking).
- Keep the OpenRouter base URL hardcoded.
- Reconfirmed with the user: the check goes all the way to OpenRouter (no mocking) and must get a real answer from the model; `/api/chat` is the endpoint; hardcoded base URL is fine for now.
- Verified live (2026-10-13): the first key was expired (401), and the replacement account had no credits (402) for `openai/gpt-oss-120b`. At the user's request the local `.env` now sets `OPENROUTER_MODEL=nvidia/nemotron-3-super-120b-a12b:free` (read in `config.py`; the code default is still `openai/gpt-oss-120b`). `/api/chat` returned "4" for the 2+2 prompt and `test_live_chat_openrouter` passed.
- Free models can be rate-limited upstream (429); `google/gemma-4-26b-a4b-it:free` was when tried. Remove the `OPENROUTER_MODEL` line from `.env` to go back to `openai/gpt-oss-120b` once the account has credits.

Tests
- [x] Unit test that returns 500 when OPENROUTER_API_KEY is missing.
- [x] Integration test that validates the "2+2" response path via live OpenRouter (skipped if env is missing).

Success criteria
- OpenRouter connectivity verified with a live response and guarded with tests.

Testing notes (added after Part 8)
- For live integration/E2E tests, start the container in detached mode so the terminal can run tests:
	- docker build -t pm-app .
	- docker rm -f pm-app || true
	- docker run -d --name pm-app --env-file .env -p 8000:8000 pm-app
- Wait for readiness via /health before tests:
	- curl -sf http://127.0.0.1:8000/health
- Backend tests require repo root on PYTHONPATH:
	- PM_BASE_URL=http://127.0.0.1:8000 PYTHONPATH=/absolute/path/to/repo pytest backend
- Frontend tests:
	- npm run test:all (runs unit + Playwright). Playwright uses the backend-served app at 8000.
- Stop the container when done:
	- ./scripts/stop-mac.sh (or platform equivalent)
- Docker Desktop must be running first (on Windows, start it before the start script).
- Builds download npm/pip packages, so a flaky connection can fail `npm ci` (ECONNRESET) or DNS lookups; re-run once the network is stable.

## Part 9: AI structured outputs for Kanban updates

Checklist
- [x] Define Structured Output schema for chat responses and optional board updates.
- [x] Send current Kanban JSON + conversation history to the model.
- [x] Apply model updates to persisted board data.

Tests
- [x] Unit tests for schema validation and update application.
- [x] Integration tests for end-to-end AI update flow (mocked).

Success criteria
- Structured outputs reliably update the Kanban without errors.
- Tests demonstrate correct parsing and persistence.

Notes (Part 9 review)
- Schema-invalid model output (e.g. unknown action type) raised an unhandled pydantic `ValidationError` and returned 500. `parse_structured_output` now returns 502, matching the other bad-model-output cases.
- Added tests for JSON wrapped in prose, non-JSON output and schema-invalid output (backend: 23 passed, 3 live tests skipped, 91% coverage).
- Verified against the live free model: "add a card" via `/api/chat` returned valid structured JSON (a `create_card` action), the card was persisted and returned in `board`. The test card was deleted afterwards.

## Part 10: AI chat sidebar UI

Checklist
- [x] Build sidebar chat UI aligned to the color scheme.
- [x] Display conversation history and AI responses.
- [x] Apply AI-driven Kanban updates and refresh the UI.

Tests
- [x] Unit tests for chat UI components (coverage targets where sensible).
- [x] Integration tests for chat flow including AI-triggered Kanban updates (mocked).

Success criteria
- Sidebar chat is responsive, clear, and stable.
- AI-driven Kanban updates reflect immediately in the UI.

## After Part 10: setup, repo and polish

Done
- [x] `scripts/start-windows.ps1` stops with a clear error if `.env` is missing or `docker build` fails (previously it continued to `docker run`). The Mac and Linux scripts were not changed.
- [x] Added `.env.example` (`OPENROUTER_API_KEY=`) and a README "Setup" section. `.env` stays gitignored and is required by the start scripts; the app runs with a dummy key but AI chat returns an error.
- [x] Fixed the full-board flash after drag-and-drop (see Part 7 design decisions).

- [x] Restyled the whole UI to a clean, light "category standard" look (one blue accent, Geist type, muted per-column status dots, drawn SVG icons, slim top bar, thinking state in the chat). Look and feel only; behavior, data and API unchanged. Product and design records are in `PRODUCT.md` and `DESIGN.md`.
- [x] Deployed to Fly.io: https://kanban-studio.fly.dev (app `kanban-studio`, region iad, one shared-cpu-1x 512 MB machine that stops when idle, 1 GB volume `pm_data` at `/data`, `PM_DB_PATH=/data/pm.db`). Secrets `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are set on Fly, not in the repo. Verified live: `/health`, sign-in, board data, a real assistant reply, and data surviving a machine restart.
- [x] Added `docker-entrypoint.sh`: a Fly volume mounts owned by root, so the container now chowns `/data` and then drops to the unprivileged `appuser` (checked locally with a root-owned volume).

Decisions
- The project lives in its own repo, `JeArthur-wd/kanban-fullapp` (`main`). The original remote was renamed `upstream` (ed-donner/pm).
- The existing GitHub Pages site (jearthur-wd.github.io/kanban) is a separate, frontend-only repo and is left untouched. Pages cannot run the FastAPI backend or SQLite, and the static export is built for `/` rather than `/kanban/`.
- Commits carry no Co-Authored-By trailer (user preference).

Known follow-ups
- Not built (scope was look and feel only, awaiting a decision): highlight of cards the assistant just changed, clickable example prompts in the empty chat, and reworded login copy (currently "explore the MVP").
- `handleDragEnd` in `KanbanBoard.tsx` calls `onMoveCard` inside the `setBoard` updater. Updaters should be pure and may run twice in React Strict Mode (dev), sending a duplicate move request. Harmless today because the move is idempotent, but worth moving out of the updater.
- No unit test covers the "no loading screen on background refresh" behavior.