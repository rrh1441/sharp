#!/usr/bin/env bash
# start.sh – runs Gmail worker continuously and fires settler every hour
set -euo pipefail

echo "⇢ starting Gmail worker ..."
poetry run python -m worker &            # background long-poller
WORKER_PID=$!

while true; do
  echo "⇢ settler tick $(date -u +%FT%TZ)"
  poetry run python -m settler
  sleep 3600                             # 1 hour
done

# (The loop never exits; if it somehow does, kill the worker)
trap 'kill "$WORKER_PID"' EXIT