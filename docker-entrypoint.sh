#!/bin/sh
set -e
# A mounted volume (for example on Fly.io) is owned by root; give it to the app user, then drop privileges.
if [ -d /data ]; then
  chown -R appuser:appuser /data
fi
exec setpriv --reuid=1000 --regid=1000 --init-groups "$@"
