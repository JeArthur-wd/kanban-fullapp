# Code review

Date: 2026-10-20. Branch `main` at `302c8e5`, plus the deleted working-tree file noted below.

This review replaces the one dated 2026-10-14, which had been deleted from the working tree
(it is still in history: `git show HEAD:docs/code_review.md`). All High and Medium findings of
that review were fixed before this one; nothing below repeats them.

## How this was done

- Read all of `backend/app`, `frontend/src`, both test suites, the scripts, Dockerfile, and the docs.
- Ran the backend and frontend test suites, lint, typecheck and a production build.
- Ran the Playwright suite 7 times against a local `uvicorn` process with a throwaway database
  (Docker Desktop was not running, so the container itself was not exercised).
- Findings marked Verified were reproduced by running them in this session. Findings marked
  From code come from reading only.

## Test status (2026-10-20)

| Suite | Result |
| --- | --- |
| Backend pytest | 71 passed, 6 skipped (live tests), 98% coverage |
| Frontend vitest | 29 passed |
| eslint, tsc --noEmit, next build | clean |
| Playwright, 7 full runs | 3 runs 10/10, 4 runs with 2-3 failures (see M1, M2, L3) |

## Findings

### H1 - Concurrent requests fail with 500 on the board endpoint (Verified)

Two `GET /api/board` requests 500'd during a Playwright run:

```
sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread.
The object was created in thread id 13644 and this is thread id 16040.
```

Reproduced with a controlled burst of 200 concurrent `GET /api/board` calls after one login:

```
concurrent results: {200: 126, 500: 74}      # 37% failed
sequential baseline: 200                      # always fine
```

Root cause: `connect_db()` (`backend/app/database.py`) creates the connection in whichever thread
runs the dependency body, while FastAPI runs the sync endpoint, and the dependency's exit, through
separate `anyio` threadpool calls. `sqlite3.connect()` defaults to `check_same_thread=True`, so any
time the pool hands the endpoint (or `conn.close()` in `backend/app/dependencies.py`) a different
thread than the one that opened the connection, the request raises. Sequential requests usually
reuse the same thread and pass, which is why the test suites, and most E2E runs, never noticed.

Impact: any two overlapping requests can 500, for example a board refresh while the AI chat is
answering, or two browser tabs. The frontend shows its "Unable to load the board" state.

Suggested fix: pass `check_same_thread=False` to `sqlite3.connect()` (safe here: one connection per
request, used sequentially), and add a regression test that fires concurrent requests - none of the
current tests are concurrent, which is why the suite is 98% covered and still missed this.

### M1 - The login rate limit can be bypassed with a header the client controls (Verified)

`backend/app/routes/auth.py` keys the login limiter on `_client_key(request)`, which prefers the
`Fly-Client-IP` header. Locally, and in the Docker container this MVP targets, there is no proxy
that sets that header, so the client chooses its own key.

Evidence: 14 login attempts with rotating `Fly-Client-IP` values all returned 401, never 429; the
same client without the header got 429 on attempt 11.

Two consequences, one fix each:
- Brute-force protection is defeatable by anyone who can send a header.
- `RateLimiter._hits` (`backend/app/ratelimit.py`) is a `defaultdict` that never drops keys, so each
  invented key leaves an entry behind. This is attacker-controlled growth.

Suggested fix: only trust the header when the app is actually behind Fly (an env flag), and prune
keys whose deque has emptied.

### M2 - The Playwright suite fails when runs are close together (Verified)

Only 3 of 7 full runs were clean, and the failing runs were consecutive ones. Cause: the suite logs
in once per test while `LOGIN_RATE_LIMIT` is 10 per minute per server process, so the tail of a
second run inside the same minute gets 429. Confirmed twice - error context said
"Too many sign-in attempts. Try again in a minute.", and the server log shows the 429s. A single
run against a fresh server passed 10/10.

Suggested fix: raise the limit for the test server, or have the suite sign in once and reuse the
session (Playwright `storageState`).

### L1 - Unknown `/api` paths return 200 with HTML (Verified)

`GET /api/does-not-exist` returns 200 `text/html` (the SPA index). The catch-all in
`backend/app/routes/static.py` treats everything as a frontend route. A client that mistypes a path
gets HTML with a success status instead of a 404; the server log even shows a local poller asking
for `/v1/models` and being told 200. Suggested fix: return 404 JSON for unknown paths under `/api`.

### L2 - Card editing is missing and untested (From code)

AGENTS.md requires cards to be "moved with drag and drop, and edited". The frontend can create,
drag, and delete cards, but there is no edit affordance: `KanbanCard.tsx` renders title/details plus
a delete button only, and the only `updateCard(` call site is the drag handler in
`page.tsx:231`. The backend supports it (`PATCH /api/cards/{id}` with title/details), and
`frontend/AGENTS.md` lists "card editing" as a flow E2E should cover, so this looks like an
unfinished item rather than a deliberate cut.

### L3 - The keyboard drag test failed once and was not diagnosed (Verified, not reproduced)

On the first run, "moves a card with the keyboard" failed: the card landed in the next column
instead of one slot down; the error snapshot showed "E2E first" sitting in In Progress. It passed
in six later attempts. Worth watching, but it may also have been a symptom of H1, since that test
re-reads the board over HTTP. The remaining failures in the back-to-back runs were not individually
diagnosed.

### L4 - Stale and wrong documentation

- `frontend/AGENTS.md` still says the frontend "is a standalone demo that uses in-memory state
  only", and describes `KanbanBoard` as owning board state. Neither is true.
- `scripts/AGENTS.md` is a one-line placeholder ("This folder will contain start and stop
  scripts...") although the scripts exist.
- `docs/PLAN.md:153-154` says backend tests need the repo root on `PYTHONPATH`. That fails with
  `ModuleNotFoundError: No module named 'app'`; it needs `backend` on the path. Its test counts
  (23 tests, 91%) and its Part 1 "(current)" label are also out of date.

### L5 - `test-results` is tracked in git

`frontend/test-results/.last-run.json` is committed and rewritten by every Playwright run, so the
tree is dirty after testing. `git rm --cached` it and ignore the directory.

### L6 - Carried over from the previous review

- Python requirements are ranges, not pins, and there is no CI.
- New cards are stored with the placeholder `"No details yet."` when details are left empty.
- No test covers "no loading screen on a background refresh".
- `page.tsx` (397 lines) is still the largest file in the frontend.

## Done well

- Backend suite is thorough (71 tests, 98% coverage) including path traversal and access-control
  cases, and the six live tests skip cleanly when no server is up.
- All SQL uses parameters; the session cookie is signed, HttpOnly and compared with
  `secrets.compare_digest`.
- Board mutations live in one module (`board_ops.py`) shared by REST and the AI actions, so both
  paths get the same validation and ordering rules.
- The AI action layer rejects unknown or invalid actions per action instead of failing the batch,
  and the frontend drops stale refresh responses (`refreshSeq`).
- Docker image runs as non-root with a healthcheck, and `.env` is not committed.
- E2E tests clean up after themselves and prefix their fixtures (`E2E ...`).
