# Code review

Date: 2026-10-14. Scope: the whole repo (backend, frontend, Docker/Fly config, tests, docs). Branch `main`, working tree as of this review.

## How this was done

- Read every source file in `backend/app`, `frontend/src`, the tests, `Dockerfile`, `docker-entrypoint.sh`, `fly.toml`, the start/stop scripts and the docs.
- Ran the full test suite against a freshly built container (see "Test status").
- Ran a second pass to hunt for false positives. Each claim was re-checked by running it: backend claims against a real uvicorn process and the built Docker image (with a dummy API key and a temporary database), frontend claims with throwaway Vitest tests that were deleted afterwards. Findings marked **Verified** were reproduced that way. Findings marked **From code** come from reading the code only and were not run.
- The live Fly.io deployment was not probed.
- The second pass found one wrong claim in the first draft (the error toast in M2) and one missing finding (M10). Both are corrected below.

## Test status

| Suite | Result |
|---|---|
| Backend pytest (incl. live container tests) | 26 passed, 91% coverage |
| Frontend ESLint | clean |
| Frontend Vitest | 12 passed, 75.9% statement coverage |
| Playwright e2e (3 tests) against the container | 3 passed |

Two fixes were needed to get green, both uncommitted:

- `backend/tests/test_integration.py`: `test_live_root` still asserted the old title "Project Management"; the restyle made it "Kanban Studio".
- `frontend/vitest.config.ts`: added `testTimeout: 20000`. The "adds and removes a card" test needs about 6.7s on this machine and failed at the 5s default. It passes with a longer timeout, so it was not a bug.

Green tests do not mean the app is correct. Several real bugs below are not covered by any test.

## Summary

The structure is sound: parameterized SQL throughout, every query scoped to the signed-in user's board, a validated discriminated-union schema for AI actions, a multi-stage non-root Docker image, and good backend coverage. The problems are concentrated in three places:

1. The public deployment has no real access control, and one route can read files outside the static directory.
2. Card ordering logic is copied into four places, and the copies are wrong for same-column moves.
3. Several frontend error paths leave the user stuck or discard their input.

## Resolution status (added after the fixes)

All High and Medium findings were fixed. Low items were not part of this round.

