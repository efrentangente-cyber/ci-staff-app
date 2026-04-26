# Auto-loaded for any `gunicorn app:app` run from this directory (Gunicorn default).
# Fixes Render when the dashboard uses a minimal start command without worker flags.
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Flask-SocketIO + in-memory rooms: one process only (no Redis message_queue here).
workers = 1
worker_class = "eventlet"
worker_connections = int(os.environ.get("GUNICORN_WORKER_CONNECTIONS", "1000") or "1000")

# Long-poll / Engine.IO holds requests open; a finite timeout kills the worker as "silent".
# 0 disables the worker "no heartbeat" kill (see Gunicorn docs for `timeout`).
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "0") or "0")
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "120") or "120")
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5") or "5")

# Local `gunicorn app:app` only. Production should use scripts/start_gunicorn.sh (--no-control-socket, --timeout 0).
control_socket_disable = True

proc_name = "dccco_ci"
