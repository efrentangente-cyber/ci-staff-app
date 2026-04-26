# Auto-loaded for any `gunicorn app:app` run from this directory (Gunicorn default).
# Also loaded by scripts/start_gunicorn.sh via GUNICORN_CMD_ARGS / default file discovery.
import os
import warnings

# ──────────────────────────────────────────────────────────────────────────────
# Eventlet / gunicorn 25 compatibility
# ──────────────────────────────────────────────────────────────────────────────
# Problem 1: gunicorn 25 imports `logging` (and other stdlib modules with RLocks)
# before geventlet.py runs monkey_patch(). When geventlet then patches, eventlet
# finds those un-greened locks and prints "N RLock(s) were not greened".
# Fix: suppress the specific warning here (process-wide, inherited by workers).
# The un-greened logging lock is benign — eventlet cooperative threads still work.
warnings.filterwarnings(
    'ignore',
    message=r'.*not greened.*',
)
# Problem 2: geventlet.py emits a DeprecationWarning every worker boot. Silence it
# until we migrate to gevent/gthread.
warnings.filterwarnings(
    'ignore',
    message=r'.*eventlet worker is.*[Dd]eprecated.*',
    category=DeprecationWarning,
)

# Call monkey_patch() early so geventlet.py's own call becomes a no-op and the
# warning is never printed (eventlet skips re-patching already-patched modules).
import eventlet  # noqa: E402
if not eventlet.patcher.is_monkey_patched('os'):
    eventlet.monkey_patch()

# ──────────────────────────────────────────────────────────────────────────────
# Worker / server settings
# ──────────────────────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"

# Flask-SocketIO + in-memory rooms: one process only (no Redis message_queue here).
workers = 1
worker_class = "eventlet"
worker_connections = int(os.environ.get("GUNICORN_WORKER_CONNECTIONS", "1000") or "1000")

# Socket.IO long-polling holds requests open for up to the ping_timeout (60 s here).
# A non-zero Gunicorn timeout kills any worker that appears "silent" for that long.
# 0 = disable the silence kill entirely (workers are only killed on explicit signals).
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "0") or "0")
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "120") or "120")
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5") or "5")

# Gunicorn 25+ asyncio control socket breaks under eventlet (monkey-patched Thread + asyncio.run).
# --no-control-socket is also passed explicitly in scripts/start_gunicorn.sh and GUNICORN_CMD_ARGS.
control_socket_disable = True

proc_name = "dccco_ci"

# ──────────────────────────────────────────────────────────────────────────────
# Suppress "Bad file descriptor" noise during graceful shutdown
# ──────────────────────────────────────────────────────────────────────────────
# When Render sends SIGTERM for a rolling redeploy, gunicorn closes the listen
# socket while eventlet's WSGI layer is still tearing down Socket.IO connections.
# eventlet's wsgi.py calls socket.shutdown() on the already-closed fd and writes
#   "server=... client=... socket shutdown error: [Errno 9] Bad file descriptor"
# directly to stderr (a file-like object, NOT through Python's logging module).
# A logging.Filter won't intercept it; we must wrap sys.stderr.
import sys
import logging

_SHUTDOWN_NOISE = ('Bad file descriptor', 'socket shutdown error')


class _FilteredStream:
    """Drop shutdown-noise lines; pass everything else through unchanged."""
    def __init__(self, stream):
        self.__stream = stream

    def write(self, msg):
        if any(n in msg for n in _SHUTDOWN_NOISE):
            return
        self.__stream.write(msg)

    def flush(self):
        self.__stream.flush()

    def isatty(self):
        return getattr(self.__stream, 'isatty', lambda: False)()

    def __getattr__(self, name):
        return getattr(self.__stream, name)


sys.stderr = _FilteredStream(sys.stderr)

# Belt-and-suspenders: also add a logging.Filter for any path that *does* use
# the logging module (e.g. gunicorn's own error logger on some versions).
class _ShutdownNoiseLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return not any(n in msg for n in _SHUTDOWN_NOISE)


for _ln in ('eventlet.wsgi.server', 'eventlet.wsgi', 'gunicorn.error', 'gunicorn.access', ''):
    logging.getLogger(_ln).addFilter(_ShutdownNoiseLogFilter())