| Finding | Status | How it was fixed |
|---|---|---|
| H1 path traversal | Fixed | `static_fallback` resolves the path and returns 404 outside the static root. Tests fail on the old code. |
| H2 no access control | Fixed | Server-side `POST /api/login`, signed HTTP-only SameSite=Lax cookie, 401 on every other `/api` route, `X-User` ignored. Chat: 4000-character message, 20-item history, 20 requests per minute. Login: 10 attempts per minute. |
| H3 same-column move | Fixed | `move_card` in `backend/app/board_ops.py` removes the card before inserting. Tests fail on the old code. |
| H4 dependencies | Fixed | `next` 16.4.0 and `npm audit fix`. `npm audit --omit=dev` reports 0 vulnerabilities. The `next` advisories concern the Next server, which does not run here (static export), so the real exposure was low. 9 dev-only advisories remain (Vitest's `tinypool` and similar); they need a Vitest major upgrade. |
| M1 endless spinner | Fixed | Error message and a "Try again" button. |
| M2 column titles | Fixed | Saved once on blur or Enter; empty title reverts; Escape cancels. |
| M3 AI actions | Fixed | Bad ids and invalid fields are skipped; the response has a `skipped` list and the reply says what was not applied. |
| M4 SQLite | Fixed, with one correction | Foreign keys on, WAL, upserts, seeding at board creation. Correction to the report: Python's `sqlite3.connect` already has a 5 second default timeout, so "no busy_timeout" was overstated; it is now explicit at 10 seconds. Migrations are documented as not implemented (`docs/DB_MODEL.md`). |
| M5 duplicated ordering code | Fixed | Single module `board_ops.py`. |
| M6 stale refresh, impure updater | Fixed | Sequence counter drops older responses. Drag-end computes the new order outside the updater and skips no-op drops. |
| M7 upstream errors | Fixed | 429 passes through with a retry message, 401/402/403 give a key/credits message, timeouts give 504, a non-JSON body gives 502. The chat shows the server's message. |
| M8 prompt and history | Fixed | Board sent once, failure notices not sent back, history capped on both sides. |
| M9 keyboard | Fixed | `KeyboardSensor`, covered by a Playwright test. |
| M10 swallowed errors | Fixed | Error is set after the refresh; auto-dismisses after 6 seconds. |

Not done: the Low items, except where a fix was a side effect. Side effects: the dead `database.get_db` was removed, tests no longer leak `PM_DB_PATH` (each test gets its own temporary database), the Playwright tests now clean up the cards they create, and the docs for auth, the database and the module layout were updated. Still open: untracking `frontend/test-results`, pinning and splitting the Python requirements, CI, `frontend/AGENTS.md` and `scripts/AGENTS.md` being stale, splitting `page.tsx`, and the "No details yet." placeholder stored as card content.

Module layout (follow-up request): `main.py` was already small (an app factory is now all it holds). `ai.py` is now the `app/ai/` package and `models.py` the `app/models/` package, with the public import paths unchanged.

Deployment: the live site at https://kanban-studio.fly.dev still runs the old code, including H1 and H2, until it is redeployed. Set `PM_SESSION_SECRET` and a new `PM_LOGIN_PASSWORD` as Fly secrets first.

The sections below are the original findings, unchanged.

## High severity

### H1. Path traversal in the static file fallback (Verified)

`backend/app/routes/static.py:42-60`. `static_fallback` builds `STATIC_DIR / full_path` and serves it if it exists, with no check that the result is inside `STATIC_DIR`.

Evidence 1 (real uvicorn on Windows, raw request paths, temporary files):

```
GET /%2e%2e/SECRET.txt      -> 200 "TOP-SECRET-OUTSIDE-STATIC-DIR"
GET /..%2fSECRET.txt        -> 200 "TOP-SECRET-OUTSIDE-STATIC-DIR"
GET /C:/.../abs_secret.txt  -> 200 "TOP-SECRET-ABSOLUTE"   (absolute path replaces the base)
```

Evidence 2 (the built Linux Docker image, run locally with a dummy API key, `curl --path-as-is`):

```
GET /%2e%2e/%2e%2e/%2e%2e/etc/passwd      -> 200, 882 bytes, "root:x:0:0:..."
GET /%2e%2e/%2e%2e/backend/app/main.py    -> 200, application source
GET /%2e%2e/%2e%2e/backend/data/pm.db     -> 200, 40960 bytes, "SQLite format 3"
GET //etc/passwd                          -> 200, 882 bytes (absolute path replaces the base)
GET /../../../etc/passwd                  -> 200, 882 bytes
GET /%2e%2e/%2e%2e/%2e%2e/proc/self/environ -> 200, 0 bytes
```

So anyone can download files outside `/app/frontend/out`, including the application source and the SQLite file, which holds every user's boards. On Fly the database is at `/data/pm.db`; I tested the local default path, which is the same mechanism. `/proc/self/environ` came back empty (zero length), so the API key was not exposed through that file. I did not try other `/proc` files.

Action:
- Resolve the path and reject anything not inside the static root: `p = (STATIC_DIR / full_path).resolve(); if not p.is_relative_to(STATIC_DIR.resolve()): 404`.
- Or drop the hand-written catch-all and mount `StaticFiles(directory=STATIC_DIR, html=True)` after the API routers.
- Add a test that requests `/%2e%2e/` and an absolute path and expects 404.
- Redeploy to Fly as soon as it is fixed.

### H2. No real access control on a public deployment (Verified locally)

`backend/app/dependencies.py:17-18`, `frontend/src/app/page.tsx:25,69`. Login is a client-side string comparison. The backend trusts an `X-User` header (default `user`) and creates that user on first use. Consequences on https://kanban-studio.fly.dev:

- Anyone can read, edit or delete any user's board by sending the header, without signing in. Verified: `GET /api/board` with `X-User: someone-else` returns 200 and a freshly seeded board.
- `POST /api/chat` is unauthenticated and calls OpenRouter with the owner's key. `ChatRequest.message` and `history[].content` have no length limit, and there is no rate limit. Verified: a 2 MB message plus 20 history items of 500 KB each is accepted with 200 (the OpenRouter call was mocked in this test, so no credits were spent). Anyone could spend the credits; I did not test the live site.

The plan accepts a hardcoded login for the MVP. That was written for local Docker; the Fly deployment changes the risk.

Action (smallest useful step):
- Add `POST /api/login` that checks `user`/`password` on the server and sets a signed, HTTP-only session cookie. Make `get_username` read the session instead of the header.
- Add `max_length` to `ChatRequest.message`, cap the number of history items, and add a simple per-IP or per-session rate limit on `/api/chat`.
- If a real login is out of scope, at least cap message length and rate-limit chat.

### H3. Moving a card down within its own column lands in the wrong place (Verified)

Same logic in `backend/app/routes/board.py:212-240` (`update_card`) and `backend/app/ai.py:216-244` (`move_card` action). The target list is loaded from the database while the card is still in it, then the card is inserted again. The id appears twice, so every card after it is shifted by one.

Evidence: column `[A, B, Third]`, `PATCH /api/cards/{A}` with the same `column_id` and `position: 2` (what the frontend sends for a drop at the bottom) gives `[B, A, Third]`. Expected `[B, Third, A]`. Moving up works by accident.

Impact: reordering within a column is the core drag-and-drop gesture. After a drop the board is re-fetched, so the card snaps to the wrong place. The AI `move_card` action has the same bug. No test covers it; the Playwright move test is cross-column only.

Action: remove the card from the target list when source and target are the same column before inserting. Better, fix it once in a shared helper (see M5). Add unit tests for same-column moves in both directions and a Playwright test that reorders within a column.

### H4. Production dependencies with known advisories (From `npm audit`, not triaged)

`npm audit --omit=dev` reports 6 vulnerabilities: 1 critical (`next`), 4 high (`nanoid`, `next`'s nested `postcss`, `sharp`, `source-map-js`) and 1 moderate (`baseline-browser-mapping`). I did not read the individual advisories, so I do not know which apply to a statically exported site served by FastAPI. Several are likely build-time only.

Action: run `npm audit` and read the `next` advisory first; move to the patched `next` 16.x release if there is one. Re-run `npm audit fix` and the tests. Pin Python dependencies and run `pip-audit` too (see L3).

## Medium severity

### M1. Initial board load failure shows an endless spinner (Verified)

`frontend/src/app/page.tsx:282-302`. When `board` is null the page always renders "Loading your board". `boardError` is only rendered in the main view (`:324`), which needs a board. If the first `GET /api/board` fails (server error, 30s timeout on a cold Fly start, network), the user sees the spinner forever with no message and no retry.

Verified with a Vitest test: with `fetch` rejecting, after signing in the page still shows "Loading your board", with no alert and no retry button.

Action: render `boardError` with a Retry button in the `!board` branch.

### M2. Editing a column title sends a request per keystroke and cannot be cleared (Verified)

`frontend/src/components/KanbanColumn.tsx:58` calls `onRename` on every `onChange`, and `page.tsx:94-107` sends a PATCH each time. Problems:

- One request per character, with no ordering guarantee between them. Verified: typing "Hi" into the "Backlog" title sent `{"title":"BacklogH"}` and `{"title":"BacklogHi"}`.
- Clearing the title sends `{"title":""}` (verified). The server rejects it with 422 (verified, `ColumnUpdate` has `min_length=1`). The page then re-fetches the board and the old title ("Backlog") reappears in the input while the user is typing (verified).
- The first draft of this report also said the user sees "Unable to save column changes." That was wrong: no message appears. See M10 for why.

Action: keep the title in local state and save on blur or Enter (or debounce). Do not send an empty title; revert it locally instead.

### M3. AI action handling is brittle and can mislead the user (Verified)

`backend/app/ai.py:134-266`. Each of these was run through `POST /api/chat` with the model call mocked:

- A non-numeric id from the model (`columnId: "Backlog"`) raises `ValueError` from `int(...)`. The response is 500, not the 502 used for other bad model output.
- A `delete_card` action for a card that does not exist is skipped silently with `continue`. The response is 200, the model's reply still reads "Deleted the card.", and the action is echoed back as if it ran, so the board and the message disagree.
- An `update_card` action with `title: ""` is accepted and the card ends up with an empty title. The action models have none of the length or minimum limits the REST models have (`models.py`).
- Nothing in the response says which actions were applied and which were skipped.

Action: validate ids when parsing (use `int` fields or a validator), reuse the REST `CardCreate`/`CardUpdate` constraints, and have `apply_actions` return the applied/skipped list so the chat response can say what actually happened.

### M4. SQLite setup is minimal (Partly verified)

`backend/app/database.py`.

- Verified: `PRAGMA foreign_keys` is 0. The `FOREIGN KEY` clauses in the schema are not enforced, and column delete cascades by hand (`board.py:115`).
- From code, not run: no WAL mode or `busy_timeout`, so concurrent writers could hit "database is locked".
- From code, not run: `get_or_create_user` has a check-then-insert race; two first requests for the same new user could raise `IntegrityError` (500).
- Verified: `fetch_board` writes (`ensure_seed_data`) on a GET. After deleting all 5 columns, the next `GET /api/board` returned 5 columns again. Also verified: `POST /api/cards` for a brand-new user before any GET returns 404 "Column not found".
- `docs/DB_MODEL.md` promises forward-only migrations using `PRAGMA user_version`. Nothing implements them; the schema is only `CREATE TABLE IF NOT EXISTS`.

Action: enable `PRAGMA foreign_keys=ON` in `connect_db` (with `ON DELETE CASCADE`), set WAL and a busy timeout, use `INSERT ... ON CONFLICT DO NOTHING` for users, and decide whether to implement the migration plan or edit the doc. Move seeding to user creation.

### M5. The same ordering code is written four times (From code; the cause of H3)

Clamp-the-insert-position, load-ordered-ids, insert, resequence appears in `board.py` (`create_column`, `create_card`, `update_card`) and `ai.py` (`create_card`, `move_card`). The "find a card that belongs to this board" query appears four times as well. The H3 bug exists because the same-column case was written twice and wrong both times.

Action: a small module (for example `backend/app/cards.py`) with `create_card`, `move_card`, `update_card`, `delete_card`, each taking `conn, board_id` and doing ownership checks. Both the REST routes and `apply_actions` call it. This is the fix that removes H3 for good and shortens `ai.py` and `board.py` considerably.

### M6. Out-of-order board refreshes (From code)

`page.tsx` calls `refreshBoard()` after every add, delete and move. Two quick actions start two fetches; whichever response arrives last wins, which may be the older snapshot. The existing known follow-up (`handleDragEnd` calls `onMoveCard` inside the `setBoard` updater, `KanbanBoard.tsx:110-117`) also still stands: the updater is impure and may fire twice in Strict Mode.

Action: ignore stale responses (a request counter or an `AbortController` for the previous refresh). Compute `nextColumns` from current state outside the updater, then call `setBoard` and `onMoveCard` separately.

### M7. Upstream AI errors are flattened (Verified)

`ai.py:65-85`. With `httpx.post` mocked: a 429 and a 402 from OpenRouter both reach the client as `502 {"detail": "OpenRouter returned an error"}`, and a 200 response with a non-JSON body gives a 500 because `response.json()` is not guarded. The 402 (no credits) and 429 (rate limit) cases are ones this project has already hit live, and the distinction is lost. The frontend then shows one generic message for everything (`page.tsx:207`).

Action: map 429 to a retryable message, 402/401 to a clear "AI is not configured" message, and show the server's `detail` in the chat error. Guard `response.json()`.

### M8. Prompt and history handling (From code)

- `build_structured_messages` sends the board twice: once as a text summary and once as indented JSON. That is wasted tokens on every call, and slow free models make cost and latency visible.
- The error reply "Something went wrong. Please try again." is added to `chatMessages` (`page.tsx:208-211`) and is then sent back to the model as real assistant history on the next turn.
- History is unbounded and sent in full each time.

Action: drop the summary or the JSON, keep only genuine assistant replies in the history sent to the API, and cap history length.

### M9. Keyboard users cannot move cards (Verified by search)

`KanbanBoard.tsx:49-53` registers only `PointerSensor`, and `KeyboardSensor` appears nowhere in `frontend/src`. `PRODUCT.md` and `DESIGN.md` both ask for keyboard-reachable controls. I did not try dragging with a keyboard in a browser. Add `KeyboardSensor` with `sortableKeyboardCoordinates`, and test it.

### M10. Errors from board actions are never shown to the user (Verified; new in the second pass)

`frontend/src/app/page.tsx`: the rename, add, delete and move handlers all do `setBoardError("...")` and then call `refreshBoard()` in their `catch`. `refreshBoard` starts with `setBoardError(null)` (`:41`), so the message is cleared in the same render and never appears. The error toast at `page.tsx:324` can only show for a failed refresh itself.

Verified with Vitest, with the server mocked to fail:
- A failed column rename (422): no `role="alert"` element, and the title silently reverts.
- A failed card delete (500): no `role="alert"` element, and the card silently reappears.

This contradicts the plan item "Handle error states gracefully" (Part 7). The user sees their edit undone with no explanation.

Action: call `refreshBoard()` before `setBoardError(...)`, or stop `refreshBoard` clearing the error unless it succeeds. Add a test for each handler.

## Low severity and hygiene

### L1. Tracked and dead files

- `frontend/test-results/.last-run.json` is tracked in git and changes on every Playwright run. Untrack it and add `test-results/` and `playwright-report/` to `frontend/.gitignore`.
- `database.get_db` (`database.py:78-83`) duplicates `dependencies.get_db` and is unused.
- `/api/hello` and the fallback HTML ("PM MVP") are Part 2 scaffolding. `test_main.py` still tests them.
- `useMemo(() => board.cards, ...)` in `KanbanBoard.tsx:55` does nothing. `_overId` in `handleMoveCard` is unused. `VALID_TABLES` duplicates the `Literal` type next to it.
- `handleLogin` declares a local `username` that shadows the state variable (`page.tsx:66`).

### L2. Data and UX details

- The placeholder "No details yet." is stored in the database as card content (`page.tsx:120`) and is then shown to the AI as real text. Store an empty string and render the placeholder in the UI.
- Refreshing the page logs the user out, because `isAuthenticated` is not persisted. Fine for a demo; worth a line in the README, or fixed by H2's session cookie.
- `page.tsx` is 334 lines and mixes login view, loading view, board view and all the API handlers. Splitting out `LoginForm` and a `useBoard` hook would make it testable.

### L3. Docker and dependencies

- `backend/requirements.txt` has version ranges and no lockfile, and installs `pytest`/`pytest-cov` into the production image. Split into runtime and dev requirements and pin them (`uv pip compile`).
- The container is Python 3.12; the tests here ran on Python 3.13. Pick one and use it in CI.
- `scripts/start-mac.sh` and `start-linux.sh` do not check that `.env` exists (the Windows script does).
- There is no CI. A GitHub Actions workflow that runs lint, Vitest and pytest would have caught the stale `test_live_root` assertion.

### L4. Test quality

- Coverage: backend 91% (`ai.py` 85%, `board.py` 85%). Frontend 75.9% (`page.tsx` 61.8%, `KanbanBoard.tsx` 66.2%, `api.ts` 68.7%, `layout.tsx` 0%). The uncovered frontend lines are mostly the error and move paths, which is where M1, M2 and M6 live.
- `test_board_api.py` sets `os.environ["PM_DB_PATH"]` and never restores it, which leaks into later tests. Use `monkeypatch.setenv`.
- The Playwright tests share one persistent database. "adds a card" leaves a new card on every run, and "moves a card" moves a seed card without moving it back. Use a unique username per test (via the API, once H2 is decided) or reset the database in a fixture.
- Missing tests: same-column reorder (H3), traversal (H1), non-numeric AI ids (M3), empty column title (M2), initial-load failure (M1), error toasts (M10), keyboard drag (M9).

### L5. Docs out of date

- `frontend/AGENTS.md` still describes an in-memory demo and lists two test files.
- `scripts/AGENTS.md` is a placeholder line.
- `docs/PLAN.md` still labels Part 1 "(current)", and its test counts ("23 passed", "91%") are from an earlier run.
- `backend/AGENTS.md` does not mention the `X-User` header, the `PM_DB_PATH`/`PM_STATIC_DIR` settings, or the Fly deployment and entrypoint.

## Done well

- Every SQL statement is parameterized. The one f-string (`resequence_positions`) interpolates a table name checked against a whitelist.
- Ownership is checked with a join on `columns.board_id` for cards, so one user cannot touch another's rows through the API.
- AI output goes through a Pydantic discriminated union, with 502 for unparseable output and tolerance for JSON wrapped in prose.
- Multi-stage Docker build, non-root runtime, healthcheck, and a documented entrypoint that fixes volume ownership.
- Optimistic UI with a background re-fetch and no full-screen flash, as the plan describes.
- Accessible names on controls, reduced-motion handling, and a written design system.

## Action list

Suggested order. Effort: S under an hour, M a few hours, L a day or more.

**Do first (security and data correctness)**
- [ ] H1: constrain static file serving to `STATIC_DIR`, add a regression test, redeploy to Fly. (S)
- [ ] H2: server-side login with a session cookie; length limits and a rate limit on `/api/chat`. (M)
- [ ] H3 + M5: extract shared card/column ordering helpers, fix same-column moves, add tests including a Playwright reorder test. (M)
- [ ] H4: read the `next` advisory, upgrade, re-run `npm audit` and all tests. (S-M)

**Then (user-visible bugs)**
- [ ] M1: show the error and a Retry button when the first board load fails. (S)
- [ ] M2: save column titles on blur or Enter and never send an empty title. (S)
- [ ] M10: make board action errors actually display (set the error after `refreshBoard`, or stop it clearing errors). (S)
- [ ] M3: validate AI action ids and fields, report applied and skipped actions. (M)
- [ ] M6: ignore stale refresh responses and move `onMoveCard` out of the state updater. (S)
- [ ] M7 and M8: map OpenRouter errors to clear messages, send the board once, keep error replies out of history. (S-M)
- [ ] M9: add `KeyboardSensor`. (S)

**Then (robustness and hygiene)**
- [ ] M4: foreign keys on, WAL and busy timeout, upsert for users, seed on user creation, decide on migrations. (M)
- [ ] L1: untrack `test-results`, delete dead code. (S)
- [ ] L3: split and pin Python requirements, add CI. (M)
- [ ] L4: monkeypatch env in tests, make Playwright tests isolated, raise frontend coverage on `page.tsx` and `KanbanBoard.tsx`. (M)
- [ ] L2 and L5: store empty details, split `page.tsx`, refresh the stale docs. (S-M)
- [ ] Commit the two test fixes described under "Test status". (S)
