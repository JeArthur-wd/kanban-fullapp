# Project Management MVP

## Setup

Copy `.env.example` to `.env` in the repo root and set `OPENROUTER_API_KEY`. The start scripts require this file. Without a valid key the app runs, but AI chat returns an error.

## Signing in

The login is checked on the server and kept in a signed cookie. The default account is `user` / `password`; set `PM_LOGIN_USER` and `PM_LOGIN_PASSWORD` to change it. Set `PM_SESSION_SECRET` to a long random string so sessions survive a restart (on Fly: `fly secrets set PM_SESSION_SECRET=...`). Without it, everyone is signed out whenever the server restarts.

## Local run (Docker)

- Mac: scripts/start-mac.sh
- Linux: scripts/start-linux.sh
- Windows: scripts/start-windows.ps1

The backend will be available at http://localhost:8000

## Stop container

- Mac: scripts/stop-mac.sh
- Linux: scripts/stop-linux.sh
- Windows: scripts/stop-windows.ps1

## Integration tests

Set PM_BASE_URL to the running backend URL (for example http://localhost:8000) before running integration tests.

## Deploy (Fly.io)

Live at https://kanban-studio.fly.dev. Config is in `fly.toml`; the SQLite file lives on a 1 GB volume mounted at `/data`.

1. Install `flyctl` and run `fly auth login`.
2. `fly apps create <name>` and `fly volumes create pm_data --region iad --size 1`.
3. Set secrets: `fly secrets set OPENROUTER_API_KEY=... OPENROUTER_MODEL=... PM_SESSION_SECRET=... PM_LOGIN_PASSWORD=...`. The default password is public in this repo, so change it for a public deployment.
4. `fly deploy --ha=false`.

The container starts as root only to give the mounted volume to the app user, then runs as that user (`docker-entrypoint.sh`).
