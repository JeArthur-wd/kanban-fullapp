# Project Management MVP

## Setup

Copy `.env.example` to `.env` in the repo root and set `OPENROUTER_API_KEY`. The start scripts require this file. Without a valid key the app runs, but AI chat returns an error.

## Accounts

Anyone can create an account on the sign-in screen (set `PM_ALLOW_SIGNUP=false` to turn that off). Passwords are stored as scrypt hashes and the session is kept in a signed cookie. Each account can have any number of boards.

A demo account, `user` / `password`, is created at startup; set `PM_LOGIN_USER` and `PM_LOGIN_PASSWORD` to change it. That password is only applied while the account has none, so a password changed in the app is kept. Set `PM_SESSION_SECRET` to a long random string so sessions survive a restart (on Fly: `fly secrets set PM_SESSION_SECRET=...`). Without it, everyone is signed out whenever the server restarts.

The database schema is upgraded automatically at startup (`PRAGMA user_version`); existing boards and cards are kept.

## Local run (Docker)

- Mac: scripts/start-mac.sh
- Linux: scripts/start-linux.sh
- Windows: scripts/start-windows.ps1

The backend will be available at http://localhost:8000

## Stop container

- Mac: scripts/stop-mac.sh
- Linux: scripts/stop-linux.sh
- Windows: scripts/stop-windows.ps1

## Tests

- Backend: `cd backend && pytest`. Live tests need a running server: `PM_BASE_URL=http://localhost:8000 pytest tests/test_integration.py`.
- Frontend: `cd frontend && npm run test:unit`, and `npm run test:e2e` against a server on port 8000 (Playwright starts the Docker app if nothing is running there).

## CI

`.github/workflows/ci.yml` runs on every pull request and push to `main`: backend tests, frontend lint/typecheck/unit tests/build, then the Docker image is built and the live backend tests and Playwright run against it. On pushes to `main` it can also deploy to Fly: set the repository secret `FLY_API_TOKEN` (`fly tokens create deploy`) and the repository variable `FLY_DEPLOY=true`. Deploys stay off until then.

## Deploy (Fly.io)

Live at https://kanban-studio.fly.dev. Config is in `fly.toml`; the SQLite file lives on a 1 GB volume mounted at `/data`.

1. Install `flyctl` and run `fly auth login`.
2. `fly apps create <name>` and `fly volumes create pm_data --region iad --size 1`.
3. Set secrets: `fly secrets set OPENROUTER_API_KEY=... OPENROUTER_MODEL=... PM_SESSION_SECRET=... PM_LOGIN_PASSWORD=...`. The default password is public in this repo, so change it for a public deployment.
4. `fly deploy --ha=false`.

The container starts as root only to give the mounted volume to the app user, then runs as that user (`docker-entrypoint.sh`).
