# Scripts

Start and stop the Docker app (image and container are both named `pm-app`, port 8000).

- `start-mac.sh`, `start-linux.sh`, `start-windows.ps1`: build the image and run it with `--env-file .env`. They stop if `.env` is missing (the Windows script also stops if the build fails). The container runs in the foreground; Playwright uses these as its web server.
- `stop-mac.sh`, `stop-linux.sh`, `stop-windows.ps1`: remove the container.

Docker Desktop must be running first.
