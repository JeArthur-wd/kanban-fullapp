# Project Management MVP

## Setup

Copy `.env.example` to `.env` in the repo root and set `OPENROUTER_API_KEY`. The start scripts require this file. Without a valid key the app runs, but AI chat returns an error.

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
3. Set secrets: `fly secrets set OPENROUTER_API_KEY=... OPENROUTER_MODEL=...`.
4. `fly deploy --ha=false`.

The container starts as root only to give the mounted volume to the app user, then runs as that user (`docker-entrypoint.sh`).
