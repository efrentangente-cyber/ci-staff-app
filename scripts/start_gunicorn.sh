#!/usr/bin/env bash
# Single production entrypoint for Render/Heroku-style hosts.
# - --no-control-socket: Gunicorn 25+ asyncio control server breaks when the eventlet worker
#   imports monkey_patch() into the master (asyncio.run / patched Thread.join).
# - --timeout 0: Socket.IO long-polling must not trip the "silent worker" kill.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PORT="${PORT:-5000}"

exec gunicorn \
  --config "$ROOT/gunicorn.conf.py" \
  --no-control-socket \
  --worker-class eventlet \
  -w 1 \
  --bind "0.0.0.0:${PORT}" \
  --timeout 0 \
  --graceful-timeout 120 \
  --worker-connections 1000 \
  app:app
