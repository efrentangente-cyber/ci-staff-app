# IMPORTANT: eventlet monkey_patch must be called FIRST before any other imports.
# Guard: gunicorn's eventlet worker (geventlet.py) already calls monkey_patch() at module
# level in the master process. Re-patching in the worker triggers "N RLock(s) were not
# greened" warnings about locks created by gunicorn before the first patch. Skip if already done.
import eventlet
if not eventlet.patcher.is_monkey_patched('os'):
    eventlet.monkey_patch()

import sys

# Avoid UnicodeEncodeError on Windows consoles when printing diagnostic messages.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from flask import Flask, g, has_request_context, render_template, request, redirect, url_for, flash, send_file, jsonify, send_from_directory, session, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_socketio import SocketIO, emit, join_room, disconnect
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, get_database_type, is_postgresql  # Use database abstraction layer
from io import BytesIO
from document_helpers import (
    blob_bytes,
    ensure_documents_blob_columns,
    insert_loan_document_row,
    mime_type_from_document_row,
)
import os
import uuid
import re
import json
import mimetypes
import time
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import resend
import requests  # For SMS API

# Load environment variables
load_dotenv()

# DIAGNOSTIC: Print environment info on startup (helps debug Render issues)
print("\n" + "="*80)
print("🚀 DCCCO Loan Management System - Starting Up")
print("="*80)
print(f"📌 DATABASE_URL: {'SET ✓' if os.getenv('DATABASE_URL') else 'NOT SET ❌'}")
if os.getenv('DATABASE_URL'):
    db_url = os.getenv('DATABASE_URL')
    if db_url.startswith('postgresql') or db_url.startswith('postgres'):
        print(f"   Type: PostgreSQL ✓")
    else:
        print(f"   Type: {db_url.split(':')[0]}")
else:
    print("   ⚠️  WARNING: DATABASE_URL not set! App will use SQLite (local only)")
    print("   For Render deployment, set DATABASE_URL in dashboard!")
print("="*80 + "\n")

_startup_semaphore_key = (os.getenv('SEMAPHORE_API_KEY') or os.getenv('SMS_API_KEY') or '').strip()
if _startup_semaphore_key:
    print(f"✓ SEMAPHORE_API_KEY is set — outbound SMS will use Semaphore (key ends with ...{_startup_semaphore_key[-6:]}).")
else:
    print("ℹ️  SEMAPHORE_API_KEY is not set — set it in the environment (or .env) to send SMS via your Semaphore credits; otherwise TextBelt free tier is used as fallback.\n")

# Always store UTC - JS will convert to local time for display
def now_ph():
    """Return current UTC time for DB storage (JS handles timezone display)"""
    return datetime.utcnow()


def naive_utc_iso_z(dt=None):
    """Format a UTC (naive or aware) instant as ISO-8601 with Z for JavaScript Date."""
    if dt is None:
        dt = datetime.utcnow()
    if not isinstance(dt, datetime):
        return ''
    if dt.tzinfo is not None:
        dt = dt.astimezone(pytz.UTC).replace(tzinfo=None)
    return dt.isoformat() + 'Z'


def db_instant_iso_z_for_js(value):
    """
    Normalize DB-stored UTC instants (naive datetime or ISO string) to ISO-8601 with Z
    for JavaScript Date / relative time. Empty string if unparseable.
    """
    if value is None:
        return ''
    dt = None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        s = value.strip()
        if not s:
            return ''
        try:
            s_norm = s.replace('Z', '+00:00')
            if 'T' not in s_norm and len(s_norm) >= 10:
                if len(s_norm) > 10 and s_norm[10] == ' ':
                    s_norm = s_norm[:10] + 'T' + s_norm[11:].strip()
                elif len(s_norm) == 10:
                    s_norm = s_norm + 'T00:00:00'
            dt = datetime.fromisoformat(s_norm)
        except ValueError:
            return ''
    else:
        return ''
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    else:
        dt = dt.astimezone(pytz.UTC)
    naive_utc = dt.replace(tzinfo=None)
    return naive_utc.isoformat() + 'Z'


app = Flask(__name__)

# Official cooperative name (injected into Jinja as org_full_name, org_abbr, org_print_caps).
ORG_FULL_NAME = 'Dumaguete City Community Multi-Purpose Cooperative'
ORG_ABBR = 'DCCCO'

# Performance logger — emits WARNING lines visible in Render logs.
import logging as _logging
_perf_logger = _logging.getLogger('app.perf')
if not _perf_logger.handlers:
    _perf_handler = _logging.StreamHandler()
    _perf_handler.setFormatter(_logging.Formatter('[PERF] %(message)s'))
    _perf_logger.addHandler(_perf_handler)
_perf_logger.setLevel(_logging.WARNING)

_secret_key = (os.getenv('SECRET_KEY') or '').strip()
if not _secret_key:
    raise RuntimeError("SECRET_KEY must be set in environment for secure sessions.")
app.secret_key = _secret_key
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SIGNATURE_FOLDER'] = 'signatures'
# Render (or any host): optional root for durable files only — never mount disk over repo src.
_persist_root = (os.getenv('RENDER_PERSISTENT_DIR') or os.getenv('PERSISTENT_DATA_DIR') or '').strip()
if _persist_root:
    _persist_root = os.path.abspath(_persist_root)
    os.makedirs(_persist_root, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = os.path.join(_persist_root, 'uploads')
    app.config['SIGNATURE_FOLDER'] = os.path.join(_persist_root, 'signatures')
    app.config['MESSAGE_ATTACHMENTS_FOLDER'] = os.path.join(_persist_root, 'message_attachments')
    app.config['VOICE_MESSAGES_FOLDER'] = os.path.join(_persist_root, 'voice_messages')
else:
    app.config['MESSAGE_ATTACHMENTS_FOLDER'] = 'message_attachments'
    app.config['VOICE_MESSAGES_FOLDER'] = 'voice_messages'
for _fd in (
    app.config['UPLOAD_FOLDER'],
    app.config['SIGNATURE_FOLDER'],
    app.config['MESSAGE_ATTACHMENTS_FOLDER'],
    app.config['VOICE_MESSAGES_FOLDER'],
):
    os.makedirs(_fd, exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['WTF_CSRF_ENABLED'] = os.getenv('WTF_CSRF_ENABLED', 'True').lower() == 'true'
app.config['WTF_CSRF_TIME_LIMIT'] = None  # CSRF tokens don't expire
app.config['WTF_CSRF_CHECK_DEFAULT'] = os.getenv('WTF_CSRF_CHECK_DEFAULT', 'True').lower() == 'true'
app.config['REMEMBER_COOKIE_DURATION'] = __import__('datetime').timedelta(days=30)
app.config['PERMANENT_SESSION_LIFETIME'] = __import__('datetime').timedelta(hours=2)  # Session expires after 2 hours of inactivity
app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes
# HSTS / "production" UI — not the same as session cookie "Secure" (RENDER=1 is often only for DATABASE_URL on LAN).
_is_production = (os.getenv('FLASK_ENV', '').lower() == 'production') or (os.getenv('RENDER', '').lower() == 'true')
_flask_debug = app.config.get('DEBUG', False)
_use_https_local = (os.getenv('USE_HTTPS_LOCAL', 'false') or '').lower() in ('1', 'true', 'yes')
# True when actually deployed to render.com (HTTPS). Local .env often has RENDER=1 for Postgres — not HTTPS in the browser.
_on_render = (os.getenv('ON_RENDER', '').lower() == 'true')
_sce_env = (os.getenv('SESSION_COOKIE_SECURE') or '').strip()
if _sce_env:
    app.config['SESSION_COOKIE_SECURE'] = _sce_env.lower() == 'true'
else:
    # Default: Secure only on real Render. Without ON_RENDER, default False (http:// can save session).
    app.config['SESSION_COOKIE_SECURE'] = _on_render and (not _flask_debug)
# Browsers will not keep a Secure session cookie on plain http:// — login 302s to dashboard, then 302 back to /login.
if _flask_debug and (not _use_https_local) and app.config.get('SESSION_COOKIE_SECURE'):
    app.config['SESSION_COOKIE_SECURE'] = False
# Local http://: never keep Secure (browser drops the cookie → login loop).
if (not _on_render) and (not _use_https_local) and app.config.get('SESSION_COOKIE_SECURE'):
    app.config['SESSION_COOKIE_SECURE'] = False
    if _sce_env and _sce_env.lower() == 'true':
        print('⚠️  SESSION_COOKIE_SECURE was true in .env but not ON_RENDER/HTTPS; forced off for http:// login. '
              'On render.com, set ON_RENDER=true (and HTTPS). For local mkcert, set USE_HTTPS_LOCAL=true.')
if not _on_render and (os.getenv('RENDER', '').lower() == 'true') and (not _sce_env):
    print('ℹ️  RENDER=1 in .env (Postgres) does not enable Secure cookies. For hosted Render, add ON_RENDER=true.')
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# gzip / br responses (smaller HTML/JSON; no behavior change for users)
try:
    from flask_compress import Compress
    app.config.setdefault('COMPRESS_MIN_SIZE', 512)
    _compress = Compress()
    _compress.init_app(app)
except ImportError:
    pass

# ── WhiteNoise: serve /static/ files at WSGI level, before Flask routing ──────
# Problem: with a single eventlet worker, every static file request goes through
# the full Flask pipeline (rate limiter, before_request hooks, send_from_directory
# file I/O, after_request hooks). Requests serialise behind slower app requests,
# causing 7–8 s TTFB on tiny CSS/JS files.
# WhiteNoise intercepts /static/… before Flask sees the request, serves from an
# in-memory cache built at startup, and sets long-lived Cache-Control headers so
# the browser avoids the round-trip entirely on subsequent page loads.
try:
    from whitenoise import WhiteNoise as _WhiteNoise
    _static_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.wsgi_app = _WhiteNoise(
        app.wsgi_app,
        root=_static_root,
        prefix='static',
        # 1-day browser cache.  Files without a content-hash in the name get a
        # shorter lifetime so stale assets aren't cached across deploys.
        max_age=86400,
        # Re-scan disk on every request in dev so you don't need to restart when
        # editing static files; in production keep the startup snapshot (faster).
        autorefresh=not _on_render,
    )
    print('✓ WhiteNoise static file middleware active')
except ImportError:
    print('ℹ️  whitenoise not installed — Flask will serve static files (slower in production)')
except Exception as _wn_err:
    print(f'⚠️  WhiteNoise setup failed: {_wn_err} — falling back to Flask static serving')

_SKIP_SESSION_ENFORCE_ENDPOINTS = frozenset(
    {
        'login',
        'logout',
        'serve_static',
        'favicon',
        'serve_upload',
        'serve_signature',
        'serve_message_file',
    }
)


def _should_skip_session_enforce():
    """
    Do not run user_login_sessions check on every static/upload asset request.
    A single page can load 20+ images; each was doing a full DB round-trip and
    made the app feel globally slow. HTML/API routes still enforce every time.
    """
    ep = request.endpoint
    if ep in _SKIP_SESSION_ENFORCE_ENDPOINTS:
        return True
    p = request.path or ''
    if p.startswith('/static/') or p.startswith('/uploads/') or p.startswith('/signatures/') or p.startswith(
        '/serve_message_file/',
    ):
        return True
    # Socket.IO long-poll / transport hits Flask often; would duplicate session DB checks.
    if p.startswith('/socket.io'):
        return True
    return False


@app.template_filter('fmt_datetime')
def fmt_datetime(value, fmt='%Y-%m-%d %H:%M'):
    """Format datetime values safely for templates (datetime or ISO string)."""
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime(fmt)
        except ValueError:
            return value[:16] if len(value) >= 16 else value
    return str(value)


def _activity_log_timestamp_display(value, fmt='%d-%m-%Y %H:%M'):
    """DB stores UTC; show in DISPLAY_TIMEZONE (default Asia/Manila)."""
    if value is None:
        return ''
    tz_name = (os.getenv('DISPLAY_TIMEZONE') or 'Asia/Manila').strip() or 'Asia/Manila'
    try:
        display_tz = pytz.timezone(tz_name)
    except Exception:
        display_tz = pytz.timezone('Asia/Manila')
    dt = value
    if isinstance(value, str):
        try:
            s = value.strip().replace('Z', '+00:00')
            if 'T' not in s and s[:10].count('-') == 2:
                s = s.replace(' ', 'T', 1)
            dt = datetime.fromisoformat(s)
        except ValueError:
            return value
    if not isinstance(dt, datetime):
        return str(value)
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    else:
        dt = dt.astimezone(pytz.UTC)
    return dt.astimezone(display_tz).strftime(fmt)


@app.template_filter('activity_log_ts')
def activity_log_ts(value, fmt=None):
    return _activity_log_timestamp_display(value, fmt if fmt else '%d-%m-%Y %H:%M')


@app.template_filter('utc_iso_z')
def utc_iso_z_filter(value):
    """DB UTC instants as ISO+Z for data attributes and JavaScript Date (datetime or string)."""
    if isinstance(value, datetime):
        return naive_utc_iso_z(value)
    return db_instant_iso_z_for_js(value)


@app.template_filter('route_tokens')
def route_tokens_filter(value):
    """Split users.assigned_route (comma-separated route ids) for templates."""
    if not value:
        return []
    return [x.strip() for x in str(value).split(',') if x.strip()]


def _assigned_route_keys_set(value):
    """Non-empty route_key tokens from users.assigned_route (same semantics as route_tokens_filter)."""
    if not value:
        return set()
    return {x.strip() for x in str(value).split(',') if x.strip()}


def _ci_staff_route_claims_by_user(conn) -> dict:
    """Map user id → set(route_key) for rows with role ci_staff and any assigned_route."""
    rows = conn.execute(
        """
        SELECT id, assigned_route
        FROM users
        WHERE role = 'ci_staff' AND assigned_route IS NOT NULL
        """
    ).fetchall()
    claims = {}
    for r in rows or []:
        keys = _assigned_route_keys_set(r['assigned_route'])
        if keys:
            claims[int(r['id'])] = keys
    return claims


def _ci_route_keys_claimed_by_other_ci_staff(claims_by_uid: dict, exclude_user_id: int) -> set:
    """Routes already held by another CI/Bi staff (approved or pending), excluding exclude_user_id."""
    blocked = set()
    exclude_user_id = int(exclude_user_id)
    for uid, keys in claims_by_uid.items():
        if int(uid) == exclude_user_id:
            continue
        blocked |= set(keys)
    return blocked


_CI_ROUTE_LABELS = {
    'route_1_bayawan_kalumboyan': 'Bayawan → Kalumboyan',
    'route_2_bayawan_basay': 'Bayawan → Basay',
    'route_3_bayawan_sipalay': 'Bayawan → Sipalay',
    'route_4_bayawan_santa_catalina': 'Bayawan → Santa Catalina',
    'route_5_bayawan_center': 'Bayawan City Center',
    'route_6_bayawan_omod': 'Bayawan → Omod',
    'route_7_bayawan_tayawan': 'Bayawan → Tayawan',
    'route_8_bayawan_mabinay': 'Bayawan → Mabinay',
}

# Defaults for address-based CI auto-assignment (merged with `ci_coverage_routes.keywords` from DB).
_FALLBACK_ADDRESS_KEYWORDS = {
    'route_1_bayawan_kalumboyan': ['kalumboyan', 'kalamtukan', 'malabugas', 'bugay', 'nangka'],
    'route_2_bayawan_basay': ['basay', 'actin', 'bal-os', 'bongalonan', 'cabalayongan', 'maglinao', 'nagbo-alao', 'olandao'],
    'route_3_bayawan_sipalay': ['sipalay', 'cabadiangan', 'camindangan', 'canturay', 'cartagena', 'mambaroto', 'maricalum'],
    'route_4_bayawan_santa_catalina': [
        'santa catalina', 'alangilan', 'amio', 'buenavista', 'caigangan', 'cawitan', 'manalongon',
        'milagrosa', 'obat', 'talalak',
    ],
    'route_5_bayawan_center': [
        'ali-is', 'banaybanay', 'banga', 'boyco', 'cansumalig',
        # 'dawis' / 'san jose' omitted — corridor barangays on Kalumboyan–Dawis style routes handled via
        # _BAYAWAN_BARANGAY_SEGMENT_LABEL_HINTS + custom coverage routes whose labels include those hints.
        'manduao', 'mandu-ao', 'maninihon',
        'minaba', 'narra', 'pagatban', 'poblacion', 'san isidro', 'san miguel', 'san roque', 'suba',
        'tabuan', 'tayawan', 'tinago', 'ubos', 'villareal', 'villasol',
    ],
    'route_6_bayawan_omod': ['omod', 'tamisu'],
    'route_7_bayawan_tayawan': ['hilmantagon'],
    'route_8_bayawan_mabinay': ['mabinay', 'bonbon', 'bongabong'],
}

# Seed rows for `ci_coverage_routes` (INSERT OR IGNORE / ON CONFLICT DO NOTHING); keywords stored as JSON array text.
_CI_COVERAGE_SEED = [
    (
        'route_1_bayawan_kalumboyan', 'Bayawan → Kalumboyan', 10,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_1_bayawan_kalumboyan'], ensure_ascii=False),
    ),
    (
        'route_2_bayawan_basay', 'Bayawan → Basay', 20,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_2_bayawan_basay'], ensure_ascii=False),
    ),
    (
        'route_3_bayawan_sipalay', 'Bayawan → Sipalay', 30,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_3_bayawan_sipalay'], ensure_ascii=False),
    ),
    (
        'route_4_bayawan_santa_catalina', 'Bayawan → Santa Catalina', 40,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_4_bayawan_santa_catalina'], ensure_ascii=False),
    ),
    (
        'route_5_bayawan_center', 'Bayawan City Center', 50,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_5_bayawan_center'], ensure_ascii=False),
    ),
    (
        'route_6_bayawan_omod', 'Bayawan → Omod', 60,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_6_bayawan_omod'], ensure_ascii=False),
    ),
    (
        'route_7_bayawan_tayawan', 'Bayawan → Tayawan', 70,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_7_bayawan_tayawan'], ensure_ascii=False),
    ),
    (
        'route_8_bayawan_mabinay', 'Bayawan → Mabinay', 80,
        json.dumps(_FALLBACK_ADDRESS_KEYWORDS['route_8_bayawan_mabinay'], ensure_ascii=False),
    ),
]

_PRESET_CI_ROUTE_KEYS = frozenset(_FALLBACK_ADDRESS_KEYWORDS.keys())

# Barangays in Bayawan resolved to a corridor route when the manage-users label contains both hints
# e.g. "City of Bayawan: Kalumboyan → Dawis" (handles Purok Aya, San Jose, Bayawan that were matching city-center preset).
_BAYAWAN_BARANGAY_SEGMENT_LABEL_HINTS = {
    'san jose': ('kalumboyan', 'dawis'),
    'dawis': ('kalumboyan', 'dawis'),
}

# Strip from route_5 keyword lists (preset + stale DB merges) — these barangays use corridor routing above.
_ROUTE5_BARANGAYS_ASSIGNED_TO_CORRIDOR = frozenset({'san jose', 'dawis'})

_ci_route_label_cache: dict | None = None
_ci_route_sort_index_cache: dict | None = None

# Municipality / province placeholders that custom routes used to keyword — must not decide a match alone,
# or every "…Bayawan City…" applicant hits whichever route appears first (wrong CI).
_CI_ROUTE_GENERIC_ADDRESS_KEYWORDS = frozenset({
    x.strip().lower()
    for x in (
        'bayawan',
        'bayawan city',
        'negros oriental',
        'negros occidental',
        'negros',
        'philippines',
        'ph',
    )
    if x.strip()
})


def invalidate_ci_route_label_cache() -> None:
    global _ci_route_label_cache, _ci_route_sort_index_cache
    _ci_route_label_cache = None
    _ci_route_sort_index_cache = None


def get_ci_route_label_dict() -> dict:
    """Display labels: DB `ci_coverage_routes` (active) merged over built-in fallback."""
    global _ci_route_label_cache
    if _ci_route_label_cache is not None:
        return _ci_route_label_cache
    out = dict(_CI_ROUTE_LABELS)
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT route_key, label
            FROM ci_coverage_routes
            WHERE is_active = 1
            ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()
        for r in rows or []:
            k = r['route_key']
            lab = r['label']
            if k and lab is not None:
                out[str(k).strip()] = str(lab).strip()
    except Exception as e:
        app.logger.debug('get_ci_route_label_dict: %s', e)
    _ci_route_label_cache = out
    return out


def get_ci_route_address_match_map() -> dict:
    """route_key -> list of lowercase address keywords. DB keywords override/extend fallbacks for same key."""
    merged = {k: list(v) for k, v in _FALLBACK_ADDRESS_KEYWORDS.items()}
    try:
        conn = get_db()
        rows = conn.execute(
            "SELECT route_key, keywords FROM ci_coverage_routes WHERE is_active = 1"
        ).fetchall()
        for r in rows or []:
            rk = r['route_key']
            raw = (r['keywords'] or '') or ''
            if not str(raw).strip():
                continue
            kws = []
            try:
                j = json.loads(raw)
                if isinstance(j, list):
                    kws = [str(x).lower() for x in j if str(x).strip()]
            except Exception:
                kws = [x.strip().lower() for x in str(raw).split(',') if x.strip()]
            if not kws:
                continue
            merged[str(rk).strip()] = kws
    except Exception as e:
        app.logger.debug('get_ci_route_address_match_map: %s', e)
    try:
        r5 = merged.get('route_5_bayawan_center')
        if r5 is not None:
            merged['route_5_bayawan_center'] = [
                kw for kw in r5 if kw not in _ROUTE5_BARANGAYS_ASSIGNED_TO_CORRIDOR
            ]
    except Exception:
        pass
    return merged


def _normalize_address_for_ci_route_match(addr: str | None) -> str:
    if not addr:
        return ''
    x = str(addr).lower().replace(',', ' ')
    x = re.sub(r'\s+', ' ', x).strip()
    return x


def _keyword_boundary_match_normalized(keyword: str, addr_norm: str) -> bool:
    """Phrase must appear without touching extra letters (fewer bogus substring hits)."""
    kw = keyword.strip().lower()
    if not kw or not addr_norm:
        return False
    idx = addr_norm.find(kw)
    if idx < 0:
        return False
    prev = addr_norm[idx - 1] if idx > 0 else ' '
    end = idx + len(kw)
    nxt = addr_norm[end] if end < len(addr_norm) else ' '

    def _boundary(ch):
        return not (ch.isalnum() or ch in '-−‐‑⁃')

    return _boundary(prev) and _boundary(nxt)


def get_ci_route_sort_index_map() -> dict:
    """route_key -> [sort_order, id] rows for deterministic tie-breaking (lower sort_order wins)."""
    global _ci_route_sort_index_cache
    if _ci_route_sort_index_cache is not None:
        return _ci_route_sort_index_cache
    rows = []
    try:
        conn = get_db()
        rows = conn.execute(
            '''
            SELECT route_key, sort_order, id
            FROM ci_coverage_routes
            WHERE is_active = 1
            '''
        ).fetchall()
    except Exception as e:
        app.logger.debug('get_ci_route_sort_index_map: %s', e)
    out = {}
    for r in rows or []:
        rk = str(r['route_key'] or '').strip()
        if not rk:
            continue
        try:
            so = int(r['sort_order'] or 0)
        except (TypeError, ValueError):
            so = 0
        try:
            rid = int(r['id'] or 0)
        except (TypeError, ValueError):
            rid = 0
        out[rk] = [so, rid]
    _ci_route_sort_index_cache = out
    return out


def _bayawan_city_context_address(addr_norm: str) -> bool:
    """True if applicant address reads as Bayawan (City of Bayawan service area vs other LGUs with same barangay names)."""
    if not addr_norm:
        return False
    return 'bayawan' in addr_norm


def _corridor_hints_for_bayawan_barangay_hit(addr_norm: str) -> tuple[str, ...] | None:
    """If a routed barangay token matches, return DB label substring hints for the corridor route."""
    for bar_token, hints in _BAYAWAN_BARANGAY_SEGMENT_LABEL_HINTS.items():
        if _keyword_boundary_match_normalized(bar_token, addr_norm):
            return tuple(h.strip().lower() for h in hints if (str(h)).strip())
    return None


def resolve_coverage_route_key_by_label_hints(hints: tuple[str, ...]) -> str | None:
    """Pick route_key whose label mentions every hint substring; prefer non-preset custom coverage rows."""
    if len(hints) < 2:
        return None
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT route_key, label
            FROM ci_coverage_routes
            WHERE is_active = 1
            ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()
    except Exception as e:
        app.logger.debug('resolve_coverage_route_key_by_label_hints: %s', e)
        return None
    candidates_custom = []
    candidates_other = []
    for r in rows or []:
        rk = str(r['route_key'] or '').strip()
        lab = str(r['label'] or '').lower()
        if not rk or not lab:
            continue
        if all(h in lab for h in hints):
            if rk not in _PRESET_CI_ROUTE_KEYS:
                candidates_custom.append(rk)
            else:
                candidates_other.append(rk)
    return (candidates_custom[0] if candidates_custom else (candidates_other[0] if candidates_other else None))


def resolve_ci_route_key_for_member_address(member_address: str | None) -> str | None:
    """Best route_key for member_address: Bayawan corridor barangays first, then keyword tiers."""
    addr_norm = _normalize_address_for_ci_route_match(member_address)
    if not addr_norm:
        return None

    # Kalumboyan→Dawis corridor barangays in Bayawan: assign custom segment route before generic keyword tiers.
    if _bayawan_city_context_address(addr_norm):
        ch = _corridor_hints_for_bayawan_barangay_hit(addr_norm)
        if ch:
            seg = resolve_coverage_route_key_by_label_hints(ch)
            if seg:
                return seg

    route_map = get_ci_route_address_match_map()
    sort_map = get_ci_route_sort_index_map()
    ranked = []
    for route_key, keywords in route_map.items():
        best_len = 0
        for raw_kw in keywords:
            kw = str(raw_kw).strip().lower()
            if not kw or kw in _CI_ROUTE_GENERIC_ADDRESS_KEYWORDS:
                continue
            if not _keyword_boundary_match_normalized(kw, addr_norm):
                continue
            if len(kw) > best_len:
                best_len = len(kw)
        if best_len <= 0:
            continue
        rk = str(route_key).strip()
        tier = sort_map.get(rk, [999999, 999999])
        ranked.append((best_len, tier[0], tier[1], rk))
    if not ranked:
        return None
    ranked.sort(key=lambda t: (-t[0], t[1], t[2], t[3]))
    return ranked[0][3]


def fetch_first_ci_staff_id_for_route_key(conn, route_key: str | None):
    rk = str(route_key or '').strip()
    if not rk:
        return None
    like_params = (
        f'%{rk}%,%',
        f'%,{rk}%',
        f'%,{rk},%',
        rk,
    )
    try:
        row = conn.execute(
            '''
            SELECT id FROM users
            WHERE role=? AND is_approved=1
            AND (assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route = ?)
            LIMIT 1
            ''',
            ('ci_staff',) + like_params,
        ).fetchone()
        if row:
            return row['id']
    except Exception as e:
        app.logger.debug('fetch_first_ci_staff_id_for_route_key: %s', e)
        try:
            row = conn.execute(
                '''
                SELECT id FROM users
                WHERE role=? AND (assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route = ?)
                LIMIT 1
                ''',
                ('ci_staff',) + like_params,
            ).fetchone()
            if row:
                return row['id']
        except Exception:
            pass
        return None
    return None


def ensure_ci_coverage_routes_table():
    """CI coverage areas: labels + optional keywords (JSON) for address-based assignment."""
    try:
        conn = get_db()
        db_type = get_database_type()
        if db_type == 'sqlite':
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ci_coverage_routes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    route_key TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL,
                    keywords TEXT,
                    sort_order INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                )
                """
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ci_coverage_routes (
                    id SERIAL PRIMARY KEY,
                    route_key TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL,
                    keywords TEXT,
                    sort_order INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        for route_key, label, order, kws in _CI_COVERAGE_SEED:
            if db_type == 'sqlite':
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ci_coverage_routes (route_key, label, sort_order, keywords, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (route_key, label, order, kws),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO ci_coverage_routes (route_key, label, sort_order, keywords, is_active)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT (route_key) DO NOTHING
                    """,
                    (route_key, label, order, kws),
                )
        conn.commit()
        conn.close()
        print('✓ ci_coverage_routes table ensured')
    except Exception as e:
        print(f'⚠️  ci_coverage_routes migration warning: {e}')


def list_ci_routes_for_ui():
    """Rows for manage-users modals: { route_key, label }. No close on get_db()."""
    try:
        conn = get_db()
        rows = conn.execute(
            """
            SELECT route_key, label
            FROM ci_coverage_routes
            WHERE is_active = 1
            ORDER BY sort_order ASC, id ASC
            """
        ).fetchall()
        return [{'route_key': r['route_key'], 'label': r['label']} for r in rows]
    except Exception as e:
        app.logger.debug('list_ci_routes_for_ui: %s', e)
        return [{'route_key': k, 'label': v} for k, v in _CI_ROUTE_LABELS.items()]


@app.template_filter('ci_route_label')
def ci_route_label_filter(rid):
    if not rid:
        return ''
    d = get_ci_route_label_dict()
    return d.get(str(rid).strip(), str(rid))


# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'webm', 'mp3', 'wav'}

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Offline / WebView: idempotent CI interview POST (FormData + client_request_id)
from offline_interview_complete import init_offline_interview_api
from ci_offline_saves import ensure_ci_offline_packages_table, init_ci_offline_saves, get_offline_package_for_wizard

init_offline_interview_api(app, csrf)
init_ci_offline_saves(app, csrf)


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    """Gracefully handle CSRF mismatches for both AJAX and full-page requests."""
    try:
        msg = 'Security token mismatch. Please refresh the page and try again.'
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or (request.accept_mimetypes and request.accept_mimetypes.best == 'application/json')
            or request.path.startswith('/api/')
            or request.is_json
        )
        if is_ajax:
            return jsonify({'success': False, 'error': 'csrf_mismatch', 'message': msg}), 400
        flash(msg, 'warning')
        ref = request.referrer
        current = request.url
        # Avoid redirect loops when referrer is the same failing URL.
        if ref and ref != current:
            return redirect(ref)
        return redirect(url_for('login'))
    except Exception:
        return jsonify({'success': False, 'error': 'csrf_mismatch'}), 400

# Import secure routing module
from secure_routes import SecureRouter, require_token

# Initialize Rate Limiter - 50 requests per minute
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["50 per minute"],
    storage_uri="memory://"
)

# Exempt static assets from rate limiting.
# WhiteNoise already intercepts /static/… before Flask, so these filters are
# belt-and-suspenders for requests that fall through (e.g. favicon.ico).
@limiter.request_filter
def _limiter_exempt_static():
    p = request.path or ''
    return p.startswith('/static/') or p == '/favicon.ico'

# Configure Resend
resend.api_key = os.getenv('RESEND_API_KEY')


def _normalize_permission_list(raw):
    """Turn stored permissions (comma-separated string or list) into a list of tokens."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple, set)):
        return [str(x).strip() for x in raw if str(x).strip()]
    return [x.strip() for x in str(raw).split(',') if x.strip()]


def has_permission(user, permission):
    """Check if user has specific permission (loan_officer comma-separated flags; admin always yes)."""
    if getattr(user, 'role', None) == 'admin':
        return True
    if getattr(user, 'role', None) == 'loan_officer':
        plist = _normalize_permission_list(getattr(user, 'permissions', None))
        return permission in plist
    return False


def can_manage_loan_types(user):
    """Loan Types UI + APIs: admin, or officer with manage_loan_types OR system_settings (legacy bundle)."""
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    if getattr(user, 'role', None) == 'admin':
        return True
    if getattr(user, 'role', None) == 'loan_officer':
        return has_permission(user, 'manage_loan_types') or has_permission(user, 'system_settings')
    return False


# Add template helper function
@app.context_processor
def utility_processor():
    from flask_wtf.csrf import generate_csrf

    def user_perm_list(user):
        if not user or not getattr(user, 'is_authenticated', False):
            return []
        if getattr(user, 'role', None) == 'admin':
            return ['manage_users', 'system_settings', 'manage_loan_types']
        return _normalize_permission_list(getattr(user, 'permissions', None))

    def user_has_perm(user, permission_name):
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'role', None) == 'admin':
            return True
        return permission_name in user_perm_list(user)
    
    def get_user_by_id(user_id):
        if not user_id:
            return None
        try:
            return get_db().execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        except Exception:
            return None
    
    def secure_token(resource_type, resource_id):
        """Generate a secure token for hiding IDs in URLs"""
        return SecureRouter.generate_token(resource_type, resource_id)
    
    def csrf_token():
        """Generate CSRF token for forms"""
        return generate_csrf()

    # Inject unread message count into every template automatically.
    # get_unread_message_count() uses COUNT_CACHE_TTL in-process cache; on cache-miss it
    # uses get_db() — same request-scoped connection as the route (do not close inside helpers).
    message_unread_count = 0
    try:
        import time as _t
        from flask_login import current_user as _cu
        if _cu.is_authenticated:
            _ctx_t0 = _t.monotonic()
            message_unread_count = get_unread_message_count(_cu.id)
            _ctx_elapsed = _t.monotonic() - _ctx_t0
            if _ctx_elapsed > 0.1:
                import logging as _log
                _log.getLogger('app.perf').warning(
                    'context_processor get_unread_message_count slow %.0fms user=%s',
                    _ctx_elapsed * 1000, _cu.id,
                )
    except Exception:
        pass

    return dict(
        get_user_by_id=get_user_by_id,
        message_unread_count=message_unread_count,
        secure_token=secure_token,
        csrf_token=csrf_token,
        org_full_name=ORG_FULL_NAME,
        org_abbr=ORG_ABBR,
        org_print_caps=ORG_FULL_NAME.upper(),
        user_perm_list=user_perm_list,
        user_has_perm=user_has_perm,
    )


def _get_cached_count(cache, user_id):
    now_ts = time.time()
    with _count_cache_lock:
        cached = cache.get(user_id)
        if cached and (now_ts - cached['ts']) <= _COUNT_CACHE_TTL_SECONDS:
            return cached['value']
    return None


def _set_cached_count(cache, user_id, value):
    with _count_cache_lock:
        cache[user_id] = {'value': int(value), 'ts': time.time()}


def _clear_cached_count(cache, user_id):
    try:
        with _count_cache_lock:
            cache.pop(user_id, None)
    except Exception:
        pass


def get_unread_message_count(user_id):
    cached = _get_cached_count(_message_count_cache, user_id)
    if cached is not None:
        return cached
    row = None
    try:
        row = get_db().execute('''
            SELECT COUNT(*) as count FROM direct_messages
            WHERE receiver_id = ? AND is_read = 0
        ''', (user_id,)).fetchone()
    except Exception:
        row = None
    count = row['count'] if row else 0
    _set_cached_count(_message_count_cache, user_id, count)
    return count


def get_unread_notification_count(user_id):
    cached = _get_cached_count(_notification_count_cache, user_id)
    if cached is not None:
        return cached
    row = None
    try:
        row = get_db().execute(
            "SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'",
            (user_id,)
        ).fetchone()
    except Exception:
        try:
            row = get_db().execute(
                "SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0",
                (user_id,)
            ).fetchone()
        except Exception:
            row = None
    count = row['count'] if row else 0
    _set_cached_count(_notification_count_cache, user_id, count)
    return count


# CI staff list cache — invalidated on user approve/role change; TTL is a safety net.
_ci_staff_cache: dict = {}
_CI_STAFF_CACHE_TTL = 120  # seconds


def _invalidate_ci_staff_cache():
    """Call after any users table write that changes CI staff membership/approval."""
    _ci_staff_cache.clear()


def fetch_ci_staff_list(conn, include_pending=True):
    """
    Fetch CI staff list with compatibility for older schemas where users.is_approved
    may not exist yet in production.  Results are cached for up to 120 s so that
    dashboard and application detail pages don't each hit the DB independently.
    """
    cache_key = 'all' if include_pending else 'approved'
    _now = time.time()
    _cached = _ci_staff_cache.get(cache_key)
    if _cached and (_now - _cached['ts']) < _CI_STAFF_CACHE_TTL:
        return _cached['value']

    where_role = "WHERE role='ci_staff'"
    order_by = "ORDER BY name ASC"
    if include_pending:
        try:
            result = conn.execute(
                f'''
                SELECT id, name, email, is_approved
                FROM users
                {where_role}
                {order_by}
                '''
            ).fetchall()
        except Exception:
            try:
                rows = conn.execute(
                    f'''
                    SELECT id, name, email
                    FROM users
                    {where_role}
                    {order_by}
                    '''
                ).fetchall()
            except Exception:
                return []
            result = [
                {'id': r['id'], 'name': r['name'], 'email': r['email'], 'is_approved': 1}
                for r in rows
            ]
        _ci_staff_cache[cache_key] = {'value': result, 'ts': _now}
        return result

    try:
        result = conn.execute(
            f'''
            SELECT id, name, email, is_approved
            FROM users
            {where_role} AND is_approved=1
            {order_by}
            '''
        ).fetchall()
    except Exception:
        try:
            rows = conn.execute(
                f'''
                SELECT id, name, email
                FROM users
                {where_role}
                {order_by}
                '''
            ).fetchall()
        except Exception:
            return []
        result = [{'id': r['id'], 'name': r['name'], 'email': r['email'], 'is_approved': 1} for r in rows]

    _ci_staff_cache[cache_key] = {'value': result, 'ts': _now}
    return result


def _fetch_loan_types_flexible(conn, active_only=False):
    """
    Read loan_types with backward-compatible column mapping.
    Supports legacy schemas where 'name' might be stored as loan_type/loan_name.
    """
    preview = conn.execute('SELECT * FROM loan_types LIMIT 0')
    cols = [d[0] for d in preview.description] if preview and preview.description else []
    if not cols:
        return []

    name_key = None
    for candidate in ('name', 'loan_type', 'loan_name', 'type_name'):
        if candidate in cols:
            name_key = candidate
            break

    base_query = 'SELECT * FROM loan_types'
    if active_only and 'is_active' in cols:
        base_query += ' WHERE is_active=1'
    if name_key:
        base_query += f' ORDER BY {name_key} ASC'
    rows = conn.execute(base_query).fetchall()

    normalized = []
    for row in rows:
        row_dict = dict(row)
        row_dict['name'] = (row_dict.get(name_key) if name_key else None) or row_dict.get('name') or 'Loan Type'
        normalized.append(row_dict)
    return normalized


def _loan_types_schema_info(conn):
    """Return loan_types schema metadata for cross-db compatibility."""
    preview = conn.execute('SELECT * FROM loan_types LIMIT 0')
    cols = [d[0] for d in preview.description] if preview and preview.description else []
    if not cols:
        return {'columns': [], 'name_key': 'name'}
    for candidate in ('name', 'loan_type', 'loan_name', 'type_name'):
        if candidate in cols:
            return {'columns': cols, 'name_key': candidate}
    return {'columns': cols, 'name_key': 'name'}

_socketio_origins_raw = (os.getenv('SOCKETIO_ALLOWED_ORIGINS') or '').strip()
if _socketio_origins_raw:
    _socketio_origins = [o.strip() for o in _socketio_origins_raw.split(',') if o.strip()]
else:
    _socketio_origins = None

# Must match Gunicorn: `-k eventlet` requires async_mode='eventlet' (see gunicorn.conf.py).
# Using 'threading' here breaks WebSockets under eventlet. Production uses control_socket_disable
# so Gunicorn 25's arbiter asyncio control socket is not broken by eventlet's monkey_patch.
_socket_async_mode = (os.getenv('SOCKETIO_ASYNC_MODE') or 'eventlet').strip().lower()
if _socket_async_mode not in ('eventlet', 'threading', 'gevent'):
    _socket_async_mode = 'eventlet'

socketio = SocketIO(
    app,
    cors_allowed_origins=_socketio_origins,
    async_mode=_socket_async_mode,
    ping_timeout=60,
    ping_interval=10,
    logger=False,
    engineio_logger=False,
    always_connect=True,
    manage_session=False,
)

# Track online users
online_users = {}  # {user_id: {'name': name, 'role': role, 'last_seen': timestamp}}

# Tiny in-memory caches to reduce repeated COUNT(*) queries per user (message + notification badges).
try:
    _COUNT_CACHE_TTL_SECONDS = int((os.getenv('COUNT_CACHE_TTL_SECONDS') or '90').strip() or '90')
except ValueError:
    _COUNT_CACHE_TTL_SECONDS = 90
_count_cache_lock = eventlet.semaphore.Semaphore()
# Skip user_login_sessions SELECT on rapid GET navigations (default ~20s throttle). POST/PUT/PATCH/DELETE always validate.
# Set SESSION_ENFORCE_GET_MIN_SEC=0 to check every request (slowest, strictest).
try:
    _ENFORCE_GET_MIN_SEC = float((os.getenv('SESSION_ENFORCE_GET_MIN_SEC') or '20').strip() or '20')
except ValueError:
    _ENFORCE_GET_MIN_SEC = 20.0
_ENFORCE_GET_MIN_SEC = max(0.0, _ENFORCE_GET_MIN_SEC)
_notification_count_cache = {}
_message_count_cache = {}
_security_alert_cache = {}
_SECURITY_ALERT_TTL_SECONDS = 300
# System settings cache — invalidated on every write to system_settings table.
_system_settings_cache: dict = {'data': None, 'ts': 0.0}
_SYSTEM_SETTINGS_CACHE_TTL = 60  # seconds
# Server-side "abandoned session" window — increase for long forms / field work (overridable).
try:
    _SESSION_STALE_HOURS = float((os.getenv('SESSION_STALE_HOURS') or '8').strip() or '8')
except ValueError:
    _SESSION_STALE_HOURS = 8.0
_SESSION_STALE_HOURS = max(1.0, min(72.0, _SESSION_STALE_HOURS))
_SINGLE_LOGIN_STALE_SECONDS = int(_SESSION_STALE_HOURS * 3600)
# How often to update last_seen in the DB (keeps long single-page work from going stale).
try:
    _SESSION_TOUCH_MIN_SEC = int((os.getenv('SESSION_TOUCH_MIN_SEC') or '45').strip() or '45')
except ValueError:
    _SESSION_TOUCH_MIN_SEC = 45
_SESSION_TOUCH_MIN_SEC = max(15, min(600, _SESSION_TOUCH_MIN_SEC))

# Serve static files — fallback only (WhiteNoise handles /static/… before Flask).
# This route is only reached when WhiteNoise is not installed or misses a file.
@app.route('/static/<path:filename>')
def serve_static(filename):
    resp = send_from_directory('static', filename)
    if 'Cache-Control' not in resp.headers:
        resp.headers['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=3600'
    return resp

# Serve favicon directly at /favicon.ico
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/images', 'logo.jpg', mimetype='image/jpeg')

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Database is now managed by database.py - supports both SQLite and PostgreSQL

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_password_strength(password):
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal"""
    filename = secure_filename(filename)
    # Remove any remaining path separators
    filename = filename.replace('/', '').replace('\\', '')
    return filename


def _is_path_within_directory(directory, candidate_path):
    """
    True if candidate_path is inside directory (after resolving ..).
    Safer than str.startswith() on Windows (e.g. C:\\a vs C:\\ab).
    """
    d = os.path.abspath(directory)
    p = os.path.abspath(candidate_path)
    d_prefix = d if d.endswith(os.sep) else d + os.sep
    return p == d or p.startswith(d_prefix)


def _message_media_roots():
    return (
        os.path.abspath(app.config['MESSAGE_ATTACHMENTS_FOLDER']),
        os.path.abspath(app.config['VOICE_MESSAGES_FOLDER']),
    )


def _resolve_stored_message_media_path(stored_path):
    """
    Map DB file_path to a real file under configured attachment roots.
    Supports legacy values like message_attachments/... after moving to RENDER_PERSISTENT_DIR.
    """
    if not stored_path:
        return None
    roots = _message_media_roots()
    raw = str(stored_path).strip()
    s_abs = os.path.abspath(raw.replace('\\', os.sep))
    if os.path.isfile(s_abs) and any(_is_path_within_directory(r, s_abs) for r in roots):
        return s_abs
    norm = raw.replace('\\', '/')
    for prefix, root in (('message_attachments', roots[0]), ('voice_messages', roots[1])):
        if norm == prefix or norm.startswith(prefix + '/'):
            tail = norm[len(prefix) :].lstrip('/')
            candidate = os.path.normpath(os.path.join(root, tail))
            if os.path.isfile(candidate) and _is_path_within_directory(root, candidate):
                return candidate
    bn = os.path.basename(norm)
    if bn:
        for root in roots:
            candidate = os.path.normpath(os.path.join(root, bn))
            if os.path.isfile(candidate) and _is_path_within_directory(root, candidate):
                return candidate
    return None


def _upload_relpath_for_serve(file_path_stored):
    """
    Build the relative path under UPLOAD_FOLDER for use with serve_upload <path:filename>.
    The DB may store a Windows path, a relative path, or 'uploads/...' — only using basename
    was wrong for subfolders and sometimes failed when cwd differed from where files live.
    """
    if not file_path_stored or not str(file_path_stored).strip():
        return ''
    s = str(file_path_stored).replace('\\', '/').strip()
    s = s.split('?')[0].split('#')[0]
    parts = [p for p in s.split('/') if p]
    if not parts:
        return ''
    for j, seg in enumerate(parts):
        if seg.lower() == 'uploads' and j < len(parts) - 1:
            sub = '/'.join(parts[j + 1 :])
            if '..' in sub.split('/'):
                return os.path.basename(s.replace('/', os.sep) or s)
            return sub
    return parts[-1]


# Optional: set HSTS_ENABLE=false to disable (e.g. split HTTP/HTTPS in odd setups).
_hsts_header_enabled = (os.getenv('HSTS_ENABLE', 'true' if _is_production else 'false')).lower() == 'true'


def _client_request_is_https():
    """True when the public URL is HTTPS (proxy-friendly; does not change app logic)."""
    if request.is_secure:
        return True
    return (request.headers.get('X-Forwarded-Proto', '') or '').lower().split(',')[0].strip() == 'https'


@app.after_request
def _add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Legacy plugins / cross-domain policy files; does not affect normal HTML/JS.
    response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
    if _hsts_header_enabled and _client_request_is_https():
        try:
            max_age = int((os.getenv('HSTS_MAX_AGE') or '15552000').strip())  # default 180 days
        except ValueError:
            max_age = 15552000
        if max_age > 0:
            # Subresource behavior unchanged; this only hardens the HTTPS channel after first visit.
            response.headers.setdefault('Strict-Transport-Security', f'max-age={max_age}; includeSubDomains')
    return response


class User(UserMixin):
    def __init__(self, id, email, name, role, signature_path=None, backup_email=None, profile_photo=None, assigned_route=None, permissions=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.signature_path = signature_path
        self.backup_email = backup_email
        self.profile_photo = profile_photo
        self.assigned_route = assigned_route
        self.permissions = permissions


ROLE_ALIASES = {
    'superadmin': 'admin',
    'super_admin': 'admin',
    'loan officer': 'loan_officer',
    'loan_officer': 'loan_officer',
    'ci/bi': 'ci_staff',
    'ci-bi': 'ci_staff',
    'ci_bi': 'ci_staff',
    'ci staff': 'ci_staff',
    'lps': 'loan_staff',
    'loan staff': 'loan_staff'
}

VALID_ROLES = {'admin', 'loan_officer', 'loan_staff', 'ci_staff'}
MANAGE_USERS_ASSIGNABLE_ROLES = {'loan_staff', 'ci_staff'}


def normalize_role(role):
    """Normalize legacy/display role names to system role keys."""
    if role is None:
        return None
    role_key = str(role).strip().lower()
    mapped = ROLE_ALIASES.get(role_key, role_key)
    return mapped if mapped in VALID_ROLES else None

def send_verification_email(to_email, code, user_name):
    """Send verification code email using Resend"""
    try:
        from_email = os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
        
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": f"Password Reset Verification Code - {ORG_ABBR}",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f7fa;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h2 style="color: #1e3a5f; margin: 0;">{ORG_FULL_NAME}</h2>
                            <p style="color: #666; margin: 5px 0;">Loan Management System</p>
                        </div>
                        
                        <h3 style="color: #1e3a5f;">Hello {user_name},</h3>
                        
                        <p style="color: #333; line-height: 1.6;">
                            You requested to reset your password. Use the verification code below to continue:
                        </p>
                        
                        <div style="background: #f8f9fa; border-left: 4px solid #1e3a5f; padding: 20px; margin: 20px 0; text-align: center;">
                            <p style="margin: 0; color: #666; font-size: 14px;">Your Verification Code</p>
                            <h1 style="margin: 10px 0; color: #1e3a5f; font-size: 36px; letter-spacing: 5px;">{code}</h1>
                            <p style="margin: 0; color: #999; font-size: 12px;">Valid for 15 minutes</p>
                        </div>
                        
                        <p style="color: #333; line-height: 1.6;">
                            If you didn't request this password reset, please ignore this email or contact support if you have concerns.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                        
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            This is an automated message, please do not reply to this email.
                        </p>
                    </div>
                </body>
            </html>
            """
        }
        
        response = resend.Emails.send(params)
        return True
    except Exception as e:
        error_msg = str(e)
        
        # Check if it's the Resend testing limitation
        if "You can only send testing emails" in error_msg:
            # Return a special error code
            return "RESEND_LIMIT"
        
        import traceback
        traceback.print_exc()
        return False

# Removed old get_db() function - now using database.py


def can_access_manage_users_actions():
    """Same as /manage_users: admin, or loan officer with manage_users permission."""
    if not current_user.is_authenticated:
        return False
    if current_user.role == 'admin':
        return True
    if current_user.role == 'loan_officer' and has_permission(current_user, 'manage_users'):
        return True
    return False


def init_db():
    """Initialize database if it doesn't exist (SQLite only - PostgreSQL uses migrations)"""
    db_type = get_database_type()
    
    if db_type == 'postgresql':
        # PostgreSQL is already initialized via migration
        print("📊 Using PostgreSQL - database already initialized")
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('signatures', exist_ok=True)
        return
    
    # SQLite initialization
    if not os.path.exists('app.db'):
        print("📊 Initializing SQLite database...")
        conn = get_db()
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())
        
        # Create demo users (all approved by default)
        from werkzeug.security import generate_password_hash
        admin_hash = generate_password_hash('admin123')
        loan_hash = generate_password_hash('loan123')
        ci_hash = generate_password_hash('ci123')
        
        conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
                     ('admin@dccco.test', admin_hash, 'Admin User', 'admin', 1))
        conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
                     ('loan@dccco.test', loan_hash, 'Loan Staff', 'loan_staff', 1))
        conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
                     ('ci@dccco.test', ci_hash, 'CI Staff', 'ci_staff', 1))
        
        conn.commit()
        conn.close()
        print("✓ SQLite database initialized")
        
    # Create directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('signatures', exist_ok=True)


def ensure_performance_indexes():
    """Create indexes for login, dashboards, and high-traffic actions."""
    try:
        conn = get_db()
        statements = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_role_approved_workload ON users(role, is_approved, current_workload)",
            "CREATE INDEX IF NOT EXISTS idx_users_approved_role_name ON users(is_approved, role, name)",
            "CREATE INDEX IF NOT EXISTS idx_loan_applications_status_submitted_at ON loan_applications(status, submitted_at)",
            "CREATE INDEX IF NOT EXISTS idx_loan_applications_assigned_ci_staff ON loan_applications(assigned_ci_staff)",
            "CREATE INDEX IF NOT EXISTS idx_loan_applications_submitted_by ON loan_applications(submitted_by)",
            "CREATE INDEX IF NOT EXISTS idx_loan_applications_member_name ON loan_applications(member_name)",
            "CREATE INDEX IF NOT EXISTS idx_loan_applications_lower_member_name ON loan_applications(LOWER(member_name))",
            "CREATE INDEX IF NOT EXISTS idx_notifications_user_read_created ON notifications(user_id, is_read, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_documents_loan_uploaded ON documents(loan_application_id, uploaded_at)",
            "CREATE INDEX IF NOT EXISTS idx_messages_app_sent ON messages(loan_application_id, sent_at)",
            "CREATE INDEX IF NOT EXISTS idx_direct_messages_receiver_read_sent ON direct_messages(receiver_id, is_read, sent_at)",
            "CREATE INDEX IF NOT EXISTS idx_direct_messages_sender_receiver_sent ON direct_messages(sender_id, receiver_id, sent_at)",
            "CREATE INDEX IF NOT EXISTS idx_location_tracking_user_tracked ON location_tracking(user_id, tracked_at)",
            # ── admin_dashboard specific ──────────────────────────────────────
            # Covers the IN-process tab (submitted / assigned_to_ci) quickly.
            "CREATE INDEX IF NOT EXISTS idx_loan_app_submitted_at_asc ON loan_applications(submitted_at ASC)",
            # Covers the direct-submission OR branch: needs_ci_interview=0 AND status='submitted'.
            # PostgreSQL partial indexes are ignored by SQLite but harmless.
            "CREATE INDEX IF NOT EXISTS idx_loan_app_direct_submit ON loan_applications(submitted_at) WHERE needs_ci_interview = 0 AND status = 'submitted'",
            # Partial index for each status that admin review tab queries.
            "CREATE INDEX IF NOT EXISTS idx_loan_app_ci_completed ON loan_applications(submitted_at) WHERE status = 'ci_completed'",
            # users.role lookup (CI staff widget and role-based queries everywhere).
            "CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)",
            # Notification count: user_id+is_read already covered; add message prefix
            # as a separate leading-char index isn't possible for LIKE '%...%', but
            # the existing composite index narrows the set enough.  Add a covering
            # index so the COUNT needs no heap fetch.
            "CREATE INDEX IF NOT EXISTS idx_notif_user_read_msg ON notifications(user_id, is_read, message)",
            # ── messages (internal loan-application thread) ────────────────────
            "CREATE INDEX IF NOT EXISTS idx_messages_receiver_read ON messages(receiver_id, is_read)",
            # ── direct_messages bilateral history query ────────────────────────
            # Speeds up the chat_with_user pair query (sender+receiver in both directions).
            "CREATE INDEX IF NOT EXISTS idx_dm_sender_receiver ON direct_messages(sender_id, receiver_id, sent_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_dm_receiver_sender ON direct_messages(receiver_id, sender_id, sent_at DESC)",
            # ── loan_applications assigned_ci_staff + status (ci_dashboard) ───
            "CREATE INDEX IF NOT EXISTS idx_loan_app_ci_status ON loan_applications(assigned_ci_staff, status, submitted_at)",
            # ── loan_applications submitted_by + status (loan_dashboard) ───────
            "CREATE INDEX IF NOT EXISTS idx_loan_app_by_status ON loan_applications(submitted_by, status, submitted_at)",
            # ── system_activity_log (system_settings page) ────────────────────
            # Primary sort column; makes LIMIT 50/200 ORDER BY fast.
            "CREATE INDEX IF NOT EXISTS idx_sys_log_created ON system_activity_log(created_at DESC)",
            # Covering index for the 3 DISTINCT filter-dropdown queries.
            "CREATE INDEX IF NOT EXISTS idx_sys_log_role ON system_activity_log(role)",
            "CREATE INDEX IF NOT EXISTS idx_sys_log_full_name ON system_activity_log(full_name)",
            "CREATE INDEX IF NOT EXISTS idx_sys_log_action ON system_activity_log(action)",
            # ── sms_sent_log (manage_sms_templates page) ──────────────────────
            "CREATE INDEX IF NOT EXISTS idx_sms_log_sent_at ON sms_sent_log(sent_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sms_log_sent_by ON sms_sent_log(sent_by_user_id)",
            # ── sms_templates ────────────────────────────────────────────────
            "CREATE INDEX IF NOT EXISTS idx_sms_tpl_category ON sms_templates(category)",
            "CREATE INDEX IF NOT EXISTS idx_sms_tpl_active ON sms_templates(is_active)",
            # ── user_login_sessions ──────────────────────────────────────────
            # Already has user_id as PRIMARY KEY (PK lookup is O(1)); no extra index needed.
            # Composite for the session-enforce SELECT that filters on session_token too.
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_token ON user_login_sessions(user_id, session_token)",
            # ── notifications additional covering indexes ───────────────────
            "CREATE INDEX IF NOT EXISTS idx_notif_user_created ON notifications(user_id, created_at DESC)",
        ]
        for statement in statements:
            conn.execute(statement)
        conn.commit()
        conn.close()
        print("✓ Performance indexes ensured")
    except Exception as e:
        print(f"⚠️  Performance index warning: {e}")


def ensure_direct_message_columns():
    """Backfill direct_messages columns required by messaging UI/APIs."""
    try:
        conn = get_db()
        db_type = get_database_type()

        if db_type == 'sqlite':
            existing_cols = set()
            rows = conn.execute("PRAGMA table_info(direct_messages)").fetchall()
            for row in rows:
                col_name = row['name'] if isinstance(row, dict) or hasattr(row, 'keys') else row[1]
                existing_cols.add(col_name)

            if 'is_deleted' not in existing_cols:
                conn.execute("ALTER TABLE direct_messages ADD COLUMN is_deleted INTEGER DEFAULT 0")
            if 'is_edited' not in existing_cols:
                conn.execute("ALTER TABLE direct_messages ADD COLUMN is_edited INTEGER DEFAULT 0")
            if 'edited_at' not in existing_cols:
                conn.execute("ALTER TABLE direct_messages ADD COLUMN edited_at TEXT")
        else:
            conn.execute("ALTER TABLE direct_messages ADD COLUMN IF NOT EXISTS is_deleted INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE direct_messages ADD COLUMN IF NOT EXISTS is_edited INTEGER DEFAULT 0")
            conn.execute("ALTER TABLE direct_messages ADD COLUMN IF NOT EXISTS edited_at TIMESTAMP")

        conn.commit()
        conn.close()
        print("✓ direct_messages columns ensured")
    except Exception as e:
        print(f"⚠️  direct_messages migration warning: {e}")


def ensure_users_columns():
    """Backfill optional columns on the users table (e.g. permissions) on both DBs."""
    try:
        conn = get_db()
        db_type = get_database_type()

        if db_type == 'sqlite':
            rows = conn.execute("PRAGMA table_info(users)").fetchall()
            existing = set()
            for row in rows:
                col_name = row['name'] if hasattr(row, 'keys') else row[1]
                existing.add(col_name)
            if 'permissions' not in existing:
                conn.execute("ALTER TABLE users ADD COLUMN permissions TEXT")
            if 'backup_email' not in existing:
                conn.execute("ALTER TABLE users ADD COLUMN backup_email TEXT")
            if 'profile_photo' not in existing:
                conn.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
            if 'signature_path' not in existing:
                conn.execute("ALTER TABLE users ADD COLUMN signature_path TEXT")
            if 'assigned_route' not in existing:
                conn.execute("ALTER TABLE users ADD COLUMN assigned_route TEXT")
            if 'approval_type' not in existing:
                conn.execute("ALTER TABLE users ADD COLUMN approval_type TEXT")
            if 'current_workload' not in existing:
                conn.execute("ALTER TABLE users ADD COLUMN current_workload INTEGER DEFAULT 0")
        else:
            for col, ddl in (
                ('permissions', 'TEXT'),
                ('backup_email', 'TEXT'),
                ('profile_photo', 'TEXT'),
                ('signature_path', 'TEXT'),
                ('assigned_route', 'TEXT'),
                ('approval_type', 'TEXT'),
                ('current_workload', 'INTEGER DEFAULT 0'),
            ):
                conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {ddl}")

        conn.commit()
        conn.close()
        print("✓ users columns ensured")
    except Exception as e:
        print(f"⚠️  users columns migration warning: {e}")


_sms_templates_table_ready = False


def ensure_sms_templates_table():
    """Create sms_templates table in a DB-compatible way."""
    global _sms_templates_table_ready
    if _sms_templates_table_ready:
        return
    try:
        conn = get_db()
        db_type = get_database_type()
        if db_type == 'postgresql':
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sms_templates (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('approved', 'disapproved', 'deferred', 'custom')),
                    message TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('ALTER TABLE sms_templates ADD COLUMN IF NOT EXISTS is_active INTEGER DEFAULT 1')
        else:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sms_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('approved', 'disapproved', 'deferred', 'custom')),
                    message TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # SQLite fallback for existing tables missing is_active.
            cols = conn.execute("PRAGMA table_info(sms_templates)").fetchall()
            col_names = {c['name'] if hasattr(c, 'keys') else c[1] for c in cols}
            if 'is_active' not in col_names:
                conn.execute('ALTER TABLE sms_templates ADD COLUMN is_active INTEGER DEFAULT 1')
        conn.commit()
        conn.close()
        _sms_templates_table_ready = True
        print("✓ sms_templates table ensured")
    except Exception as e:
        print(f"⚠️  sms_templates migration warning: {e}")


_sms_sent_log_table_ready = False


def ensure_sms_sent_log_table():
    """Store outgoing SMS for audit, search, and support."""
    global _sms_sent_log_table_ready
    if _sms_sent_log_table_ready:
        return
    try:
        conn = get_db()
        db_type = get_database_type()
        if db_type == 'postgresql':
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sms_sent_log (
                    id SERIAL PRIMARY KEY,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    phone_number TEXT NOT NULL,
                    message_body TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_detail TEXT,
                    loan_application_id INTEGER,
                    sent_by_user_id INTEGER,
                    category TEXT,
                    template_id INTEGER,
                    member_name TEXT
                )
            ''')
        else:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sms_sent_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    phone_number TEXT NOT NULL,
                    message_body TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_detail TEXT,
                    loan_application_id INTEGER,
                    sent_by_user_id INTEGER,
                    category TEXT,
                    template_id INTEGER,
                    member_name TEXT
                )
            ''')
        conn.commit()
        conn.close()
        _sms_sent_log_table_ready = True
        print("✓ sms_sent_log table ensured")
    except Exception as e:
        print(f"⚠️  sms_sent_log migration warning: {e}")


def _persist_sms_sent_log(
    phone,
    message_body,
    status,
    error_detail=None,
    loan_application_id=None,
    sent_by_user_id=None,
    category=None,
    template_id=None,
    member_name=None,
):
    """Best-effort row insert; does not raise (logging must not break sends)."""
    try:
        ensure_sms_sent_log_table()
        conn = get_db()
        conn.execute(
            '''
            INSERT INTO sms_sent_log (
                phone_number, message_body, status, error_detail,
                loan_application_id, sent_by_user_id, category, template_id, member_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                phone or '',
                message_body or '',
                status,
                error_detail,
                loan_application_id,
                sent_by_user_id,
                category,
                template_id,
                member_name,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.exception("sms_sent_log insert failed: %s", e)


_system_activity_log_table_ready = False


def ensure_system_activity_log_table():
    """Create system activity log table used by System Settings -> Recent Logs."""
    global _system_activity_log_table_ready
    if _system_activity_log_table_ready:
        return
    try:
        conn = get_db()
        db_type = get_database_type()
        if db_type == 'postgresql':
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS system_activity_log (
                    id SERIAL PRIMARY KEY,
                    role TEXT,
                    full_name TEXT,
                    action TEXT NOT NULL,
                    actor_user_id INTEGER,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            try:
                conn.execute(
                    'ALTER TABLE system_activity_log ADD COLUMN IF NOT EXISTS actor_user_id INTEGER'
                )
                conn.execute(
                    'ALTER TABLE system_activity_log ADD COLUMN IF NOT EXISTS metadata TEXT'
                )
            except Exception:
                pass
            conn.commit()
        else:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS system_activity_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT,
                    full_name TEXT,
                    action TEXT NOT NULL,
                    actor_user_id INTEGER,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            conn.commit()
            # Migrate older SQLite installs that lacked actor_user_id/metadata.
            try:
                col_rows = conn.execute('PRAGMA table_info(system_activity_log)').fetchall()
                existing_cols = set()
                for cr in col_rows:
                    nm = (
                        cr['name']
                        if isinstance(cr, dict) or hasattr(cr, 'keys')
                        else cr[1]
                    )
                    existing_cols.add(nm)
                if 'actor_user_id' not in existing_cols:
                    conn.execute(
                        'ALTER TABLE system_activity_log ADD COLUMN actor_user_id INTEGER'
                    )
                if 'metadata' not in existing_cols:
                    conn.execute(
                        'ALTER TABLE system_activity_log ADD COLUMN metadata TEXT'
                    )
                conn.commit()
            except Exception as mig_exc:
                app.logger.debug('system_activity_log column migrate: %s', mig_exc)
        conn.close()
        _system_activity_log_table_ready = True
        print("✓ system_activity_log table ensured")
    except Exception as e:
        print(f"⚠️  system_activity_log migration warning: {e}")


def ensure_user_login_sessions_table():
    """Track one active authenticated session per user for security."""
    try:
        conn = get_db()
        db_type = get_database_type()
        if db_type == 'postgresql':
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS user_login_sessions (
                    user_id INTEGER PRIMARY KEY,
                    session_token TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
        else:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS user_login_sessions (
                    user_id INTEGER PRIMARY KEY,
                    session_token TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
        conn.commit()
        conn.close()
        print("✓ user_login_sessions table ensured")
    except Exception as e:
        print(f"⚠️  user_login_sessions migration warning: {e}")


def _log_system_activity(role, full_name, action, actor_user_id=None, metadata=None):
    """Best-effort insert of an activity row. Never raises."""
    try:
        ensure_system_activity_log_table()
        conn = get_db()
        metadata_text = None
        if metadata is not None:
            try:
                metadata_text = json.dumps(metadata, default=str, ensure_ascii=False)
            except Exception:
                metadata_text = str(metadata)
        conn.execute(
            '''
            INSERT INTO system_activity_log (role, full_name, action, actor_user_id, metadata)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                (role or '').strip() or None,
                (full_name or '').strip() or None,
                (action or '').strip() or 'SYSTEM',
                actor_user_id,
                metadata_text,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        app.logger.debug("system_activity_log insert skipped: %s", e)


# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")
    print("⚠️  Continuing app startup...")

ensure_performance_indexes()
ensure_direct_message_columns()
ensure_users_columns()
ensure_sms_templates_table()
ensure_sms_sent_log_table()
ensure_system_activity_log_table()
ensure_user_login_sessions_table()
ensure_ci_coverage_routes_table()
ensure_ci_offline_packages_table()
ensure_documents_blob_columns()


# ── Asset minification / bundling ────────────────────────────────────────────
def _build_minified_assets():
    """
    Minify CSS and bundle+minify JS at startup using pure-Python rcssmin/rjsmin.
    Outputs land in static/css/ and static/js/ so WhiteNoise serves them with
    the same 1-day cache headers as all other static files.
    Falls back silently if the packages are not yet installed.
    """
    try:
        import rcssmin as _rcss
        import rjsmin as _rjs
    except ImportError:
        print("⚠  rcssmin/rjsmin not installed — skipping asset minification (pip install rcssmin rjsmin)")
        app.config['USE_MINIFIED_ASSETS'] = False
        return

    _static = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    os.makedirs(os.path.join(_static, 'js'), exist_ok=True)

    # ── CSS: minify individual files ─────────────────────────────────────────
    _css_pairs = [
        ('css/base.css', 'css/base.min.css'),
        ('ci-field.css', 'ci-field.min.css'),
    ]
    _css_ok = False
    for src_rel, dst_rel in _css_pairs:
        src_path = os.path.join(_static, src_rel)
        if not os.path.exists(src_path):
            continue
        try:
            with open(src_path, 'r', encoding='utf-8') as _f:
                _raw = _f.read()
            _min = _rcss.cssmin(_raw, keep_bang_comments=False)
            dst_path = os.path.join(_static, dst_rel)
            with open(dst_path, 'w', encoding='utf-8') as _f:
                _f.write(_min)
            print(f"✓ CSS minified  {src_rel} → {dst_rel}  "
                  f"({len(_raw) // 1024}KB → {len(_min) // 1024}KB)")
            if src_rel == 'css/base.css':
                _css_ok = True
        except Exception as _e:
            print(f"⚠  CSS minify failed {src_rel}: {_e}")

    # ── JS: bundle + minify groups ───────────────────────────────────────────
    # Each bundle = (output_path_rel, [source_paths_rel_to_static])
    _js_bundles = [
        (
            'js/app-core.min.js',
            ['csrf-protection.js', 'session-security.js', 'tab-close-logout.js', 'offline-request-queue.js'],
        ),
        (
            'js/ci-pwa.min.js',
            ['indexeddb-manager.js', 'offline-sync.js'],
        ),
    ]
    _js_ok = False
    for dst_rel, src_rels in _js_bundles:
        parts = []
        for sr in src_rels:
            sp = os.path.join(_static, sr)
            if os.path.exists(sp):
                try:
                    with open(sp, 'r', encoding='utf-8') as _f:
                        parts.append(_f.read())
                except Exception:
                    pass
        if not parts:
            continue
        try:
            _raw = '\n;\n'.join(parts)
            _min = _rjs.jsmin(_raw, keep_bang_comments=False)
            dst_path = os.path.join(_static, dst_rel)
            with open(dst_path, 'w', encoding='utf-8') as _f:
                _f.write(_min)
            print(f"✓ JS bundled    {dst_rel}  "
                  f"({len(_raw) // 1024}KB → {len(_min) // 1024}KB)")
            if dst_rel == 'js/app-core.min.js':
                _js_ok = True
        except Exception as _e:
            print(f"⚠  JS bundle failed {dst_rel}: {_e}")

    # Signal to base.html which assets to serve.
    app.config['USE_MINIFIED_ASSETS'] = _css_ok and _js_ok
    if app.config['USE_MINIFIED_ASSETS']:
        print("✓ Minified assets active — base.html will use .min files")


_build_minified_assets()


# Setup production users (runs on every startup to ensure correct roles)
def setup_production_users():
    """Create or update default users"""
    try:
        conn = get_db()
        from werkzeug.security import generate_password_hash
        
        users = [
            ('superadmin@dccco.test', 'admin@2024', 'Super Admin', 'admin'),
            ('admin@dccco.test', 'admin123', 'Loan Officer', 'loan_officer'),
            ('ci@dccco.test', 'ci123', 'CI Staff', 'ci_staff'),
            ('loan@dccco.test', 'loan123', 'Loan Staff', 'loan_staff')
        ]
        
        for email, password, name, role in users:
            try:
                existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
                password_hash = generate_password_hash(password)
                
                if existing:
                    # Keep default accounts deterministic on every startup.
                    conn.execute('''
                        UPDATE users
                        SET name = ?, role = ?, password_hash = ?, is_approved = 1
                        WHERE email = ?
                    ''', (name, role, password_hash, email))
                else:
                    # Create new user
                    conn.execute('''
                        INSERT INTO users (email, password_hash, name, role, is_approved)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (email, password_hash, name, role))
            except Exception as user_error:
                print(f"⚠️  User setup warning for {email}: {user_error}")
                continue

        # Keep only approved default system accounts.
        allowed_emails = tuple(u[0] for u in users)
        placeholders = ','.join(['?'] * len(allowed_emails))
        conn.execute(f'''
            UPDATE users
            SET is_approved = 0
            WHERE email NOT IN ({placeholders})
        ''', allowed_emails)
        
        conn.commit()
        print("✓ Production users setup complete")
        
        # Setup default loan types if table is empty
        try:
            count = conn.execute('SELECT COUNT(*) as count FROM loan_types').fetchone()
            if count and count['count'] == 0:
                print("Setting up default DCCCO loan types...")
                loan_types = [
                    ('Agricultural with Chattel', 'Agricultural loan with chattel mortgage', 1),
                    ('Agricultural with REM', 'Agricultural loan with real estate mortgage', 1),
                    ('Agricultural w/o Collateral', 'Agricultural loan without collateral', 1),
                    ('Business with Chattel', 'Business loan with chattel mortgage', 1),
                    ('Business with REM', 'Business loan with real estate mortgage', 1),
                    ('Business w/o Collateral', 'Business loan without collateral', 1),
                    ('Multipurpose with Chattel', 'Multipurpose loan with chattel mortgage', 1),
                    ('Multipurpose with REM', 'Multipurpose loan with real estate mortgage', 1),
                    ('Multipurpose w/o Collateral', 'Multipurpose loan without collateral', 1),
                    ('Salary ATM - Dim', 'Salary loan via ATM', 1),
                    ('Salary MOA - Dim', 'Salary loan via MOA', 1),
                    ('Car Loan - Dim (surplus)', 'Car loan for surplus vehicles', 1),
                    ('Car Loan (Brand New) - Dim', 'Car loan for brand new vehicles', 1),
                    ('Back-to-back Loan', 'Back-to-back loan', 1),
                    ('Pension Loan', 'Pension loan', 1),
                    ('Hospitalization Loan', 'Hospitalization loan', 1),
                    ('Petty Cash Loan', 'Petty cash loan', 1),
                    ('Incentive Loan', 'Incentive loan', 1)
                ]
                
                inserted = 0
                for loan_name, description, is_active in loan_types:
                    try:
                        # SQLite schema uses name; older/PostgreSQL variants may use loan_name.
                        try:
                            conn.execute(
                                '''
                                INSERT INTO loan_types (name, description, is_active)
                                VALUES (?, ?, ?)
                                ''',
                                (loan_name, description, is_active),
                            )
                        except Exception:
                            conn.execute(
                                '''
                                INSERT INTO loan_types (loan_name, description, is_active)
                                VALUES (?, ?, ?)
                                ''',
                                (loan_name, description, is_active),
                            )
                        inserted += 1
                    except Exception as loan_error:
                        print(f"⚠️  Loan type warning for {loan_name}: {loan_error}")
                        continue
                
                conn.commit()
                print(f"✓ Created {inserted} default loan types")
        except Exception as loan_types_error:
            print(f"⚠️  Loan types setup warning: {loan_types_error}")
        
        # Setup default system settings if table is empty
        try:
            count = conn.execute('SELECT COUNT(*) as count FROM system_settings').fetchone()
            if count and count['count'] == 0:
                print("Setting up default system settings...")
                settings = [
                    ('company_name', ORG_FULL_NAME, 'Company name displayed in the system'),
                    ('max_loan_amount', '500000', 'Maximum loan amount allowed'),
                    ('min_loan_amount', '5000', 'Minimum loan amount allowed'),
                    ('default_interest_rate', '12', 'Default annual interest rate (%)'),
                    ('ci_required_threshold', '50000', 'Loan amount threshold requiring CI')
                ]
                
                for key, value, description in settings:
                    try:
                        conn.execute('''
                            INSERT INTO system_settings (setting_key, setting_value, description)
                            VALUES (?, ?, ?)
                        ''', (key, value, description))
                    except Exception as setting_error:
                        print(f"⚠️  Setting warning for {key}: {setting_error}")
                        continue
                
                conn.commit()
                print(f"✓ Created {len(settings)} default system settings")
        except Exception as settings_error:
            print(f"⚠️  System settings setup warning: {settings_error}")
        
        conn.close()
    except Exception as e:
        print(f"⚠️  Setup warning: {e}")
        import traceback
        traceback.print_exc()
        print("⚠️  Continuing app startup despite setup warnings...")

try:
    setup_production_users()
except Exception as e:
    print(f"⚠️  Production users setup failed: {e}")
    print("⚠️  App will continue without default users")

def create_notification(user_id, message, link=None):
    try:
        conn = get_db()
        conn.execute('INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)',
                     (user_id, message, link))
        conn.commit()
        conn.close()
        with _count_cache_lock:
            _notification_count_cache.pop(user_id, None)
        socketio.emit('new_notification', {'message': message}, room=str(user_id))
    except Exception as e:
        pass


def run_background_task(func, *args, **kwargs):
    """Run non-critical work in background so UI responses are immediate."""
    def _runner():
        try:
            func(*args, **kwargs)
        except Exception as task_error:
            print(f"⚠️  Background task failed: {task_error}")

    socketio.start_background_task(_runner)


def enqueue_notification(user_id, message, link=None):
    """Queue notification creation so endpoints stay fast."""
    run_background_task(create_notification, user_id, message, link)


def _request_client_ip():
    """Best-effort client IP extraction behind proxies/CDN."""
    forwarded = (request.headers.get('X-Forwarded-For') or '').strip()
    if forwarded:
        return forwarded.split(',')[0].strip()
    return (request.remote_addr or '').strip()


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00'))
    except Exception:
        try:
            return datetime.strptime(text, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None


def _is_session_stale(last_seen_value):
    last_seen_dt = _parse_dt(last_seen_value)
    if last_seen_dt is None:
        # Missing/unparsable last_seen must NOT force logout — common after migrations or clock quirks.
        # Valid tokens still pass enforce; after_request heartbeat refreshes last_seen on HTML responses.
        return False
    if last_seen_dt.tzinfo is not None:
        now_dt = datetime.now(last_seen_dt.tzinfo)
    else:
        now_dt = datetime.utcnow()
    return (now_dt - last_seen_dt).total_seconds() > _SINGLE_LOGIN_STALE_SECONDS


def _login_blocked_by_active_session(row) -> bool:
    """
    If True, a new login for this user must be rejected: the account still has an
    active server session (not signed out) and last activity is within the idle window.
    IP/User-Agent are not used to decide this—only session is_active + last_seen.
    When last_seen is past the idle limit, allow login to replace the row (reclaims
    abandoned sessions without a formal Log out).
    """
    if not row:
        return False
    try:
        is_active = int(row['is_active']) if row['is_active'] is not None else 0
    except (TypeError, ValueError, KeyError):
        is_active = 0
    if is_active != 1:
        return False
    ls = row['last_seen'] if 'last_seen' in row.keys() else None
    # Missing last_seen: reclaim row (same class as stale for sign-in-from-login-screen).
    if ls is None:
        return False
    if isinstance(ls, str) and not str(ls).strip():
        return False
    if _is_session_stale(ls):
        return False
    return True


def _upsert_user_session(conn, user_id, session_token):
    now_iso = now_ph().isoformat()
    conn.execute('''
        INSERT INTO user_login_sessions (user_id, session_token, is_active, ip_address, user_agent, created_at, last_seen)
        VALUES (?, ?, 1, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            session_token=excluded.session_token,
            is_active=1,
            ip_address=excluded.ip_address,
            user_agent=excluded.user_agent,
            last_seen=excluded.last_seen
    ''', (
        user_id,
        session_token,
        _request_client_ip(),
        (request.headers.get('User-Agent') or '')[:255],
        now_iso,
        now_iso,
    ))


def _touch_user_session(user_id, session_token):
    try:
        conn = get_db()
        conn.execute(
            '''
            UPDATE user_login_sessions
            SET last_seen=?
            WHERE user_id=? AND session_token=? AND is_active=1
            ''',
            (
                now_ph().isoformat(),
                user_id,
                session_token,
            ),
        )
        conn.commit()
        if not has_request_context():
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass


def _deactivate_user_session(user_id, session_token=None):
    try:
        conn = get_db()
        if session_token:
            conn.execute(
                'UPDATE user_login_sessions SET is_active=0, last_seen=? WHERE user_id=? AND session_token=?',
                (now_ph().isoformat(), user_id, session_token),
            )
        else:
            conn.execute(
                'UPDATE user_login_sessions SET is_active=0, last_seen=? WHERE user_id=?',
                (now_ph().isoformat(), user_id),
            )
        conn.commit()
        if not has_request_context():
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        pass


def _maybe_send_security_alert(user_id, message, link='/notifications'):
    """Throttle security alerts to avoid notification spam."""
    now_ts = time.time()
    try:
        with _count_cache_lock:
            last_ts = _security_alert_cache.get(user_id, 0)
            if now_ts - last_ts < _SECURITY_ALERT_TTL_SECONDS:
                return
            _security_alert_cache[user_id] = now_ts
        enqueue_notification(user_id, message, link)
    except Exception:
        pass


def _ph_number_for_semaphore(phone_number):
    """
    Semaphore expects Philippine mobiles like 09171234567 (11 digits, leading 0).
    Accepts +63, 63, 09, or 9XXXXXXXXX digit strings.
    """
    d = re.sub(r'\D', '', str(phone_number or ''))
    if not d:
        return None
    if d.startswith('63') and len(d) == 12 and d[2] == '9':
        return '0' + d[2:]
    if len(d) == 11 and d.startswith('09'):
        return d
    if len(d) == 10 and d[0] == '9':
        return '0' + d
    if d.startswith('09') and len(d) == 11:
        return d
    return None


# Cache Semaphore /account/sendernames to avoid rate limits (2/min) and to use approved senders
_SEMAPHORE_SENDERLIST_CACHE = {'t': 0.0, 'names': None, 'ttl': 0.0}


def _semaphore_v4_base_url():
    u = (os.getenv('SEMAPHORE_API_URL') or 'https://api.semaphore.co/api/v4/messages').strip().rstrip('/')
    if u.endswith('/messages'):
        return u[: -len('/messages')]
    return 'https://api.semaphore.co/api/v4'


def _parse_semaphore_sendernames_json(data):
    """Normalize GET /account/sendernames body into a list of sender name strings."""
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = (
            data.get('results')
            or data.get('data')
            or data.get('sendernames')
            or data.get('sender_names')
            or []
        )
        if not isinstance(rows, list):
            rows = []
    else:
        rows = []
    out = []
    for row in rows:
        if isinstance(row, str) and row.strip():
            n = row.strip()
            if n not in out:
                out.append(n)
            continue
        if not isinstance(row, dict):
            continue
        n = (row.get('name') or row.get('sender_name') or '').strip()
        if not n:
            continue
        st = (row.get('status') or '').strip().lower()
        if st in ('rejected', 'denied', 'suspended', 'banned', 'refused'):
            continue
        if n not in out:
            out.append(n)
    return out


def _fetch_semaphore_account_sender_names(api_key):
    """
    Names registered on the Semaphore account (API order). Short TTL cache on success;
    on failure, short cache to avoid hammering the rate-limited endpoint.
    """
    now = time.time()
    c = _SEMAPHORE_SENDERLIST_CACHE
    if c['names'] is not None and (now - c['t']) < c['ttl']:
        return c['names'][:]

    url = f"{_semaphore_v4_base_url().rstrip('/')}/account/sendernames"
    try:
        r = requests.get(url, params={'apikey': api_key, 'limit': 100, 'page': 1}, timeout=8)
        if r.status_code != 200:
            print(f"[SMS] Semaphore sendernames HTTP {r.status_code}: {(r.text or '')[:200]}")
            names = []
            c['t'] = now
            c['ttl'] = 60.0
            c['names'] = names
            return names[:]
        data = r.json()
        names = _parse_semaphore_sendernames_json(data)
        print(f"[SMS] Semaphore account sender names ({len(names)}): {names[:5]}{'...' if len(names) > 5 else ''}")
        c['t'] = now
        c['ttl'] = 300.0
        c['names'] = names
        return names[:]
    except Exception as ex:
        print(f"[SMS] Semaphore sendernames fetch error: {ex}")
        c['t'] = now
        c['ttl'] = 60.0
        c['names'] = []
        return []


def _build_semaphore_sender_candidates(api_key):
    """
    Build ordered sendername attempts. Prefer env overrides, then names from Semaphore API
    (so we match whatever is actually approved in the dashboard), then optional fallbacks.
    Do not default to a hardcoded org name (e.g. DCCCO) — that often is not the approved sender.
    """
    seen = set()
    out = []

    def _add(s):
        if s in seen:
            return
        seen.add(s)
        out.append(s)

    cfg = (
        (os.getenv('SEMAPHORE_SENDERNAME') or '')
        or (os.getenv('SEMAPHORE_SENDER_NAME') or '')
        or (os.getenv('SMS_SENDER_NAME') or '')
    ).strip()
    if cfg:
        _add(cfg)
    for part in re.split(r'[,;]+', (os.getenv('SEMAPHORE_SENDER_CANDIDATES') or '')):
        p = part.strip()
        if p:
            _add(p)
    for n in _fetch_semaphore_account_sender_names(api_key):
        _add(n)
    dash = (os.getenv('SEMAPHORE_DASHBOARD_SENDER') or '').strip()
    if dash:
        _add(dash)
    # API docs: omitting sendername defaults to branded "Semaphore"; explicit sometimes matches account
    _add('SEMAPHORE')
    _add('')
    return out


def _send_sms_semaphore(phone_09, send_body_for_log):
    """
    POST to Semaphore API. phone_09 must be 09xxxxxxxxx.
    """
    api_key = (os.getenv('SEMAPHORE_API_KEY') or os.getenv('SMS_API_KEY') or '').strip()
    if not api_key:
        return False, 'SEMAPHORE_API_KEY is not set in the server environment'

    # Semaphore silently drops messages that start with "TEST"
    if send_body_for_log.lstrip().upper().startswith('TEST'):
        return False, 'Message cannot start with TEST (ignored by provider)'

    # Official host (doc); legacy semaphore.co also works, api.semaphore.co is canonical
    url = (os.getenv('SEMAPHORE_API_URL') or 'https://api.semaphore.co/api/v4/messages').strip()
    sender_candidates = _build_semaphore_sender_candidates(api_key)

    payload = {
        'apikey': api_key,
        'number': phone_09,
        'message': send_body_for_log,
    }

    def _extract_semaphore_error(response, data, text):
        if isinstance(data, dict):
            return data.get('message') or data.get('error') or str(data)[:500]
        return text[:500] or f'HTTP {response.status_code}'

    def _looks_like_sender_rejection(err):
        low = (err or '').lower()
        return (
            'sender' in low
            or 'sendername' in low
            or 'sender name' in low
            or 'not yet been approved for sending messages' in low
            or 'not yet approved for sending sms' in low
            or 'complete your account profile' in low
            or 'not verified' in low
            or 'unverified' in low
            or 'verify your account' in low
            or 'account must' in low
            or 'must verify' in low
            or 'kyc' in low
        )

    try:
        timeout = float(os.getenv('SEMAPHORE_TIMEOUT_SECONDS', '10'))

        def _attempt(send_payload, label):
            print(f"[SMS] Semaphore → {phone_09} ({label})")
            response = requests.post(url, data=send_payload, timeout=timeout)
            text = (response.text or '').strip()
            try:
                data = response.json()
            except Exception:
                err = f'HTTP {response.status_code}: {text[:500]}'
                print(f"✗ Semaphore non-JSON: {err}")
                return False, err

            if response.status_code >= 400:
                err = _extract_semaphore_error(response, data, text)
                print(f"✗ Semaphore HTTP {response.status_code}: {err}")
                return False, str(err)

            # Success payload is usually a one-element list
            if isinstance(data, list) and len(data) == 0:
                return False, 'Empty response from Semaphore'
            if isinstance(data, dict) and 'message_id' not in data:
                err = data.get('message') or data.get('error')
                if err:
                    return False, str(err)[:500]
            row = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
            if not row:
                return False, 'Unexpected Semaphore response'
            st = (row.get('status') or '').strip().lower() if row else ''
            if st == 'failed':
                err = row.get('message') or 'Semaphore status Failed'
                print(f"✗ Semaphore failed: {row}")
                return False, str(err)[:500]

            print(f"✓ Semaphore accepted: {row.get('message_id', row)} status={row.get('status')}")
            return True, None

        last_err = None
        for sender in sender_candidates:
            attempt_payload = dict(payload)
            if sender:
                attempt_payload['sendername'] = sender

            ok, err = _attempt(
                attempt_payload,
                f"sender={sender}" if sender else "default sender",
            )
            if ok:
                return True, None

            last_err = err
            if not _looks_like_sender_rejection(err):
                break
            print("[SMS] Retrying Semaphore with next sender option.")

        return False, last_err
    except requests.RequestException as e:
        err = str(e)
        print(f"✗ Semaphore request error: {err}")
        return False, err


def _send_sms_textbelt(phone, send_body, log_phone):
    """Legacy fallback when Semaphore is not configured."""
    url = 'https://textbelt.com/text'
    payload = {'phone': phone, 'message': send_body, 'key': (os.getenv('TEXTBELT_API_KEY') or 'textbelt')}
    try:
        timeout = float(os.getenv('TEXTBELT_TIMEOUT_SECONDS', '5'))
        response = requests.post(url, data=payload, timeout=timeout)
        result = response.json()
    except (requests.RequestException, ValueError) as e:
        return False, str(e)
    print(f"[SMS] TextBelt Response: {result}")
    if result.get('success'):
        return True, None
    return False, str(result.get('error', 'Unknown error'))


def _can_fallback_to_textbelt(semaphore_error):
    """
    Decide whether a Semaphore failure should try TextBelt fallback.
    Do not fallback for obvious input/content validation errors.
    """
    err = (semaphore_error or '').strip().lower()
    if not err:
        return False
    blocked_markers = (
        'message cannot start with test',
        'could not parse philippine mobile number',
        'invalid or empty phone number',
        'not yet been approved for sending messages',
        'not yet approved for sending sms',
        'http 403',
    )
    return not any(marker in err for marker in blocked_markers)


def _friendly_sms_error(raw_error):
    """Normalize provider errors into a concise operator-friendly message."""
    err = (raw_error or '').strip()
    low = err.lower()

    def _dedupe_chunks(text):
        # Remove duplicate repeated chunks from provider messages.
        normalized = (text or '').replace('\n', ' ').strip()
        if not normalized:
            return ''
        tokens = [t.strip() for t in re.split(r'[;]+', normalized) if t.strip()]
        seen = set()
        out = []
        for t in tokens:
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(t)
        collapsed = '; '.join(out)
        if len(collapsed) <= 500:
            return collapsed
        return collapsed[:500]

    if not err:
        return 'SMS could not be sent.'
    if (
        'not yet been approved for sending messages' in low
        or 'not yet approved for sending sms' in low
        or 'complete your account profile' in low
    ):
        return (
            'Semaphore account or sender name is not approved for API sending. '
            'In Semaphore → Sender Names, use the exact approved name as '
            'SEMAPHORE_SENDER_NAME (Render env) or SEMAPHORE_SENDER_CANDIDATES, '
            'or complete account verification in the Semaphore dashboard.'
        )
    if (
        'sender' in low
        and (
            'not verified' in low
            or 'unapproved' in low
            or 'not approved' in low
        )
    ):
        return (
            'Semaphore rejected the sender ID for this message. Set '
            'SEMAPHORE_SENDER_NAME to match your approved Sender Name in Semaphore, '
            'or add SEMAPHORE_SENDER_CANDIDATES=Name1,Name2 in environment.'
        )
    if 'free sms are disabled for this country' in low:
        return 'Fallback SMS provider is unavailable for this country.'
    if 'invalid or empty phone number' in low or 'could not parse philippine mobile number' in low:
        return 'Invalid member mobile number format.'
    return _dedupe_chunks(err)


def send_sms(phone_number, message, **log_ctx):
    """
    Send SMS: Semaphore (Philippines) when SEMAPHORE_API_KEY is set, else TextBelt fallback.
    Optional log_ctx: loan_application_id, sent_by_user_id, category, template_id, member_name
    Returns (success: bool, error_message: str | None).
    """
    loan_application_id = log_ctx.get('loan_application_id')
    sent_by_user_id = log_ctx.get('sent_by_user_id')
    category = log_ctx.get('category')
    template_id = log_ctx.get('template_id')
    member_name = log_ctx.get('member_name')

    def _log(status, error_detail, body, dest_phone):
        _persist_sms_sent_log(
            dest_phone,
            body,
            status,
            error_detail=error_detail,
            loan_application_id=loan_application_id,
            sent_by_user_id=sent_by_user_id,
            category=category,
            template_id=template_id,
            member_name=member_name,
        )

    try:
        phone = re.sub(r'[^\d+]', '', str(phone_number or ''))
        if phone.startswith('09') and len(phone) == 11:
            phone = '+63' + phone[1:]
        elif not phone.startswith('+'):
            if len(phone) == 10:
                phone = '+63' + phone
            else:
                phone = '+' + phone

        send_body = f"DCCCO: {message}"

        if not phone or len(phone) < 8:
            _log('failed', 'Invalid or empty phone number', send_body, phone or str(phone_number or ''))
            return False, 'Invalid or empty phone number'

        print(f"\n[SMS] Attempting to send to {phone}")
        print(f"[SMS] Message: {message[:50]}...")

        use_sem = bool((os.getenv('SEMAPHORE_API_KEY') or os.getenv('SMS_API_KEY') or '').strip())
        ph09 = _ph_number_for_semaphore(phone_number) or _ph_number_for_semaphore(phone)

        try:
            if use_sem and ph09:
                ok, err = _send_sms_semaphore(ph09, send_body)
                if ok:
                    _log('success', None, send_body, phone)
                    return True, None

                if _can_fallback_to_textbelt(err):
                    print(f"[SMS] Semaphore failed, trying TextBelt fallback. reason={err}")
                    tb_ok, tb_err = _send_sms_textbelt(phone, send_body, phone)
                    if tb_ok:
                        _log('success', f"Semaphore failed then TextBelt sent: {err}", send_body, phone)
                        return True, None
                    combined_err = f"Semaphore: {err}; TextBelt: {tb_err}"
                    friendly = _friendly_sms_error(combined_err)
                    _log('failed', friendly, send_body, phone)
                    return False, friendly

                friendly = _friendly_sms_error(err)
                _log('failed', friendly, send_body, phone)
                return False, friendly
            if use_sem and not ph09:
                msg = 'Could not parse Philippine mobile number (use 09XX XXX XXXX or +63...)'
                print(f"✗ {msg} raw={phone_number!r}")
                friendly = _friendly_sms_error(msg)
                _log('failed', friendly, send_body, phone)
                return False, friendly

            # No Semaphore key: try TextBelt on international-style number
            print("[SMS] No SEMAPHORE_API_KEY — using TextBelt (limited free tier)")
            ok, err = _send_sms_textbelt(phone, send_body, phone)
            if ok:
                _log('success', None, send_body, phone)
                return True, None
            friendly = _friendly_sms_error(err)
            _log('failed', friendly, send_body, phone)
            return False, friendly

        except Exception as e:
            print(f"✗ SMS provider exception: {str(e)}")
            import traceback
            traceback.print_exc()
            friendly = _friendly_sms_error(str(e))
            _log('failed', friendly, send_body, phone)
            return False, friendly

    except Exception as e:
        print(f"✗ SMS error: {str(e)}")
        import traceback
        traceback.print_exc()
        try:
            body = f"DCCCO: {message}"
        except Exception:
            body = ''
        friendly = _friendly_sms_error(str(e))
        _log('failed', friendly, body, str(phone_number or ''))
        return False, friendly


def send_bulk_sms(phone_numbers, message, sent_by_user_id=None):
    """
    Send to a comma- or newline-separated list of numbers; each attempt is logged.
    Returns counts for the API response.
    """
    raw = phone_numbers
    if isinstance(raw, (list, tuple)):
        parts = [str(x).strip() for x in raw if str(x).strip()]
    else:
        s = str(raw or '')
        parts = re.split(r'[\s,;]+', s)
        parts = [p.strip() for p in parts if p.strip()]

    ok = 0
    for num in parts:
        s_ok, _ = send_sms(num, message, sent_by_user_id=sent_by_user_id, category='bulk')
        if s_ok:
            ok += 1

    return {'success': ok, 'total': len(parts), 'failed': len(parts) - ok}

def build_system_context():
    """
    Build comprehensive system context for AI assistant
    Includes database schema, routes, features, and workflows
    """
    context = """
# DCCCO Loan Management System Documentation

## System Overview
Flask-based loan management system for DCCCO Multipurpose Cooperative with real-time features using Socket.IO.

## User Roles
1. *admin*: Full system access, approves/rejects loans, manages users
2. *loan_staff*: Submits loan applications, assigns to CI staff
3. *ci_staff*: Conducts credit investigations, completes checklists

## Database Schema

### users table
- id, email, password_hash, name, role, is_approved
- signature_path, backup_email, profile_photo
- is_online, last_seen, current_workload

### loan_applications table
- id, member_name, member_contact, member_address, loan_amount
- status: submitted, assigned_to_ci, ci_completed, approved, disapproved
- needs_ci_interview, submitted_by, assigned_ci_staff
- ci_notes, ci_checklist_data, ci_signature, ci_completed_at
- admin_notes, admin_decision_at, submitted_at

### documents table
- id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at

### direct_messages table
- id, sender_id, receiver_id, message, sent_at, is_read, is_edited, is_deleted

### notifications table
- id, user_id, message, link, is_read, created_at

### location_tracking table
- id, user_id, latitude, longitude, activity, tracked_at

## Key Features

### Loan Application Workflow
1. Loan staff submits application via /loan/submit
2. System auto-assigns to CI staff with lowest workload
3. CI staff completes interview and checklist
4. Admin reviews and approves/rejects
5. SMS notification sent to applicant

### Real-Time Messaging
- Direct messages between users via Socket.IO
- Application-specific messaging threads
- Typing indicators and read receipts
- Voice message support

### CI Tracking
- GPS location tracking for CI staff
- Real-time map display for admin
- Activity status updates

### User Management
- Admin approves new user registrations
- Role-based access control
- Password reset with email verification

### Dark Mode
- Toggle via localStorage
- Applies to all pages
- CSS variables for theming

## Common Issues & Solutions

### Issue: User not approved
*Solution*: Admin must approve via /manage_users

### Issue: CI staff not receiving assignments
*Solution*: Check current_workload in users table, verify is_approved=1

### Issue: SMS not sending
*Solution*: Check SEMAPHORE_API_KEY or TEXTBELT_API_KEY in .env

### Issue: Real-time features not working
*Solution*: Verify Socket.IO connection, check browser console for errors

### Issue: File upload failing
*Solution*: Check UPLOAD_FOLDER permissions, verify file extension in ALLOWED_EXTENSIONS

## File Structure
- app.py: Main Flask application
- templates/: HTML templates (Jinja2)
- static/: CSS, JavaScript, images
- uploads/: User-uploaded documents
- signatures/: Digital signatures
- schema.sql: Database schema

## Environment Variables
- SECRET_KEY: Flask session secret
- RESEND_API_KEY: Email service
- SEMAPHORE_API_KEY: SMS service (primary)
- OPENAI_API_KEY or ANTHROPIC_API_KEY: AI assistant
- FLASK_DEBUG: Debug mode flag

## API Endpoints
- /api/send_direct_message: Send message
- /api/update_location: Update CI location
- /api/unread_message_count: Get unread count
- /api/ai_query: AI assistant query (admin only)
"""
    return context


def call_ai_engine(query, history, context):
    """
    Call AI API with system context and conversation history
    Supports OpenAI and Anthropic APIs
    """
    def _sync_ai_call():
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')

        if not openai_key and not anthropic_key:
            raise Exception(
                'No AI API key configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file.'
            )

        messages = []
        for msg in history:
            messages.append({'role': msg['role'], 'content': msg['content']})
        messages.append({'role': 'user', 'content': query})

        system_message = f"""You are DaisyandCoco, an AI assistant for the {ORG_FULL_NAME} ({ORG_ABBR}) loan management system.

You help administrators understand and troubleshoot the system.

SYSTEM KNOWLEDGE:
{context}

Provide clear, accurate, and helpful responses. Use bullet points and code examples when appropriate.
Reference specific file paths, database tables, and functions when relevant.
Be friendly and conversational while maintaining professionalism."""

        if openai_key:
            try:
                import openai

                client = openai.OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model='gpt-3.5-turbo',
                    messages=[{'role': 'system', 'content': system_message}] + messages,
                    max_tokens=1000,
                    temperature=0.7,
                )
                return response.choices[0].message.content
            except Exception as e:
                app.logger.error(f"OpenAI API error: {str(e)}")
                raise Exception(f"AI service error: {str(e)}") from e

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=1000,
                system=system_message,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            app.logger.error(f"Anthropic API error: {str(e)}")
            raise Exception(f"AI service error: {str(e)}") from e

    # OpenAI/Anthropic httpx stacks use asyncio; eventlet monkey-patching conflicts with asyncio.run().
    # Run the blocking SDK in a real OS thread via eventlet's thread pool.
    return eventlet.tpool.execute(_sync_ai_call)


@login_manager.user_loader
def load_user(user_id):
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    try:
        if has_request_context():
            if getattr(g, '_login_user_id', None) == uid and getattr(g, '_login_user_obj', None) is not None:
                return g._login_user_obj
        conn = get_db()
        try:
            row = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
            if not row:
                return None
            normalized_role = normalize_role(row['role'] if 'role' in row.keys() else None)
            source_role = row['role'] if 'role' in row.keys() else None
            effective_role = normalized_role or source_role or 'loan_staff'
            if normalized_role and normalized_role != source_role:
                try:
                    conn.execute('UPDATE users SET role=? WHERE id=?', (normalized_role, uid))
                    conn.commit()
                except Exception as role_update_error:
                    print(f"⚠️  Role normalization warning (user_loader): {role_update_error}")
            signature_path = row['signature_path'] if 'signature_path' in row.keys() else None
            backup_email = row['backup_email'] if 'backup_email' in row.keys() else None
            profile_photo = row['profile_photo'] if 'profile_photo' in row.keys() else None
            assigned_route = row['assigned_route'] if 'assigned_route' in row.keys() else None
            permissions = row['permissions'] if 'permissions' in row.keys() else None
            user = User(
                row['id'], row['email'], row['name'], effective_role, signature_path,
                backup_email, profile_photo, assigned_route, permissions,
            )
            if has_request_context():
                g._login_user_id = uid
                g._login_user_obj = user
            return user
        finally:
            # Keep request-scoped connection open: closing here forced a 2nd/3rd pool
            # checkout (before_request + view). Teardown closes once per request.
            if not has_request_context():
                try:
                    conn.close()
                except Exception:
                    pass
    except Exception as load_err:
        app.logger.exception('load_user failed: %s', load_err)
        return None


@app.errorhandler(500)
def handle_internal_server_error(e):
    """Prevent raw 500 pages and guide user back safely."""
    app.logger.exception('Unhandled server error: %s', e)
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.path.startswith('/api/')
        or request.is_json
    )
    if is_ajax:
        return jsonify({'success': False, 'error': 'server_error'}), 500
    flash('Temporary server issue detected. Please try again.', 'warning')
    try:
        # Never redirect in circles on auth/root endpoints.
        if request.path in ('/', '/login', '/logout'):
            return render_template('login.html'), 500
        return redirect(url_for('login'))
    except Exception:
        return 'Temporary server issue. Please reload.', 500

# Add security headers to prevent caching of authenticated pages (not /static/ JS/CSS)
@app.after_request
def add_security_headers(response):
    p = request.path or ''
    ep = request.endpoint
    static_asset = p.startswith('/static/') or ep in ('serve_static', 'favicon')
    if static_asset and 'Cache-Control' not in response.headers:
        # 1-day browser cache for static assets (WhiteNoise sets this independently;
        # this covers the Flask fallback route and favicon).
        response.headers['Cache-Control'] = 'public, max-age=86400, stale-while-revalidate=3600'

    if current_user.is_authenticated and not static_asset:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        # Discourage shared caches from serving one user’s HTML to another (belt-and-suspenders with no-store).
        if 'Vary' not in response.headers:
            response.headers['Vary'] = 'Cookie'
        # Touch active session heartbeat once per minute (skip on static-only responses to cut noise).
        try:
            now_ts = int(time.time())
            last_touch = int(session.get('_session_touch_ts', 0) or 0)
            if now_ts - last_touch >= _SESSION_TOUCH_MIN_SEC:
                auth_token = session.get('auth_session_token')
                if auth_token:
                    _touch_user_session(current_user.id, auth_token)
                session['_session_touch_ts'] = now_ts
        except Exception:
            pass

    # ── Global slow-request logger ──────────────────────────────────────────
    # Logs any HTML page that takes over 1 s so we can pinpoint bottlenecks.
    try:
        _start = getattr(g, '_req_start', None)
        if _start is not None and not static_asset:
            _elapsed = time.monotonic() - _start
            if _elapsed >= 1.0:
                _perf_logger.warning(
                    'SLOW %s %s → %s  %.3fs',
                    request.method, p, response.status_code, _elapsed,
                )
    except Exception:
        pass

    return response


@app.before_request
def _record_request_start():
    """Stamp every request so after_request can log slow ones."""
    g._req_start = time.monotonic()


@app.before_request
def enforce_single_active_login():
    """Ensure cookie matches the server's active session row (logout ends the session)."""
    if not current_user.is_authenticated:
        return None
    if _should_skip_session_enforce():
        return None

    auth_token = session.get('auth_session_token')
    if not auth_token:
        try:
            logout_user()
        except Exception:
            pass
        session.clear()
        flash('Please sign in again for security.', 'warning')
        return redirect(url_for('login'))

    # Same valid session: skip repeated user_login_sessions reads on back-to-back GET/HEAD (major nav perf win).
    if (
        _ENFORCE_GET_MIN_SEC > 0
        and request.method in ('GET', 'HEAD')
        and auth_token == session.get('_enforce_token_snap')
    ):
        try:
            last_ok = float(session.get('_enforce_last_get_ok', 0) or 0)
        except (TypeError, ValueError):
            last_ok = 0.0
        if (time.time() - last_ok) < _ENFORCE_GET_MIN_SEC:
            return None

    try:
        conn = get_db()
        row = conn.execute(
            '''
            SELECT session_token, is_active, last_seen
            FROM user_login_sessions
            WHERE user_id=?
            LIMIT 1
            ''',
            (current_user.id,),
        ).fetchone()
    except Exception:
        return None

    if not row:
        try:
            logout_user()
        except Exception:
            pass
        session.clear()
        flash('Session expired. Please log in again.', 'warning')
        return redirect(url_for('login'))

    is_active = int(row['is_active']) if 'is_active' in row.keys() and row['is_active'] is not None else 0
    token_match = str(row['session_token']) == str(auth_token)
    is_stale = _is_session_stale(row['last_seen'] if 'last_seen' in row.keys() else None)
    if not token_match or not is_active:
        try:
            logout_user()
        except Exception:
            pass
        session.clear()
        flash(
            'Your session is no longer valid (ended or replaced). Please sign in again.',
            'warning',
        )
        return redirect(url_for('login'))
    if is_stale:
        try:
            logout_user()
        except Exception:
            pass
        session.clear()
        flash('You were away for a while, so we signed you out to protect your account. Please sign in again when you are ready.', 'info')
        return redirect(url_for('login'))
    if _ENFORCE_GET_MIN_SEC > 0 and request.method in ('GET', 'HEAD'):
        session['_enforce_last_get_ok'] = str(time.time())
        session['_enforce_token_snap'] = auth_token
    return None


@app.teardown_request
def close_db_connection_on_request_end(exc):
    """Always return request-scoped DB connections to the pool."""
    try:
        db_conn = getattr(g, '_db_conn', None)
        if db_conn is not None:
            try:
                db_conn.close()
            finally:
                g._db_conn = None
    except Exception as close_err:
        app.logger.debug('teardown DB close skipped: %s', close_err)

# Helper functions for role-based access control
def is_admin():
    """Check if current user is super admin"""
    return current_user.is_authenticated and current_user.role == 'admin'

def is_loan_officer():
    """Check if current user is loan officer"""
    return current_user.is_authenticated and current_user.role == 'loan_officer'

def is_admin_or_loan_officer():
    """Check if current user is admin or loan officer"""
    return current_user.is_authenticated and current_user.role in ['admin', 'loan_officer']

def _user_can_access_application(user_id, role, app_id):
    """Role-aware authorization for a single loan application record."""
    if role in ['admin', 'loan_officer']:
        return True
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT submitted_by, assigned_ci_staff FROM loan_applications WHERE id=?',
            (app_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return False
    if role == 'loan_staff':
        return row['submitted_by'] == user_id
    if role == 'ci_staff':
        return row['assigned_ci_staff'] == user_id
    return False

def require_admin():
    """Decorator to require admin role"""
    if not is_admin():
        flash('Unauthorized - Admin access required', 'danger')
        return redirect(url_for('index'))

def require_admin_or_loan_officer():
    """Decorator to require admin or loan officer role"""
    if not is_admin_or_loan_officer():
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))


def _split_member_name(full_name):
    """Best-effort split for pre-filling CI applicant name fields."""
    if not full_name:
        return {'last': '', 'first': '', 'middle': ''}
    parts = [p for p in str(full_name).strip().split() if p]
    if len(parts) == 1:
        return {'last': parts[0], 'first': '', 'middle': ''}
    if len(parts) == 2:
        return {'last': parts[-1], 'first': parts[0], 'middle': ''}
    return {'last': parts[-1], 'first': parts[0], 'middle': ' '.join(parts[1:-1])}


def _sanitize_optional_ph_mobile_input(raw):
    """
    Philippine mobile numbers: exactly 11 digits, format 09XXXXXXXXX (e.g. 09751762630).
    Accepts spaces/dashes; normalizes +63/639… and plain 9XXXXXXXXX (10 digits) to 09…
    Returns '' if empty; normalized string if valid; None if invalid when non-empty.
    """
    text = (raw or '').strip()
    if not text:
        return ''
    d = ''.join(c for c in text if c.isdigit())
    if not d:
        return None
    if len(d) == 12 and d.startswith('63'):
        d = '0' + d[2:]
    elif len(d) == 10 and d.startswith('9'):
        d = '0' + d
    if len(d) == 11 and d.startswith('09'):
        return d
    return None


def _split_address(addr):
    """Best-effort split for pre-filling CI address fields."""
    if not addr:
        return {'house_no': '', 'street': '', 'barangay': '', 'city': '', 'province': ''}
    chunks = [c.strip() for c in str(addr).split(',') if c.strip()]
    # Heuristic mapping: house/street/barangay/city/province
    mapped = {'house_no': '', 'street': '', 'barangay': '', 'city': '', 'province': ''}
    if len(chunks) >= 1:
        mapped['street'] = chunks[0]
    if len(chunks) >= 2:
        mapped['barangay'] = chunks[1]
    if len(chunks) >= 3:
        mapped['city'] = chunks[2]
    if len(chunks) >= 4:
        mapped['province'] = chunks[3]
    return mapped


def _ci_wizard_demo_sample_layer(app_dict, name_parts, addr, amount):
    """
    Extra sample fields so the CI wizard opens mostly complete for review/training.
    Real applicant/address/amount from LPS always come from the base prefill layer;
    this adds spouse, family, employment, and computation samples. Saved DB data
    still wins when merged after.
    """
    city = (addr.get('city') or '').strip() or 'Bayawan City'
    prov = (addr.get('province') or '').strip() or 'Negros Oriental'
    last = (name_parts.get('last') or 'Applicant').strip()
    amt = 0
    try:
        amt = float(amount or 0)
    except (TypeError, ValueError):
        amt = 0
    return {
        '_ci_sample_fill': True,
        # Spouse (sample)
        'spouse_last_name': 'Santos',
        'spouse_first_name': 'Maria',
        'spouse_middle_name': 'L.',
        'spouse_birthday': '1991-11-12',
        'spouse_age': 33,
        'spouse_employer': 'Private employer (sample)',
        'spouse_office': f'{city} (sample)',
        'spouse_contact': (app_dict.get('member_contact') or '') or '09000000000',
        # Family (sample — CI can edit)
        'family_1_name': f'Juan {last}',
        'family_1_age': 14,
        'family_1_rel': 'Child',
        'family_1_member': 'Non-member',
        'family_2_name': f'Carmen {last}',
        'family_2_age': 65,
        'family_2_rel': 'Parent',
        'family_2_member': 'Non-member',
        'family_3_name': '—',
        'family_3_age': '',
        'family_3_rel': '',
        'family_3_member': '',
        'family_4_name': '—',
        'family_4_age': '',
        'family_4_rel': '',
        'family_4_member': '',
        'applicant_birthday': '1989-04-15',
        'applicant_age': 36,
        # Work / business
        'app_employer': 'DCCCO-linked employer (sample)',
        'app_office': f'{city}, {prov} (sample)',
        'business_name': 'Agriculture / sari-sari (sample)',
        'business_address': (app_dict.get('member_address') or f'{city}')[:250],
        'years_business': 5,
        # Page 3 computation (sample — triggers formulas)
        'gross_pay': min(35000, max(15000, amt * 0.5)) if amt else 25000,
        'allowances': 0,
        'pera_aca': 0,
        'long_pay': 0,
        'statutory_deductions': 3000,
        'income_business': 0,
        'remittance': 0,
        'allotment': 0,
        'other_income': 0,
        'household_expenses': 8000,
        'tuition': 0,
        'medical': 0,
        'water_fuel': 1500,
        'internet': 1000,
        'collateral_oct': 'T-000000 (sample)',
        'collateral_location': f'{city} (sample)',
        'collateral_loan_value': min(500000, max(100000, amt * 2)) if amt else 200000,
        'collateral_area': 150,
        'other_info': 'Sample entries from system prefill after LPS submission — verify with interview.',
    }


def _build_ci_prefill_data(application, ci_name):
    """Create initial CI form values from LPS application details."""
    app_dict = dict(application)
    name = _split_member_name(app_dict.get('member_name'))
    addr = _split_address(app_dict.get('member_address'))
    today = now_ph().strftime('%Y-%m-%d')
    amount = app_dict.get('loan_amount') or 0

    prefill = {
        'applicant_last_name': name['last'],
        'applicant_first_name': name['first'],
        'applicant_middle_name': name['middle'],
        'house_no': addr['house_no'],
        'street': addr['street'],
        'barangay': addr['barangay'],
        'city': addr['city'],
        'province': addr['province'],
        'app_contact': app_dict.get('member_contact') or '',
        'comp_member_name': app_dict.get('member_name') or '',
        'comp_loan_type': app_dict.get('loan_type') or '',
        'comp_applied_amount': amount,
        'assess_member_name': app_dict.get('member_name') or '',
        'assess_loan_type': app_dict.get('loan_type') or '',
        'assess_loan_amount': amount,
        'new_loan_amount': amount,
        'date_reported': today,
        'date_investigated': today,
        'prepared_by': ci_name or '',
        'assess_prepared_by': ci_name or '',
    }
    # Demo layer (spouse, family row samples, cash-flow form numbers) — not from LPS.
    prefill.update(_ci_wizard_demo_sample_layer(app_dict, name, addr, amount))

    # If checklist already exists, use saved values as strongest source.
    saved_payload = app_dict.get('ci_checklist_data')
    if saved_payload:
        try:
            saved = json.loads(saved_payload)
            if isinstance(saved, dict):
                prefill.update(saved)
        except Exception:
            pass

    return prefill

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role in ['admin', 'loan_officer']:
            return redirect(url_for('admin_dashboard'))
        if current_user.role == 'loan_staff':
            return redirect(url_for('loan_dashboard'))
        if current_user.role == 'ci_staff':
            return redirect(url_for('ci_dashboard'))
        flash('Account role is not configured correctly. Please contact super admin.', 'danger')
        return redirect(url_for('logout'))
    return redirect(url_for('login'))


def _login_success_redirect(effective_role):
    """After successful login, go straight to the role dashboard (same as index() for auth users)."""
    if effective_role in ['admin', 'loan_officer']:
        return redirect(url_for('admin_dashboard'))
    if effective_role == 'loan_staff':
        return redirect(url_for('loan_dashboard'))
    if effective_role == 'ci_staff':
        return redirect(url_for('ci_dashboard'))
    flash('Account role is not configured correctly. Please contact super admin.', 'danger')
    return redirect(url_for('logout'))


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET' and current_user.is_authenticated:
        return index()

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # One DB checkout for this request: avoids multiple pool checkouts/round-trips on success path.
        conn = get_db()
        row = conn.execute(
            '''
            SELECT *
            FROM users
            WHERE email=?
            LIMIT 1
            ''',
            (email,),
        ).fetchone()
        valid_password = bool(row and check_password_hash(row['password_hash'], password))

        if valid_password:
            normalized_role = normalize_role(row['role'])
            effective_role = normalized_role if normalized_role else row['role']
            if normalized_role and normalized_role != row['role']:
                try:
                    conn.execute('UPDATE users SET role=? WHERE id=?', (normalized_role, row['id']))
                    conn.commit()
                except Exception as role_update_error:
                    print(f"⚠️  Role normalization warning (login): {role_update_error}")

            # Check if user is approved
            is_approved = row['is_approved'] if 'is_approved' in row.keys() else 1
            if is_approved == 0:
                flash('Your account is pending admin approval. Please wait.', 'warning')
                return render_template('login.html')

            # Active session (not signed out, not idle-expired) blocks another sign-in until Log out or idle cutoff.
            try:
                sess_row = conn.execute(
                    'SELECT is_active, last_seen FROM user_login_sessions WHERE user_id=?',
                    (row['id'],),
                ).fetchone()
            except Exception:
                sess_row = None
            if _login_blocked_by_active_session(sess_row):
                flash(
                    'This account is still signed in. Use Log out in the open session first—then you can '
                    'sign in again here from any device. '
                    '(If the session was idle for a long time, sign-in may be allowed automatically.)',
                    'warning',
                )
                return render_template('login.html')

            auth_session_token = uuid.uuid4().hex
            _upsert_user_session(conn, row['id'], auth_session_token)
            conn.commit()
            # Let teardown return this connection; do not close mid-request (saves an extra pool checkout).

            user = User(row['id'], row['email'], row['name'], effective_role, row['signature_path'] if 'signature_path' in row.keys() else None,
                       row['backup_email'] if 'backup_email' in row.keys() else None,
                       row['profile_photo'] if 'profile_photo' in row.keys() else None,
                       row['assigned_route'] if 'assigned_route' in row.keys() else None,
                       row['permissions'] if 'permissions' in row.keys() else None)
            login_user(user, remember=False)  # Session expires when browser closes
            session.permanent = False  # Ensure session is not permanent
            session['auth_session_token'] = auth_session_token
            session['_session_touch_ts'] = int(time.time())
            # Log without blocking the redirect (activity row is still written best-effort).
            run_background_task(
                _log_system_activity,
                (effective_role.replace('_', ' ').upper() if effective_role else 'SYSTEM'),
                (row['name'] if 'name' in row.keys() else row['email']),
                'LOG IN',
                actor_user_id=row['id'],
            )
            flash('Logged in successfully.', 'success')
            return _login_success_redirect(effective_role)
        if row and not valid_password:
            try:
                _maybe_send_security_alert(
                    row['id'],
                    'Security alert: A failed login attempt was detected for your account.',
                )
            except Exception:
                pass
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """
    Always allow logout without raising server errors.
    This route must succeed even when session/user state is partially broken.
    """
    auth_session_token = session.get('auth_session_token')
    legacy_sid = session.get('_user_id')
    actor_uid = None
    actor_name = None
    actor_role = None
    try:
        # Resolve identity while Flask-Login still knows the user (session key layout varies by version).
        try:
            if getattr(current_user, 'is_authenticated', False):
                actor_uid = int(getattr(current_user, 'id'))
                actor_name = getattr(current_user, 'name', None)
                actor_role = getattr(current_user, 'role', None)
        except (TypeError, ValueError, AttributeError):
            actor_uid = None

        if actor_uid is None:
            for _key in ('_user_id', 'user_id'):
                raw = session.get(_key)
                if raw is not None:
                    try:
                        actor_uid = int(raw)
                        break
                    except (TypeError, ValueError):
                        continue

        if actor_uid is not None:
            try:
                conn = get_db()
                try:
                    if not actor_name or not actor_role:
                        user_row = conn.execute(
                            'SELECT name, role FROM users WHERE id=? LIMIT 1',
                            (actor_uid,),
                        ).fetchone()
                        if user_row:
                            if not actor_name:
                                actor_name = user_row['name'] if 'name' in user_row.keys() else None
                            if not actor_role:
                                actor_role = user_row['role'] if 'role' in user_row.keys() else None
                    conn.execute(
                        'UPDATE users SET last_seen=?, is_online=0 WHERE id=?',
                        (now_ph().isoformat(), actor_uid),
                    )
                    conn.commit()
                finally:
                    conn.close()
            except Exception as online_err:
                app.logger.debug('logout online/offline update skipped: %s', online_err)

        if not actor_name:
            actor_name = getattr(current_user, 'name', None) or 'System User'
        if not actor_role:
            actor_role = getattr(current_user, 'role', None) or 'system'

        # Store logout event before clearing session.
        _log_system_activity(
            str(actor_role).replace('_', ' ').upper(),
            str(actor_name),
            'LOG OUT',
            actor_user_id=actor_uid,
        )

        # Clear AI chat history from session if present.
        session.pop('ai_chat_history', None)

        # Best effort Flask-Login logout.
        try:
            logout_user()
        except Exception as logout_err:
            app.logger.debug('logout_user failed, forcing session clear: %s', logout_err)

        deactivate_uid = actor_uid
        if deactivate_uid is None and legacy_sid is not None:
            try:
                deactivate_uid = int(legacy_sid)
            except (TypeError, ValueError):
                deactivate_uid = None
        if deactivate_uid is not None:
            _deactivate_user_session(deactivate_uid, auth_session_token)

        # Clear any remaining session keys to avoid stale auth state.
        session.clear()
        if request.method == 'POST':
            return ('', 204)
        flash('Logged out.', 'info')
        return redirect(url_for('login'))
    except Exception as e:
        app.logger.exception('logout route failed: %s', e)
        try:
            session.clear()
        except Exception:
            pass
        if request.method == 'POST':
            return ('', 204)
        return redirect(url_for('login'))

# LOAN STAFF ROUTES
@app.route('/loan/dashboard')
@login_required
def loan_dashboard():
    import time as _time
    _t0 = _time.monotonic()
    if current_user.role != 'loan_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    conn = get_db()
    # Only fetch the columns the template reads — avoids transferring ci_checklist_data,
    # admin_notes, loan_officer_notes, and other wide TEXT columns from PostgreSQL.
    # Oldest first so new submissions appear at the bottom (full list per LPS — no LIMIT).
    applications = conn.execute('''
        SELECT la.id, la.status, la.member_name, la.loan_amount, la.loan_type,
               la.submitted_at, la.needs_ci_interview, la.assigned_ci_staff,
               u.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.assigned_ci_staff = u.id
        WHERE la.submitted_by = ?
        ORDER BY la.submitted_at ASC, la.id ASC
    ''', (current_user.id,)).fetchall()
    _t_q1 = _time.monotonic()

    ci_staff_list = fetch_ci_staff_list(conn, include_pending=True)
    _t_q2 = _time.monotonic()

    unread_count = get_unread_notification_count(current_user.id)

    _total = _time.monotonic() - _t0
    if _total > 0.5:
        import logging as _log
        _log.getLogger('app.perf').warning(
            'loan_dashboard slow %.3fs | q1(apps)=%.0fms q2(staff)=%.0fms q3(notif)=%.0fms',
            _total, (_t_q1 - _t0) * 1000, (_t_q2 - _t_q1) * 1000,
            (_time.monotonic() - _t_q2) * 1000,
        )

    return render_template('loan_dashboard.html', applications=applications,
                           unread_count=unread_count, ci_staff_list=ci_staff_list)

@app.route('/api/session_status', methods=['GET'])
def api_session_status():
    """
    Lightweight auth check for history revalidation (returns JSON 401, not a login HTML page).
    Used when the user returns via Back/Forward so we can redirect to login if the session ended.
    """
    if not current_user.is_authenticated:
        resp = jsonify({'ok': False})
        resp.headers['Cache-Control'] = 'no-store, private, max-age=0'
        return resp, 401
    resp = jsonify({'ok': True})
    resp.headers['Cache-Control'] = 'no-store, private, max-age=0'
    return resp


@app.route('/api/session_heartbeat', methods=['POST'])
@login_required
def session_heartbeat():
    """
    Refresh server-side last_seen for long single-page work (checklists, long forms)
    so the session is not treated as idle while the user is still active in the tab.
    """
    try:
        auth_token = session.get('auth_session_token')
        if auth_token and current_user.is_authenticated:
            _touch_user_session(current_user.id, auth_token)
            session['_session_touch_ts'] = int(time.time())
    except Exception:
        pass
    return jsonify({'ok': True})


@app.route('/notifications/count')
@login_required
def notification_count():
    count = get_unread_notification_count(current_user.id)
    return jsonify({'count': count})

@app.route('/loan/update_status/<int:app_id>', methods=['POST'])
@login_required
def update_application_status(app_id):
    if current_user.role != 'loan_staff':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    conn = get_db()
    app_data = conn.execute(
        'SELECT * FROM loan_applications WHERE id=? AND submitted_by=?',
        (app_id, current_user.id),
    ).fetchone()
    if not app_data:
        conn.close()
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    conn.execute('UPDATE loan_applications SET status=? WHERE id=?', (new_status, app_id))
    conn.commit()
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (app_id,)).fetchone()
    conn.close()
    
    try:
        if not app_data:
            _st_sb = None
        else:
            _r = app_data['submitted_by']
            _st_sb = int(_r) if _r is not None else None
    except (KeyError, TypeError, ValueError):
        _st_sb = None
    # Emit real-time update to all connected dashboards
    socketio.emit('application_updated', {
        'id': app_id,
        'status': new_status,
        'member_name': app_data['member_name'] if app_data else '',
        'loan_amount': float(app_data['loan_amount']) if app_data else 0,
        'submitted_by': _st_sb,
        'timestamp': now_ph().isoformat()
    })
    
    return jsonify({'success': True})

@app.route('/loan/update_ci_staff/<int:app_id>', methods=['POST'])
@login_required
def update_ci_staff_assignment(app_id):
    if current_user.role != 'loan_staff':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    ci_staff_id = data.get('ci_staff_id')
    
    conn = get_db()
    owner = conn.execute(
        'SELECT id FROM loan_applications WHERE id=? AND submitted_by=?',
        (app_id, current_user.id),
    ).fetchone()
    if not owner:
        conn.close()
        return jsonify({'success': False, 'error': 'Forbidden'}), 403
    if ci_staff_id:
        conn.execute('UPDATE loan_applications SET assigned_ci_staff=?, status=? WHERE id=?', 
                    (ci_staff_id, 'assigned_to_ci', app_id))
        # Send notification to CI staff
        enqueue_notification(
            int(ci_staff_id),
            'New loan application assigned to you',
            f'/ci/application/{app_id}'
        )
    else:
        conn.execute('UPDATE loan_applications SET assigned_ci_staff=NULL WHERE id=?', (app_id,))
    
    conn.commit()
    
    # Get application details for real-time update
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (app_id,)).fetchone()
    conn.close()
    
    try:
        if not app_data:
            _ci2_sb = None
        else:
            _r2 = app_data['submitted_by']
            _ci2_sb = int(_r2) if _r2 is not None else None
    except (KeyError, TypeError, ValueError):
        _ci2_sb = None
    # Emit real-time update to all connected dashboards
    socketio.emit('application_updated', {
        'id': app_id,
        'status': 'assigned_to_ci' if ci_staff_id else app_data['status'],
        'member_name': app_data['member_name'] if app_data else '',
        'loan_amount': float(app_data['loan_amount']) if app_data else 0,
        'ci_staff_id': ci_staff_id,
        'submitted_by': _ci2_sb,
        'timestamp': now_ph().isoformat()
    })
    
    return jsonify({'success': True})

@app.route('/loan/submit', methods=['GET','POST'])
@login_required
def submit_application():
    try:
        user_role = getattr(current_user, 'role', None)
        if user_role != 'loan_staff':
            flash('Unauthorized', 'danger')
            return redirect(url_for('index'))

        if request.method == 'POST':
            try:
                member_name = (request.form.get('member_name') or '').strip()
                member_contact = _sanitize_optional_ph_mobile_input(request.form.get('member_contact'))
                if member_contact is None:
                    flash(
                        'Contact number must be 11 digits starting with 09 (e.g. 09751762630). '
                        'Leave blank if unknown.',
                        'danger',
                    )
                    return redirect(url_for('submit_application'))
                member_address = (request.form.get('member_address') or '').strip()
                loan_amount = (request.form.get('loan_amount') or '').strip()
                # Support both the visible typeahead field and hidden selected value.
                loan_type = (request.form.get('loan_type_hidden') or request.form.get('loan_type') or '').strip()
                lps_remarks = request.form.get('lps_remarks', '').strip()
                needs_ci_value = request.form.get('needs_ci', '1')

                if not member_name or not loan_amount or not loan_type:
                    flash('Please fill in member name, loan amount, and loan type.', 'danger')
                    return redirect(url_for('submit_application'))

                try:
                    amount_value = float(loan_amount)
                    if amount_value <= 0:
                        raise ValueError('Loan amount must be greater than zero')
                except Exception:
                    flash('Loan amount is invalid. Please enter a valid number.', 'danger')
                    return redirect(url_for('submit_application'))

                conn = get_db()
                removed = _purge_nonfinal_duplicate_applications(conn, member_name)
                if removed:
                    flash(
                        f'Removed {removed} older open application(s) for this member name '
                        '(submitted / assigned to CI / deferred only; completed and final decisions are kept).',
                        'info',
                    )

                # Check if specific CI staff was selected
                specific_ci_id = None
                if needs_ci_value.startswith('ci_'):
                    ci_id_raw = needs_ci_value.replace('ci_', '').strip()
                    if not ci_id_raw.isdigit():
                        raise ValueError('Invalid CI staff selection')
                    specific_ci_id = int(ci_id_raw)
                    needs_ci = 1
                else:
                    try:
                        needs_ci = int(needs_ci_value)
                    except Exception:
                        needs_ci = 1
                    needs_ci = 1 if needs_ci not in (0, 1) else needs_ci
            except Exception as e:
                print(f"ERROR in form processing: {str(e)}")
                import traceback
                traceback.print_exc()
                flash(f'Error processing form data: {str(e)}', 'danger')
                return redirect(url_for('submit_application'))
            try:
                app_id = _insert_loan_application(
                    conn,
                    member_name,
                    member_contact,
                    member_address,
                    loan_amount,
                    loan_type,
                    lps_remarks,
                    needs_ci,
                    current_user.id,
                )
                if not app_id:
                    conn.rollback()
                    conn.close()
                    flash('Could not save the application. Please try again.', 'danger')
                    return redirect(url_for('submit_application'))
                # Handle file uploads
                if 'documents' in request.files:
                    files = request.files.getlist('documents')
                    for file in files:
                        if file and file.filename:
                            # Validate file extension
                            if not allowed_file(file.filename):
                                conn.rollback()
                                conn.close()
                                flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, PDF, DOC, DOCX', 'danger')
                                return redirect(url_for('submit_application'))

                            filename = sanitize_filename(file.filename)
                            unique_filename = f"{app_id}_{uuid.uuid4().hex[:8]}_{filename}"
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                            file.save(filepath)
                            insert_loan_document_row(
                                conn, app_id, filepath, filename, current_user.id
                            )

                # Assign to CI staff
                if needs_ci:
                    if specific_ci_id:
                        # Assign to specific approved CI staff when explicitly selected.
                        try:
                            selected_ci = conn.execute(
                                '''
                                SELECT id FROM users
                                WHERE id = ? AND role = 'ci_staff' AND is_approved = 1
                                LIMIT 1
                                ''',
                                (specific_ci_id,),
                            ).fetchone()
                        except Exception:
                            selected_ci = conn.execute(
                                '''
                                SELECT id FROM users
                                WHERE id = ? AND role = 'ci_staff'
                                LIMIT 1
                                ''',
                                (specific_ci_id,),
                            ).fetchone()
                        ci_staff_id = selected_ci['id'] if selected_ci else None
                    else:
                        # ROUTE-BASED ASSIGNMENT: Match applicant address to CI route coverage
                        ci_staff_id = None
                        matched_route = resolve_ci_route_key_for_member_address(member_address)

                        if matched_route:
                            ci_staff_id = fetch_first_ci_staff_id_for_route_key(conn, matched_route)
                        # Fallback to workload-based if no route match
                        if not ci_staff_id:
                            try:
                                ci_staff = conn.execute('''
                                    SELECT id FROM users
                                    WHERE role='ci_staff' AND is_approved=1
                                    ORDER BY current_workload ASC
                                    LIMIT 1
                                ''').fetchone()
                            except Exception:
                                try:
                                    ci_staff = conn.execute('''
                                        SELECT id FROM users
                                        WHERE role='ci_staff'
                                        ORDER BY current_workload ASC
                                        LIMIT 1
                                    ''').fetchone()
                                except Exception:
                                    ci_staff = conn.execute('''
                                        SELECT id FROM users
                                        WHERE role='ci_staff'
                                        LIMIT 1
                                    ''').fetchone()
                            ci_staff_id = ci_staff['id'] if ci_staff else None

                    if ci_staff_id:
                        conn.execute('UPDATE loan_applications SET status=?, assigned_ci_staff=? WHERE id=?',
                                   ('assigned_to_ci', ci_staff_id, app_id))
                        conn.execute('UPDATE users SET current_workload = current_workload + 1 WHERE id=?',
                                   (ci_staff_id,))
                        conn.commit()
                        conn.close()
                        enqueue_notification(
                            ci_staff_id,
                            f'New loan application assigned: {member_name}',
                            f'/ci/application/{app_id}'
                        )
                    else:
                        conn.commit()
                        conn.close()
                else:
                    # Send directly to loan officer
                    try:
                        loan_officer = conn.execute('''
                            SELECT id
                            FROM users
                            WHERE is_approved = 1
                              AND role IN ('loan_officer', 'admin')
                            ORDER BY CASE WHEN role = 'loan_officer' THEN 0 ELSE 1 END, id ASC
                            LIMIT 1
                        ''').fetchone()
                    except Exception:
                        loan_officer = conn.execute('''
                            SELECT id
                            FROM users
                            WHERE role IN ('loan_officer', 'admin')
                            ORDER BY CASE WHEN role = 'loan_officer' THEN 0 ELSE 1 END, id ASC
                            LIMIT 1
                        ''').fetchone()
                    conn.commit()
                    conn.close()
                    if loan_officer:
                        enqueue_notification(
                            loan_officer['id'],
                            f'New loan application submitted: {member_name}',
                            f'/admin/application/{app_id}'
                        )

                flash('Application submitted successfully!', 'success')

                # Emit WebSocket event for instant dashboard update
                socketio.emit('new_application', {
                    'id': app_id,
                    'member_name': member_name,
                    'status': 'assigned_to_ci' if needs_ci else 'submitted',
                    'submitted_by': int(current_user.id),
                })

                return redirect(url_for('loan_dashboard'))
            except Exception as e:
                print(f"ERROR in database operations: {str(e)}")
                import traceback
                traceback.print_exc()
                if 'conn' in locals():
                    conn.rollback()
                    conn.close()
                flash(f'Error submitting application: {str(e)}', 'danger')
                return redirect(url_for('submit_application'))

        try:
            conn = get_db()
            # Get all CI staff with backward-compatible schema handling.
            ci_staff_list = fetch_ci_staff_list(conn, include_pending=True)
            conn.close()
        except Exception as e:
            print(f"WARNING loading CI staff list for submit page: {e}")
            ci_staff_list = []
        try:
            unread_count = get_unread_notification_count(current_user.id)
        except Exception as e:
            print(f"WARNING loading unread notifications for submit page: {e}")
            unread_count = 0
        try:
            return render_template('submit_application.html', unread_count=unread_count, ci_staff_list=ci_staff_list)
        except Exception as e:
            app.logger.exception("submit_application GET render failed: %s", e)
            flash('Submit Application page encountered a temporary issue. Please try again in a moment.', 'warning')
            return redirect(url_for('loan_dashboard'))
    except Exception as outer_err:
        app.logger.exception("submit_application unexpected failure: %s", outer_err)
        flash('Submit Application is temporarily unavailable. Please refresh and try again.', 'danger')
        return redirect(url_for('loan_dashboard'))


@app.route('/api/member_application_prefill')
@login_required
def api_member_application_prefill():
    """
    For new submissions: return the most recent loan_application row for this member name
    (case-insensitive, trimmed) so the form can prefill contact/address/loan — all still editable.
    """
    if current_user.role != 'loan_staff':
        return jsonify({'ok': False, 'error': 'forbidden'}), 403
    name = (request.args.get('name') or '').strip()
    if len(name) < 2:
        return jsonify({'ok': True, 'found': False})
    conn = get_db()
    try:
        row = conn.execute(
            '''
            SELECT member_contact, member_address, loan_type, loan_amount
            FROM loan_applications
            WHERE LOWER(TRIM(COALESCE(member_name, ''))) = LOWER(TRIM(?))
            ORDER BY id DESC
            LIMIT 1
            ''',
            (name,),
        ).fetchone()
        if not row:
            return jsonify({'ok': True, 'found': False})
        d = dict(row)
        la = d.get('loan_amount')
        try:
            la_out = float(la) if la is not None and la != '' else None
        except (TypeError, ValueError):
            la_out = None
        related_rows = conn.execute(
            '''
            SELECT loan_type, loan_amount, status, member_contact, member_address, submitted_at
            FROM loan_applications
            WHERE LOWER(TRIM(COALESCE(member_name, ''))) = LOWER(TRIM(?))
            ORDER BY id DESC
            LIMIT 30
            ''',
            (name,),
        ).fetchall()
        applications = []
        active_count = 0
        for rr in related_rows or []:
            r = dict(rr)
            raw_amt = r.get('loan_amount')
            try:
                amt = float(raw_amt) if raw_amt is not None and raw_amt != '' else None
            except (TypeError, ValueError):
                amt = None
            status = (r.get('status') or '').strip()
            if status in ('submitted', 'assigned_to_ci', 'ci_completed', 'deferred'):
                active_count += 1
            applications.append(
                {
                    'loan_type': (r.get('loan_type') or '').strip(),
                    'loan_amount': amt,
                    'status': status,
                    'member_contact': (r.get('member_contact') or '').strip(),
                    'member_address': (r.get('member_address') or '').strip(),
                    'submitted_at': r.get('submitted_at'),
                }
            )
        return jsonify(
            {
                'ok': True,
                'found': True,
                'member_contact': (d.get('member_contact') or '') or '',
                'member_address': (d.get('member_address') or '') or '',
                'loan_type': (d.get('loan_type') or '') or '',
                'loan_amount': la_out,
                'applications': applications,
                'active_application_count': active_count,
            }
        )
    except Exception as e:
        app.logger.exception('api_member_application_prefill: %s', e)
        return jsonify({'ok': False, 'error': 'server_error'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


# CI STAFF ROUTES
@app.route('/ci/dashboard')
@login_required
def ci_dashboard():
    import time as _time
    _t0 = _time.monotonic()
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    conn = get_db()
    # Select only columns the CI dashboard template needs.
    # Oldest first so new assignments appear at the bottom of each section (no LIMIT).
    applications = conn.execute('''
        SELECT la.id, la.status, la.member_name, la.member_address, la.loan_amount,
               la.loan_type, la.submitted_at, la.needs_ci_interview, la.assigned_ci_staff,
               u.name as loan_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.submitted_by = u.id
        WHERE la.assigned_ci_staff = ?
        ORDER BY la.submitted_at ASC, la.id ASC
    ''', (current_user.id,)).fetchall()
    _t_q1 = _time.monotonic()

    unread_count = get_unread_notification_count(current_user.id)

    _total = _time.monotonic() - _t0
    if _total > 0.5:
        import logging as _log
        _log.getLogger('app.perf').warning(
            'ci_dashboard slow %.3fs | q1(apps)=%.0fms',
            _total, (_t_q1 - _t0) * 1000,
        )

    return render_template('ci_dashboard.html', applications=applications, unread_count=unread_count)

@app.route('/ci/checklist/<int:id>', methods=['GET'])
@login_required
def ci_checklist(id):
    """Redirect to checkbox summary page first"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    # Redirect to checkbox summary
    return redirect(url_for('ci_checklist_summary', id=id))


@app.route('/ci/checklist/summary/<int:id>')
@login_required
def ci_checklist_summary(id):
    """CI Checklist Summary - All checkboxes in one page before 5-page wizard"""
    try:
        # Check authorization
        if not hasattr(current_user, 'role'):
            flash('Session error. Please login again.', 'danger')
            return redirect(url_for('login'))
            
        if current_user.role != 'ci_staff':
            flash('Unauthorized access. CI Staff only.', 'danger')
            return redirect(url_for('index'))
        
        conn = get_db()
        
        # Get application data with all fields
        app_data = conn.execute('''
            SELECT 
                la.id,
                la.member_name,
                la.member_contact,
                la.member_address,
                la.loan_amount,
                la.loan_type,
                la.status,
                la.submitted_at,
                la.submitted_by,
                u.name as loan_staff_name
            FROM loan_applications la
            LEFT JOIN users u ON la.submitted_by = u.id
            WHERE la.id=?
        ''', (id,)).fetchone()
        
        if not app_data:
            conn.close()
            flash('Application not found', 'danger')
            return redirect(url_for('ci_dashboard'))
        
        # Convert to dict for easier access
        application = dict(app_data)
        
        # Get unread notifications count safely
        unread_count = 0
        try:
            result = conn.execute('''
                SELECT COUNT(*) as count 
                FROM notifications 
                WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'
            ''', (current_user.id,)).fetchone()
            if result:
                unread_count = result['count']
        except Exception as e:
            print(f"Error getting unread count: {e}")
        
        conn.close()
        
        # Render simple checkbox summary template
        return render_template('ci_checklist_summary_simple.html', 
                             application=application,
                             unread_count=unread_count)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"=== ERROR in ci_checklist_summary ===")
        print(f"Error: {str(e)}")
        print(f"Details: {error_details}")
        print(f"=== END ERROR ===")
        
        flash('An error occurred while loading the page. Please try again.', 'danger')
        
        try:
            return redirect(url_for('ci_dashboard'))
        except:
            return redirect(url_for('index'))


@app.route('/ci/checklist/wizard/<int:id>', methods=['GET'])
@login_required
def ci_checklist_wizard(id):
    """Display the multi-page CI checklist wizard (5 pages)"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    
    if not app_data:
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('ci_dashboard'))

    # Ensure CI only accesses assigned application.
    assigned_ci_staff = app_data['assigned_ci_staff'] if 'assigned_ci_staff' in app_data.keys() else None
    if assigned_ci_staff != current_user.id:
        flash('This application is not assigned to your account.', 'warning')
        conn.close()
        return redirect(url_for('ci_dashboard'))

    unread_count = get_unread_notification_count(current_user.id)
    prefill_data = _build_ci_prefill_data(app_data, current_user.name)

    import_pkg = request.args.get("import_offline_package", type=int)
    if import_pkg:
        off = get_offline_package_for_wizard(import_pkg, current_user.id, id)
        if off:
            ch = off.get("checklist")
            if isinstance(ch, str):
                try:
                    ch = json.loads(ch)
                except Exception:
                    ch = None
            if isinstance(ch, dict):
                prefill_data.update(ch)
        else:
            flash(
                "Offline import is missing or not for this application. You can still edit the checklist as usual.",
                "warning",
            )

    conn.close()
    return render_template(
        'ci_checklist_wizard.html',
        application=app_data,
        unread_count=unread_count,
        prefill_data=prefill_data
    )

@app.route('/ci/application/<int:id>', methods=['GET','POST'])
@login_required
def ci_application(id):
    """Show review page with documents and verification checkboxes"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    # Redirect to review page
    return redirect(url_for('ci_review_application', id=id))

@app.route('/ci/review/<int:id>')
@login_required
def ci_review_application(id):
    """CI Review Page - View documents and verify before interview"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('''
        SELECT la.*, u.name as loan_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.submitted_by = u.id
        WHERE la.id=? AND la.assigned_ci_staff=?
    ''', (id, current_user.id)).fetchone()
    
    if not app_data:
        flash('Application not found or not assigned to you', 'danger')
        conn.close()
        return redirect(url_for('ci_dashboard'))
    
    # Get uploaded documents (all rows; thumbnails served via view_loan_document)
    try:
        documents = conn.execute(
            'SELECT id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at'
            ' FROM documents WHERE loan_application_id=? ORDER BY uploaded_at DESC',
            (id,),
        ).fetchall()
    except Exception as doc_err:
        print(f"WARNING loading CI documents for app {id}: {doc_err}")
        documents = []

    unread_count = get_unread_notification_count(current_user.id)
    conn.close()

    return render_template('ci_review_application.html',
                           application=app_data,
                           documents=documents,
                           unread_count=unread_count)


def _coalesce_ci_staff_display(app_data, checklist_data):
    """
    When saved checklist JSON still has generic wizard placeholders, show the
    assigned CI from loan_applications (authoritative) instead.
    """
    if not isinstance(checklist_data, dict):
        return
    name = (app_data.get('ci_staff_name') or '').strip()
    if not name:
        return

    def _norm_placeholder(s):
        return ' '.join((s or '').lower().strip().split())

    generic = {
        'ci staff',
        'ci/bi',
        'ci / bi',
        'ci-bi',
        'ci staff name',
        'credit investigator',
        'cibi / lps / flms',
        'cibi',
        'lps',
        'flms',
        'n/a',
        '—',
        '-',
        'tbd',
        'prepared ci staff',
        'prepared by ci staff',
        'ci staff prepared',
        'credit investigator staff',
        'ci bi staff',
    }

    def _is_placeholder(raw):
        raw = (raw or '').strip()
        if not raw:
            return True
        tl = _norm_placeholder(raw)
        if tl in generic:
            return True
        # One-line wizard boilerplate still containing only variant CI staff wording.
        if 'ci staff' in tl and len(tl) <= 72:
            return True
        return False

    for key in ('prepared_by', 'assess_prepared_by'):
        raw = checklist_data.get(key)
        if _is_placeholder(raw):
            checklist_data[key] = name


def _loan_application_ci_signature_column_usable(raw):
    """
    loan_applications.ci_signature must be a data URL, HTTP(S) URL, or filename/path to an image.
    Older bugs stored plain-text names here — ignore those so resolution falls back to users.signature_path.
    """
    if raw is None:
        return False
    s = str(raw).strip()
    if not s:
        return False
    low = s.lower()
    if low.startswith('data:image/'):
        return True
    if low.startswith('http://') or low.startswith('https://'):
        return True
    norm = s.replace('\\', '/')
    if '/signatures/' in norm:
        return True
    tail = s.split('?')[0].split('#')[0]
    if re.search(r'\.(png|jpe?g|gif|webp|bmp|svg)$', tail, re.I):
        return True
    return False


def _resolve_ci_signature_for_print(app_data):
    """
    Build a same-origin /signatures/<file> URL or pass through data:image/* for <img src>.
    Submit may store an absolute _external URL; that breaks if host or scheme differs from
    the current app. Fall back to the assigned CI user signature_path.
    """
    from urllib.parse import unquote, urlparse

    raw_stored = (app_data.get('ci_signature') or '').strip()
    raw = raw_stored if _loan_application_ci_signature_column_usable(raw_stored) else ''
    prof = (app_data.get('ci_signature_path') or '').strip().replace('\\', '/')

    if raw.lower().startswith('data:image/'):
        return raw

    def _extract_filename(s):
        if not s or s.lower().startswith('data:') or '..' in s:
            return None
        s = s.replace('\\', '/').strip()
        is_http = s.startswith('http://') or s.startswith('https://')
        if is_http:
            path = (urlparse(s).path or '')
            if '/signatures/' not in path:
                segs = [x for x in path.split('/') if x]
                last = unquote(segs[-1]) if segs else ''
                if last and re.search(r'\.(png|jpe?g|gif|webp|bmp|svg)$', last, re.I) and '..' not in last:
                    return last
                return None
            s = path
        if '/signatures/' in s:
            fn = unquote(s.split('/signatures/', 1)[-1].split('?')[0].split('#')[0])
        else:
            parts = s.rstrip('/').split('/')
            fn = unquote(parts[-1]) if parts and parts[-1] else None
        if not fn or '..' in fn or '/' in fn or '\\' in fn:
            return None
        return fn

    for src in (raw, prof):
        if not src:
            continue
        fn = _extract_filename(src)
        if (not fn and src and not src.startswith('http') and '/signatures/' not in src
                and '/' not in src and '\\' not in src
                and re.search(r'\.(png|jpe?g|gif|webp|bmp|svg)$', src, re.I)):
            fn = src
        if fn:
            return url_for('serve_signature', filename=fn)

    # Basename fallback when stored paths use odd separators or prefixes extraction missed.
    prof_tail = prof.split('/')[-1].split('?')[0].split('#')[0]
    raw_tail = raw.replace('\\', '/').split('/')[-1].split('?')[0].split('#')[0] if raw else ''
    for tail in (prof_tail, raw_tail):
        tail = unquote((tail or '').strip())
        if not tail or '..' in tail:
            continue
        if re.search(r'\.(png|jpe?g|gif|webp|bmp|svg)$', tail, re.I):
            return url_for('serve_signature', filename=tail)
    return None


def _inline_ci_signature_from_disk(app_data, resolved=None):
    """
    Read the CI signature file into a data URL so printed checklists embed the image.
    Avoids relying on the browser fetching /signatures/... during print (same-origin cookies).
    """
    import base64

    raw_col = (app_data.get('ci_signature') or '').strip()
    if raw_col.lower().startswith('data:image/'):
        return raw_col
    if resolved and isinstance(resolved, str) and resolved.lower().startswith('data:image/'):
        return resolved

    sig_folder = os.path.abspath(app.config['SIGNATURE_FOLDER'])
    paths_try = []

    prof = (app_data.get('ci_signature_path') or '').strip()
    if prof:
        pnorm = os.path.normpath(prof.replace('\\', os.sep))
        try:
            if os.path.isfile(pnorm):
                paths_try.append(pnorm)
        except OSError:
            pass
        bn = os.path.basename(prof.replace('\\', '/'))
        if bn and '..' not in bn:
            paths_try.append(os.path.normpath(os.path.join(sig_folder, bn)))

    fn_hint = None
    if resolved and isinstance(resolved, str):
        ru = resolved.strip()
        low = ru.lower()
        if '/signatures/' in low:
            fn_hint = ru.split('/signatures/', 1)[-1].split('?')[0].split('#')[0]
        elif low.startswith('/signatures/'):
            fn_hint = ru[len('/signatures/'):].split('?')[0].split('#')[0]
    if fn_hint and '..' not in fn_hint.replace('\\', '/'):
        paths_try.append(os.path.normpath(os.path.join(sig_folder, fn_hint)))

    seen = set()
    for cand in paths_try:
        if not cand or cand in seen:
            continue
        seen.add(cand)
        try:
            acand = os.path.abspath(cand)
        except OSError:
            continue
        if not _is_path_within_directory(sig_folder, acand):
            continue
        if not os.path.isfile(acand):
            continue
        ext = os.path.splitext(acand)[1].lower()
        mime_map = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
            '.svg': 'image/svg+xml',
        }
        mime = mime_map.get(ext) or (mimetypes.guess_type(acand)[0] or 'image/png')
        try:
            with open(acand, 'rb') as f:
                b64 = base64.standard_b64encode(f.read()).decode('ascii')
            return f'data:{mime};base64,{b64}'
        except OSError:
            continue
    return None


def _ensure_ci_staff_for_print(conn, application_id, app_data):
    """Fill ci_staff_name / ci_signature_path from assigned_ci_staff or CI-uploaded documents."""
    uid = app_data.get('assigned_ci_staff')
    try:
        uid = int(uid) if uid is not None else None
    except (TypeError, ValueError):
        uid = None

    if uid:
        need_name = not (app_data.get('ci_staff_name') or '').strip()
        need_sigpath = not (app_data.get('ci_signature_path') or '').strip()
        if need_name or need_sigpath:
            urow = conn.execute(
                'SELECT COALESCE(name, "") AS n, COALESCE(signature_path, "") AS sp FROM users WHERE id=?',
                (uid,),
            ).fetchone()
            if urow:
                ud = dict(urow)
                if need_name:
                    app_data['ci_staff_name'] = (ud.get('n') or '').strip()
                if need_sigpath:
                    app_data['ci_signature_path'] = (ud.get('sp') or '').strip()
        return

    if (app_data.get('status') or '').strip() != 'ci_completed':
        return

    row = conn.execute(
        '''
        SELECT u.id AS uid, COALESCE(u.name, '') AS n, COALESCE(u.signature_path, '') AS sp
        FROM documents d
        INNER JOIN users u ON d.uploaded_by = u.id AND u.role = 'ci_staff'
        WHERE d.loan_application_id = ?
        ORDER BY d.uploaded_at DESC
        LIMIT 1
        ''',
        (application_id,),
    ).fetchone()
    if row:
        r = dict(row)
        app_data['assigned_ci_staff'] = r.get('uid')
        app_data['ci_staff_name'] = (r.get('n') or '').strip()
        app_data['ci_signature_path'] = (r.get('sp') or '').strip()


@app.route('/view/checklist/<int:id>')
@login_required
def view_ci_checklist(id):
    """View completed CI checklist (for loan officer/admin)"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        app_row = conn.execute('''
            SELECT la.*,
                   COALESCE(ci.name, '') AS ci_staff_name,
                   COALESCE(ci.signature_path, '') AS ci_signature_path,
                   COALESCE(lps.name, '') AS loan_staff_name
            FROM loan_applications la
            LEFT JOIN users ci ON la.assigned_ci_staff = ci.id
            LEFT JOIN users lps ON la.submitted_by = lps.id
            WHERE la.id=?
        ''', (id,)).fetchone()

        if not app_row:
            flash('Application not found', 'danger')
            return redirect(url_for('admin_dashboard'))

        app_data = dict(app_row)

        _ensure_ci_staff_for_print(conn, id, app_data)

        resolved_sig = _resolve_ci_signature_for_print(app_data)
        app_data['ci_signature'] = _inline_ci_signature_from_disk(app_data, resolved_sig) or resolved_sig

        # Ensure completed timestamp is a plain string for the template.
        if app_data.get('ci_completed_at') and not isinstance(app_data['ci_completed_at'], str):
            try:
                app_data['ci_completed_at'] = app_data['ci_completed_at'].strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                app_data['ci_completed_at'] = str(app_data['ci_completed_at'])

        # Parse checklist data (may be empty if CI only uploaded photos).
        checklist_data = {}
        raw_checklist = app_data.get('ci_checklist_data')
        if raw_checklist:
            try:
                import json as _json
                parsed = _json.loads(raw_checklist)
                if isinstance(parsed, dict):
                    checklist_data = parsed
            except Exception:
                checklist_data = {}

        _coalesce_ci_staff_display(app_data, checklist_data)

        # Prefill commonly referenced identity fields from the loan application
        # so the printed page is never empty when CI just uploaded photos.
        checklist_data.setdefault('applicant_first_name', app_data.get('member_name') or '')
        checklist_data.setdefault('applicant_last_name', '')
        checklist_data.setdefault('applicant_contact', app_data.get('phone_number') or '')
        checklist_data.setdefault('house_no', app_data.get('address') or '')
        checklist_data.setdefault('prepared_by', app_data.get('ci_staff_name') or '')

        # Gather LPS-submitted reference photos and any CI uploads.
        docs = conn.execute(
            'SELECT id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at'
            ' FROM documents WHERE loan_application_id=? ORDER BY uploaded_at DESC',
            (id,)
        ).fetchall()

        lps_photos = []
        ci_photos = []
        image_exts = (
            '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tif', '.tiff',
            '.heic', '.heif', '.svg',
        )
        _asg = app_data.get('assigned_ci_staff')
        for doc in docs:
            d = dict(doc)
            path = (d.get('file_path') or '').replace('\\', '/')
            serve_key = (_upload_relpath_for_serve(d.get('file_path')) or (path.split('/')[-1] if path else '')).strip()
            fn_for_type = (d.get('file_name') or serve_key or '').lower()
            is_image = fn_for_type.endswith(image_exts)
            ub = d.get('uploaded_by')
            try:
                is_ci_doc = int(_asg) == int(ub) if _asg is not None and ub is not None else False
            except (TypeError, ValueError):
                is_ci_doc = str(_asg) == str(ub) if _asg is not None and ub is not None else False
            entry = {
                'id': d.get('id'),
                'file_name': d.get('file_name') or (serve_key.rsplit('/', 1)[-1] if serve_key else ''),
                'filename': serve_key,
                'is_image': is_image,
                'uploaded_by': d.get('uploaded_by'),
                'uploaded_at': d.get('uploaded_at'),
                'is_ci_upload': is_ci_doc,
            }
            if is_ci_doc:
                ci_photos.append(entry)
            else:
                lps_photos.append(entry)

        return render_template(
            'view_ci_checklist.html',
            application=app_data,
            checklist_data=checklist_data,
            lps_photos=lps_photos,
            ci_photos=ci_photos,
        )
    except Exception as exc:
        app.logger.exception("view_ci_checklist failed: %s", exc)
        flash('Unable to load CI checklist for viewing.', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/ci/checklist/<int:id>', methods=['POST'])
@login_required
def submit_ci_checklist(id):
    """Submit the completed CI checklist"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    skip_form_keys = (
        'checklist_data', 'ci_signature', 'ci_latitude', 'ci_longitude', 'ci_photos', 'interview_photos',
    )

    conn = get_db()
    try:
        app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
        if not app_data:
            flash('Application not found', 'danger')
            return redirect(url_for('ci_dashboard'))

        app_data_dict = dict(app_data)
        if app_data_dict.get('assigned_ci_staff') != current_user.id:
            flash('Application not found', 'danger')
            return redirect(url_for('ci_dashboard'))

        checklist_raw = request.form.get('checklist_data')
        try:
            parsed_checklist = json.loads(checklist_raw) if checklist_raw else {}
            if not isinstance(parsed_checklist, dict):
                parsed_checklist = {}
        except Exception:
            parsed_checklist = {}

        for key in request.form.keys():
            if key in skip_form_keys:
                continue
            parsed_checklist[key] = request.form.get(key, '')

        try:
            checklist_data = json.dumps(parsed_checklist, default=str, ensure_ascii=False)
        except Exception as ser_err:
            app.logger.exception('checklist JSON serialize: %s', ser_err)
            flash('Could not save checklist (data too large or invalid). Try again.', 'danger')
            return redirect(url_for('ci_checklist_wizard', id=id))

        sig_candidates = [x.strip() for x in request.form.getlist('ci_signature') if x and str(x).strip()]
        ci_signature = sig_candidates[-1] if sig_candidates else (request.form.get('ci_signature') or '').strip()
        ci_latitude = request.form.get('ci_latitude') or None
        ci_longitude = request.form.get('ci_longitude') or None

        if not ci_signature:
            if current_user.signature_path:
                sig_file = (current_user.signature_path or '').replace('\\', '/').split('/')[-1]
                if sig_file:
                    ci_signature = url_for('serve_signature', filename=sig_file, _external=True)
            if not ci_signature:
                flash('Signature is required. Please update your signature on Change Password.', 'danger')
                return redirect(url_for('ci_checklist_wizard', id=id))

        conn.execute('''
            UPDATE loan_applications
            SET status=?, ci_checklist_data=?, ci_signature=?, ci_completed_at=?, ci_latitude=?, ci_longitude=?
            WHERE id=?
        ''', ('ci_completed', checklist_data, ci_signature, now_ph().isoformat(), ci_latitude, ci_longitude, id))

        uploaded_files = []
        if 'interview_photos' in request.files:
            uploaded_files.extend(request.files.getlist('interview_photos'))
        if 'ci_photos' in request.files:
            uploaded_files.extend(request.files.getlist('ci_photos'))

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{id}_ci_{uuid.uuid4().hex[:8]}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                insert_loan_document_row(
                    conn, id, filepath, filename, current_user.id
                )

        try:
            conn.execute('''
                UPDATE users SET current_workload =
                    CASE WHEN COALESCE(current_workload, 0) < 1 THEN 0 ELSE COALESCE(current_workload, 0) - 1 END
                WHERE id=?
            ''', (current_user.id,))
        except Exception as wl_err:
            # Backward compatibility for schemas that don't have current_workload yet.
            app.logger.debug('Skipping workload update during CI submit: %s', wl_err)

        conn.commit()

        try:
            la = float(app_data_dict.get('loan_amount') or 0)
        except (TypeError, ValueError):
            la = 0.0
        try:
            try:
                _ci_sb = app_data_dict.get('submitted_by')
                _ci_sb = int(_ci_sb) if _ci_sb is not None else None
            except (KeyError, TypeError, ValueError):
                _ci_sb = None
            socketio.emit('application_updated', {
                'id': id,
                'status': 'ci_completed',
                'member_name': app_data_dict.get('member_name') or '',
                'loan_amount': la,
                'submitted_by': _ci_sb,
                'timestamp': now_ph().isoformat()
            })
        except Exception as sock_err:
            app.logger.debug('socket emit after ci submit: %s', sock_err)

        try:
            notifiers = conn.execute('''
                SELECT id FROM users
                WHERE is_approved = 1 AND role IN ('loan_officer', 'admin')
                ORDER BY CASE WHEN role = 'loan_officer' THEN 0 ELSE 1 END, id
            ''').fetchall() or []
        except Exception:
            notifiers = conn.execute('''
                SELECT id FROM users
                WHERE role IN ('loan_officer', 'admin')
                ORDER BY CASE WHEN role = 'loan_officer' THEN 0 ELSE 1 END, id
            ''').fetchall() or []
        for row in notifiers:
            try:
                enqueue_notification(
                    int(row['id']),
                    f'CI interview completed for: {app_data_dict.get("member_name") or "Application"}',
                    f'/admin/application/{id}'
                )
            except Exception:
                pass

        flash('CI Checklist submitted successfully!', 'success')
        return redirect(url_for('ci_dashboard'))

    except Exception as e:
        app.logger.exception('submit_ci_checklist failed: %s', e)
        try:
            conn.rollback()
        except Exception:
            pass
        flash('Submission failed. Please try again. If it continues, contact support.', 'danger')
        return redirect(url_for('ci_checklist_wizard', id=id))
    finally:
        try:
            conn.close()
        except Exception:
            pass

# ADMIN ROUTES
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    import time as _time
    import logging as _logging
    _perf = _logging.getLogger('app.perf')

    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    _t0 = _time.monotonic()
    try:
        conn = get_db()
        _t_conn = _time.monotonic()

        # Only fetch the columns the template actually reads.
        # SELECT la.* was the primary bottleneck: it transferred ci_checklist_data,
        # admin_notes, loan_officer_notes, and other large TEXT/JSON columns for
        # every row, potentially MBs from Render's managed PostgreSQL node.
        _LA_COLS = (
            'la.id, la.status, la.member_name, la.loan_amount, la.loan_type,'
            ' la.submitted_at, la.needs_ci_interview, la.assigned_ci_staff,'
            ' u1.name AS loan_staff_name, u2.name AS ci_staff_name'
        )
        _LA_JOIN = (
            'LEFT JOIN users u1 ON la.submitted_by = u1.id'
            ' LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id'
        )

        # --- Q1: Applications ready for admin review -------------------------
        # Oldest first so new rows appear at the bottom of the table.
        applications = conn.execute(
            f'SELECT {_LA_COLS} FROM loan_applications la {_LA_JOIN}'
            " WHERE la.status IN ('ci_completed','approved','disapproved','deferred')"
            " OR (la.needs_ci_interview = 0 AND la.status = 'submitted')"
            ' ORDER BY la.submitted_at ASC, la.id ASC'
        ).fetchall()
        _t_q1 = _time.monotonic()

        # --- Q2: In-process applications (LPS → CI pipeline) -----------------
        in_process_applications = conn.execute(
            f'SELECT {_LA_COLS} FROM loan_applications la {_LA_JOIN}'
            " WHERE la.status IN ('submitted','assigned_to_ci')"
            ' ORDER BY la.submitted_at ASC, la.id ASC'
        ).fetchall()
        _t_q2 = _time.monotonic()

        # --- Q3: CI staff online status  -------------------------------------
        ci_staff = conn.execute(
            'SELECT id, name, email, is_online, last_seen, profile_photo'
            ' FROM users WHERE role = %s'
            ' ORDER BY is_online DESC, name ASC'
            if is_postgresql() else
            'SELECT id, name, email, is_online, last_seen, profile_photo'
            ' FROM users WHERE role = ?'
            ' ORDER BY is_online DESC, name ASC',
            ('ci_staff',)
        ).fetchall()
        _t_q3 = _time.monotonic()

        unread_count = get_unread_notification_count(current_user.id)
        _t_q4 = _time.monotonic()

        # Normalise submitted_at to string so templates can slice it safely
        def _norm_dt(rows):
            out = []
            for row in rows:
                d = dict(row)
                v = d.get('submitted_at')
                if isinstance(v, datetime):
                    d['submitted_at'] = v.strftime('%Y-%m-%d %H:%M:%S')
                out.append(d)
            return out

        applications = _norm_dt(applications)
        in_process_applications = _norm_dt(in_process_applications)
        _t_end = _time.monotonic()

        # Emit a WARNING whenever the full handler exceeds 500 ms so we can
        # see exactly which query is slow in Render's log stream.
        _total = _t_end - _t0
        if _total > 0.5:
            _perf.warning(
                'admin_dashboard slow %.3fs | conn=%.0fms q1(review)=%.0fms'
                ' q2(inprocess)=%.0fms q3(staff)=%.0fms q4(notif)=%.0fms norm=%.0fms',
                _total,
                (_t_conn - _t0) * 1000,
                (_t_q1 - _t_conn) * 1000,
                (_t_q2 - _t_q1) * 1000,
                (_t_q3 - _t_q2) * 1000,
                (_t_q4 - _t_q3) * 1000,
                (_t_end - _t_q4) * 1000,
            )

        return render_template(
            'admin_dashboard.html',
            applications=applications,
            in_process_applications=in_process_applications,
            ci_staff=ci_staff,
            unread_count=unread_count,
        )
    except Exception as e:
        print(f"❌ ERROR in admin_dashboard: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/admin/application/<int:id>', methods=['GET','POST'])
@login_required
def admin_application(id):
    import time as _time
    _t0 = _time.monotonic()
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    conn = get_db()
    app_data = conn.execute('''
        SELECT la.*,
               u1.name as loan_staff_name,
               u2.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u1 ON la.submitted_by = u1.id
        LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
        WHERE la.id=?
    ''', (id,)).fetchone()
    _t_q1 = _time.monotonic()
    
    if not app_data:
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        decision = request.form.get('decision')
        admin_notes = request.form.get('admin_notes')
        
        try:
            conn.execute('''
                UPDATE loan_applications 
                SET status=?, admin_notes=?, admin_decision_at=?
                WHERE id=?
            ''', (decision, admin_notes, now_ph().isoformat(), id))
            
            conn.commit()
            conn.close()

            def _emit_admin():
                try:
                    try:
                        la = float(app_data['loan_amount'] or 0)
                    except (TypeError, KeyError, ValueError):
                        la = 0.0
                    try:
                        _admin_sb = app_data['submitted_by']
                        _admin_sb = int(_admin_sb) if _admin_sb is not None else None
                    except (KeyError, TypeError, ValueError):
                        _admin_sb = None
                    socketio.emit('application_updated', {
                        'id': id,
                        'status': decision,
                        'member_name': app_data['member_name'],
                        'loan_amount': la,
                        'submitted_by': _admin_sb,
                        'timestamp': now_ph().isoformat()
                    })
                except Exception as ex:
                    app.logger.debug('background emit application_updated: %s', ex)

            run_background_task(_emit_admin)
            
            # Send SMS notification to applicant (synchronous / realtime result)
            sms_message = None
            sms_sent = None
            sms_error = None
            if app_data['member_contact']:
                if decision == 'approved':
                    try:
                        _approved_amount = float(app_data['loan_amount'] or 0)
                    except (TypeError, ValueError, KeyError):
                        _approved_amount = 0.0
                    sms_message = (
                        f"Good news! Your loan application for {app_data['member_name']} has been APPROVED. "
                        f"Amount: ₱{_approved_amount:,.2f}. Please visit DCCCO office for processing. - DCCCO Coop"
                    )
                elif decision == 'disapproved':
                    sms_message = f"We regret to inform you that your loan application for {app_data['member_name']} has been DISAPPROVED. Reason: {admin_notes[:100] if admin_notes else 'See office for details'}. - DCCCO Coop"
                else:
                    sms_message = None

                if sms_message:
                    sms_sent, sms_error = send_sms(
                        app_data['member_contact'],
                        sms_message,
                        loan_application_id=id,
                        sent_by_user_id=current_user.id,
                        category=decision,
                        member_name=(app_data['member_name'] if 'member_name' in app_data.keys() else ''),
                    )
            
            # Notify loan staff in background to keep response fast.
            run_background_task(
                create_notification,
                app_data['submitted_by'],
                f'Application {decision}: {app_data["member_name"]}',
                f'/loan/application/{id}'
            )
            
            if sms_message:
                if sms_sent:
                    flash(f'Application {decision}! SMS sent in realtime.', 'success')
                else:
                    flash(
                        f'Application {decision}. SMS failed: {sms_error or "Unknown SMS error"}',
                        'warning',
                    )
            else:
                flash(f'Application {decision}! Notifications are being sent in background.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('admin_application', id=id))
    
    try:
        # Select metadata only — avoid pulling BLOB columns into this page.
        documents = conn.execute(
            'SELECT id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at'
            ' FROM documents WHERE loan_application_id=?'
            ' ORDER BY uploaded_at DESC',
            (id,)
        ).fetchall()
    except Exception as doc_err:
        print(f"WARNING loading documents for admin_application({id}): {doc_err}")
        documents = []

    try:
        messages = conn.execute('''
            SELECT m.id, m.loan_application_id, m.message, m.sent_at,
                   m.sender_id, u.name as sender_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE m.loan_application_id=?
            ORDER BY m.sent_at ASC
            LIMIT 200
        ''', (id,)).fetchall()
    except Exception as msg_err:
        print(f"WARNING loading messages for admin_application({id}): {msg_err}")
        messages = []

    ci_staff_list = fetch_ci_staff_list(conn, include_pending=False)

    unread_count = get_unread_notification_count(current_user.id)

    _total = _time.monotonic() - _t0
    if _total > 0.5:
        _perf_logger.warning(
            'admin_application GET id=%s slow %.3fs | q1(app)=%.0fms total=%.0fms',
            id, _total, (_t_q1 - _t0) * 1000, _total * 1000,
        )

    return render_template('admin_application.html',
                           application=app_data,
                           documents=documents,
                           messages=messages,
                           ci_staff_list=ci_staff_list,
                           unread_count=unread_count)

@app.route('/reassign_ci_staff/<int:app_id>', methods=['POST'])
@login_required
def reassign_ci_staff(app_id):
    """Reassign application to different CI staff (admin/loan officer only)"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    payload = request.get_json(silent=True) or {}
    new_ci_staff_id = (
        request.form.get('new_ci_staff_id')
        or request.form.get('new_ci_staff')
        or payload.get('new_ci_staff_id')
    )
    
    if not new_ci_staff_id:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Please select a CI staff member'}), 400
        flash('Please select a CI staff member', 'warning')
        return redirect(url_for('admin_application', id=app_id))
    
    conn = get_db()
    
    try:
        # Get current assignment
        app = conn.execute('SELECT assigned_ci_staff, member_name FROM loan_applications WHERE id=?', (app_id,)).fetchone()
        old_ci_staff_id = app['assigned_ci_staff']
        
        # Update assignment
        conn.execute('''
            UPDATE loan_applications 
            SET assigned_ci_staff=? 
            WHERE id=?
        ''', (new_ci_staff_id, app_id))
        
        # Update workload counts
        if old_ci_staff_id:
            conn.execute('UPDATE users SET current_workload = current_workload - 1 WHERE id=?', (old_ci_staff_id,))
        
        conn.execute('UPDATE users SET current_workload = current_workload + 1 WHERE id=?', (new_ci_staff_id,))
        
        conn.commit()
        conn.close()
        
        # Notify new CI staff in background to keep the action snappy.
        run_background_task(
            create_notification,
            int(new_ci_staff_id),
            f'Application reassigned to you: {app["member_name"]}',
            f'/ci/application/{app_id}'
        )
        
        # Notify old CI staff if exists
        if old_ci_staff_id:
            run_background_task(
                create_notification,
                old_ci_staff_id,
                f'Application {app["member_name"]} has been reassigned',
                f'/ci/dashboard'
            )
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'CI staff reassigned successfully'})
        flash('CI staff reassigned successfully!', 'success')
        return redirect(url_for('admin_application', id=app_id))
        
    except Exception as e:
        conn.rollback()
        conn.close()
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error reassigning CI staff: {str(e)}'}), 500
        flash(f'Error reassigning CI staff: {str(e)}', 'danger')
        return redirect(url_for('admin_application', id=app_id))

# SHARED ROUTES
@app.route('/application/<int:id>')
@login_required
def view_application(id):
    if current_user.role in ['admin', 'loan_officer']:
        return redirect(url_for('admin_application', id=id))
    elif current_user.role == 'ci_staff':
        return redirect(url_for('ci_application', id=id))
    else:
        return redirect(url_for('loan_application', id=id))

@app.route('/loan/application/<int:id>', methods=['GET', 'POST'])
@login_required
def loan_application(id):
    if current_user.role != 'loan_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('''
        SELECT la.*, u.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.assigned_ci_staff = u.id
        WHERE la.id=? AND la.submitted_by=?
    ''', (id, current_user.id)).fetchone()
    
    if not app_data:
        flash('Application not found or you do not have permission to edit it', 'danger')
        conn.close()
        return redirect(url_for('loan_dashboard'))
    
    # Handle POST request (update application)
    if request.method == 'POST':
        # Check if application can still be edited
        if app_data['status'] not in ['submitted', 'assigned_to_ci']:
            flash('Cannot edit application - it has already been processed by CI or admin', 'warning')
            conn.close()
            return redirect(url_for('loan_application', id=id))
        
        try:
            member_name = request.form['member_name']
            _mc_raw = request.form.get('member_contact')
            member_contact = _sanitize_optional_ph_mobile_input(_mc_raw)
            if member_contact is None:
                conn.close()
                flash(
                    'Contact number must be 11 digits starting with 09 (e.g. 09751762630). '
                    'Leave blank if unknown.',
                    'danger',
                )
                return redirect(url_for('loan_application', id=id))
            member_address = request.form.get('member_address')
            loan_amount = request.form.get('loan_amount')
            loan_type = request.form.get('loan_type')
            needs_ci_value = request.form.get('needs_ci', '1')
            
            # Check for duplicate member name (excluding current application)
            existing = conn.execute('''
                SELECT id, member_name FROM loan_applications 
                WHERE LOWER(member_name) = LOWER(?) 
                AND status NOT IN ('disapproved', 'approved')
                AND id != ?
            ''', (member_name, id)).fetchone()
            
            if existing:
                conn.close()
                flash(f'An active application for "{member_name}" already exists (ID: #{existing["id"]}). Please use a different name.', 'warning')
                return redirect(url_for('loan_application', id=id))
            
            # Check if specific CI staff was selected
            specific_ci_id = None
            if needs_ci_value.startswith('ci_'):
                specific_ci_id = int(needs_ci_value.replace('ci_', ''))
                needs_ci = 1
            else:
                needs_ci = int(needs_ci_value)
            
            # Update application
            conn.execute('''
                UPDATE loan_applications 
                SET member_name=?, member_contact=?, member_address=?, 
                    loan_amount=?, loan_type=?, needs_ci_interview=?
                WHERE id=?
            ''', (member_name, member_contact, member_address, loan_amount, loan_type, needs_ci, id))
            
            # Handle new file uploads
            if 'documents' in request.files:
                files = request.files.getlist('documents')
                for file in files:
                    if file and file.filename:
                        if not allowed_file(file.filename):
                            conn.rollback()
                            conn.close()
                            flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, PDF, DOC, DOCX', 'danger')
                            return redirect(url_for('loan_application', id=id))
                        
                        filename = sanitize_filename(file.filename)
                        unique_filename = f"{id}_{uuid.uuid4().hex[:8]}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(filepath)
                        insert_loan_document_row(
                            conn, id, filepath, filename, current_user.id
                        )
            
            # Update CI staff assignment if changed
            old_ci_staff = app_data['assigned_ci_staff']
            new_ci_staff_id = None
            
            if needs_ci:
                if specific_ci_id:
                    new_ci_staff_id = specific_ci_id
                else:
                    # Route-based assignment (same resolver as LPS submit_application)
                    if member_address:
                        matched_route = resolve_ci_route_key_for_member_address(member_address)
                        if matched_route:
                            new_ci_staff_id = fetch_first_ci_staff_id_for_route_key(conn, matched_route)

                    # Fallback to workload-based
                    if not new_ci_staff_id:
                        ci_staff = conn.execute('''
                            SELECT id FROM users 
                            WHERE role='ci_staff' AND is_approved=1
                            ORDER BY current_workload ASC 
                            LIMIT 1
                        ''').fetchone()
                        new_ci_staff_id = ci_staff['id'] if ci_staff else None
                
                # Update CI staff assignment if changed
                if new_ci_staff_id and new_ci_staff_id != old_ci_staff:
                    # Decrease old CI staff workload
                    if old_ci_staff:
                        conn.execute('UPDATE users SET current_workload = current_workload - 1 WHERE id=?', (old_ci_staff,))
                    
                    # Increase new CI staff workload
                    conn.execute('UPDATE users SET current_workload = current_workload + 1 WHERE id=?', (new_ci_staff_id,))
                    
                    # Update assignment
                    conn.execute('UPDATE loan_applications SET assigned_ci_staff=?, status=? WHERE id=?',
                               (new_ci_staff_id, 'assigned_to_ci', id))
                    
                    # Notify new CI staff
                    enqueue_notification(
                        new_ci_staff_id,
                        f'Loan application reassigned to you: {member_name}',
                        f'/ci/application/{id}'
                    )
            
            conn.commit()
            conn.close()
            
            flash('Application updated successfully!', 'success')
            try:
                _lps = app_data['submitted_by'] if app_data else None
                _lps = int(_lps) if _lps is not None else None
            except (KeyError, TypeError, ValueError):
                _lps = None
            socketio.emit('application_updated', {
                'id': id,
                'member_name': member_name,
                'submitted_by': _lps,
            })
            
            return redirect(url_for('loan_application', id=id))
            
        except Exception as e:
            print(f"ERROR updating application: {str(e)}")
            import traceback
            traceback.print_exc()
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            flash(f'Error updating application: {str(e)}', 'danger')
            return redirect(url_for('loan_application', id=id))
    
    # GET request - show form (exclude file_data BLOBs from listing)
    documents = conn.execute(
        'SELECT id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at, mime_type '
        'FROM documents WHERE loan_application_id=? ORDER BY uploaded_at ASC',
        (id,),
    ).fetchall()
    messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.loan_application_id=?
        ORDER BY m.sent_at ASC
    ''', (id,)).fetchall()
    
    # Get all CI staff for dropdown
    ci_staff_list = conn.execute('''
        SELECT id, name, email, is_approved 
        FROM users 
        WHERE role='ci_staff' 
        ORDER BY name ASC
    ''').fetchall()
    
    row = conn.execute("SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'",
                                (current_user.id,)).fetchone()
    unread_count = row['count'] if row else 0
    conn.close()
    
    # Check if application can be edited
    can_edit = app_data['status'] in ['submitted', 'assigned_to_ci']
    
    return render_template('loan_application.html', 
                         application=app_data, 
                         documents=documents, 
                         messages=messages, 
                         unread_count=unread_count,
                         ci_staff_list=ci_staff_list,
                         can_edit=can_edit)

@app.route('/messages')
@login_required
def messages():
    import time as _time
    _t0 = _time.monotonic()
    conn = get_db()
    try:
        staff = conn.execute('''
            SELECT id, name, email, role, profile_photo
            FROM users
            WHERE id != ?
              AND is_approved = 1
              AND role IN ('admin', 'loan_officer', 'loan_staff', 'ci_staff')
            ORDER BY name
        ''', (current_user.id,)).fetchall()
        _t_q1 = _time.monotonic()

        conversations = []
        latest_rows = conn.execute('''
            SELECT other_id, message, sent_at
            FROM (
                SELECT
                    CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS other_id,
                    message,
                    sent_at,
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END
                        ORDER BY sent_at DESC, id DESC
                    ) AS rn
                FROM direct_messages
                WHERE sender_id = ? OR receiver_id = ?
            ) ranked
            WHERE rn = 1
            ORDER BY sent_at DESC
            LIMIT 50
        ''', (current_user.id, current_user.id, current_user.id, current_user.id)).fetchall()

        chat_user_ids = []
        for row in latest_rows or []:
            try:
                other_id = row['other_id']
            except (KeyError, IndexError, TypeError):
                other_id = None
            if other_id is not None:
                chat_user_ids.append(other_id)
        if chat_user_ids:
            placeholders = ','.join(['?'] * len(chat_user_ids))
            latest_map = {row['other_id']: row for row in latest_rows}

            user_rows = conn.execute(
                f'''
                SELECT id, name, role, profile_photo
                FROM users
                WHERE id IN ({placeholders})
                  AND is_approved = 1
                ''',
                tuple(chat_user_ids)
            ).fetchall()
            user_map = {u['id']: u for u in user_rows}

            unread_rows = conn.execute(
                f'''
                SELECT sender_id as other_id, COUNT(*) as count
                FROM direct_messages
                WHERE receiver_id = ? AND is_read = 0 AND sender_id IN ({placeholders})
                GROUP BY sender_id
                ''',
                (current_user.id, *chat_user_ids)
            ).fetchall()
            unread_map = {row['other_id']: row['count'] for row in unread_rows}

            for other_id in chat_user_ids:
                user_info = user_map.get(other_id)
                if not user_info:
                    continue
                last_msg = latest_map.get(other_id)
                conversations.append({
                    'other_user_id': other_id,
                    'other_user_name': user_info['name'],
                    'other_user_role': user_info['role'],
                    'other_user_photo': user_info['profile_photo'],
                    'last_message': last_msg['message'] if last_msg else '',
                    'last_message_time': last_msg['sent_at'] if last_msg else '',
                    'unread_count': unread_map.get(other_id, 0)
                })
        
        _total = _time.monotonic() - _t0
        if _total > 0.5:
            _perf_logger.warning(
                'messages slow %.3fs | staff_list=%.0fms window_cte=%.0fms',
                _total, (_t_q1 - _t0) * 1000, (_time.monotonic() - _t_q1) * 1000,
            )

        return render_template('messages_dark.html', staff=staff, conversations=conversations, unread_count=0)
    except Exception as e:
        print(f"ERROR loading messages page: {e}")
        flash('Could not load messages right now. Please try again.', 'warning')
        return redirect(url_for('index'))
    finally:
        conn.close()

@app.route('/messages/<int:user_id>')
@login_required
def chat_with_user(user_id):
    conn = get_db()
    try:
        other_user = conn.execute(
            'SELECT id, name, email, role, profile_photo FROM users WHERE id=?',
            (user_id,)
        ).fetchone()
        if not other_user:
            flash('That user is no longer available.', 'warning')
            return redirect(url_for('messages'))

        other_user = dict(other_user)
        other_user.setdefault('id', user_id)
        if not other_user.get('name'):
            other_user['name'] = other_user.get('email') or 'User'
        if not other_user.get('role'):
            other_user['role'] = 'user'

        # Limit to last 200 messages; full history causes large data transfers with no benefit.
        messages = conn.execute('''
            SELECT dm.id, dm.sender_id, dm.receiver_id, dm.message,
                   dm.sent_at, dm.is_read, dm.is_edited, dm.edited_at,
                   COALESCE(u.name, '') as sender_name
            FROM direct_messages dm
            LEFT JOIN users u ON dm.sender_id = u.id
            WHERE (dm.sender_id = ? AND dm.receiver_id = ?)
               OR (dm.sender_id = ? AND dm.receiver_id = ?)
            ORDER BY dm.sent_at DESC
            LIMIT 200
        ''', (current_user.id, user_id, user_id, current_user.id)).fetchall()
        # Reverse so oldest-first in the template (DESC + LIMIT, then flip is faster than ASC over full table)
        messages = list(reversed(messages)) if messages else []

        safe_messages = []
        for msg in messages or []:
            m = dict(msg)
            sent_at = m.get('sent_at')
            if isinstance(sent_at, datetime):
                m['sent_at'] = naive_utc_iso_z(sent_at)
            elif sent_at is None:
                m['sent_at'] = ''
            safe_messages.append(m)

        conn.execute('''
            UPDATE direct_messages
            SET is_read = 1
            WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
        ''', (user_id, current_user.id))
        conn.commit()
        return render_template(
            'chat.html',
            other_user=other_user,
            messages=safe_messages,
            unread_count=0,
        )
    except Exception as e:
        print(f"ERROR loading chat with user {user_id}: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        flash('Could not load this conversation right now. Please try again.', 'warning')
        return redirect(url_for('messages'))
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/notifications')
@login_required
def notifications():
    conn = get_db()
    try:
        rows = conn.execute('''
            SELECT * FROM notifications
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 50
        ''', (current_user.id,)).fetchall()

        notifs = []
        for r in rows:
            item = dict(r)
            link = (item.get('link') or '').strip()
            # Normalise legacy links so clicking always goes somewhere real.
            if not link or link in ('#', 'None'):
                item['link'] = url_for('index')
            else:
                item['link'] = link
            ts = item.get('created_at')
            if ts and not isinstance(ts, str):
                try:
                    item['created_at'] = ts.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    item['created_at'] = str(ts)
            notifs.append(item)

        unread_in_list = sum(1 for n in notifs if not n.get('is_read'))
        return render_template(
            'notifications.html',
            notifications=notifs,
            unread_count=unread_in_list,
        )
    except Exception as exc:
        app.logger.exception("notifications list failed: %s", exc)
        flash('Unable to load notifications right now.', 'danger')
        return redirect(url_for('index'))
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/notifications/mark_all_read', methods=['POST'])
@login_required
def api_mark_all_notifications_read():
    conn = get_db()
    try:
        conn.execute('UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0', (current_user.id,))
        conn.commit()
        try:
            _clear_cached_count(_notification_count_cache, current_user.id)
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as exc:
        app.logger.exception("mark_all_notifications_read failed: %s", exc)
        return jsonify({'success': False, 'error': 'server_error'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/api/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def api_mark_notification_read(notif_id):
    conn = get_db()
    try:
        conn.execute('UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?',
                     (notif_id, current_user.id))
        conn.commit()
        try:
            _clear_cached_count(_notification_count_cache, current_user.id)
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as exc:
        app.logger.exception("mark_notification_read failed: %s", exc)
        return jsonify({'success': False, 'error': 'server_error'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/ci-tracking')
@login_required
def ci_tracking():
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get all CI staff with their latest location
    ci_staff = conn.execute('''
        SELECT 
            u.id, u.name, u.email,
            lt.latitude, lt.longitude, lt.activity, lt.tracked_at,
            (SELECT COUNT(*) FROM loan_applications WHERE assigned_ci_staff = u.id AND status = 'assigned_to_ci') as active_cases
        FROM users u
        LEFT JOIN location_tracking lt ON u.id = lt.user_id
        WHERE u.role = 'ci_staff'
        AND (lt.id IS NULL OR lt.id = (
            SELECT id FROM location_tracking 
            WHERE user_id = u.id 
            ORDER BY tracked_at DESC 
            LIMIT 1
        ))
        ORDER BY u.name
    ''').fetchall()
    
    conn.close()
    
    gmaps_key = (os.getenv('GOOGLE_MAPS_API_KEY') or os.getenv('GOOGLE_MAPS_KEY') or '').strip()
    return render_template('ci_tracking.html', ci_staff=ci_staff, unread_count=0, google_maps_api_key=gmaps_key)

@app.route('/api/update_location', methods=['POST'])
@login_required
def update_location():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    activity = data.get('activity', 'Active')
    
    if not latitude or not longitude:
        return jsonify({'success': False, 'error': 'Missing coordinates'})
    
    conn = get_db()
    conn.execute('''
        INSERT INTO location_tracking (user_id, latitude, longitude, activity)
        VALUES (?, ?, ?, ?)
    ''', (current_user.id, latitude, longitude, activity))
    conn.commit()
    conn.close()
    
    # Emit realtime location update to admin tracking room
    from datetime import datetime
    socketio.emit('ci_location_update', {
        'user_id': current_user.id,
        'name': current_user.name,
        'latitude': latitude,
        'longitude': longitude,
        'activity': activity,
        'tracked_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }, room='admin_tracking')
    
    return jsonify({'success': True})

@app.route('/api/online_users')
@login_required
def get_online_users():
    """Get list of currently online users"""
    conn = get_db()
    users = conn.execute('''
        SELECT id, name, role, is_online, last_seen 
        FROM users 
        WHERE id != ?
        ORDER BY is_online DESC, last_seen DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return jsonify({
        'online_users': [dict(u) for u in users if u['is_online']],
        'all_users': [dict(u) for u in users]
    })

@app.route('/api/get_messages/<int:user_id>')
@login_required
def get_messages(user_id):
    try:
        conn = get_db()
        try:
            messages = conn.execute('''
                SELECT dm.*, COALESCE(u.name, '') as sender_name
                FROM direct_messages dm
                LEFT JOIN users u ON dm.sender_id = u.id
                WHERE (dm.sender_id = ? AND dm.receiver_id = ?)
                   OR (dm.sender_id = ? AND dm.receiver_id = ?)
                ORDER BY dm.sent_at ASC
            ''', (current_user.id, user_id, user_id, current_user.id)).fetchall()
            conn.execute('''
                UPDATE direct_messages
                SET is_read = 1
                WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
            ''', (user_id, current_user.id))
            conn.commit()
        finally:
            conn.close()

        safe = []
        for msg in messages or []:
            m = dict(msg)
            for field in ('sent_at', 'edited_at'):
                value = m.get(field)
                if isinstance(value, datetime):
                    m[field] = naive_utc_iso_z(value)
                elif value is None:
                    m[field] = ''
            safe.append(m)
        return jsonify({'success': True, 'messages': safe})
    except Exception as e:
        print(f"ERROR get_messages: {e}")
        return jsonify({'success': False, 'error': 'Could not load messages', 'messages': []}), 500

@app.route('/api/mark_messages_read/<int:sender_id>', methods=['POST'])
@login_required
def mark_messages_read(sender_id):
    conn = get_db()
    conn.execute('''
        UPDATE direct_messages SET is_read = 1
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (sender_id, current_user.id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/unread_message_count')
@login_required
def unread_message_count():
    conn = get_db()
    row = conn.execute('''
        SELECT COUNT(*) as count FROM direct_messages
        WHERE receiver_id = ? AND is_read = 0
    ''', (current_user.id,)).fetchone()
    conn.close()
    return jsonify({'count': row['count'] if row else 0})

@app.route('/api/unread_messages_count')
@login_required
def unread_messages_count():
    conn = get_db()
    row = conn.execute('SELECT COUNT(*) as count FROM direct_messages WHERE receiver_id=? AND is_read=0 AND is_deleted=0', (current_user.id,)).fetchone()
    count = row['count'] if row else 0
    conn.close()
    return jsonify({'count': count})


def _delete_loan_application_cascade(conn, app_id, status=None, assigned_ci_staff=None):
    """
    Delete one loan_applications row and related documents/messages/sms logs.
    Decrements CI workload when deleting assigned_to_ci rows.
    Returns True if the application row was removed.
    """
    if status is None:
        row = conn.execute(
            'SELECT id, status, assigned_ci_staff FROM loan_applications WHERE id=?',
            (app_id,),
        ).fetchone()
        if not row:
            return False
        status = row.get('status')
        assigned_ci_staff = row.get('assigned_ci_staff')
    st = (status or '').strip()
    ci = assigned_ci_staff
    if st == 'assigned_to_ci' and ci:
        try:
            conn.execute(
                '''
                UPDATE users SET current_workload =
                    CASE WHEN COALESCE(current_workload, 0) < 1 THEN 0
                         ELSE COALESCE(current_workload, 0) - 1 END
                WHERE id=?
                ''',
                (ci,),
            )
        except Exception:
            pass
    for q in (
        'DELETE FROM documents WHERE loan_application_id=?',
        'DELETE FROM messages WHERE loan_application_id=?',
    ):
        try:
            conn.execute(q, (app_id,))
        except Exception:
            pass
    try:
        conn.execute('DELETE FROM sms_sent_log WHERE loan_application_id=?', (app_id,))
    except Exception:
        pass
    try:
        conn.execute('DELETE FROM loan_applications WHERE id=?', (app_id,))
        return True
    except Exception:
        return False


_MEMBER_NAME_DEDUPE_STATUS_RANK = {
    'approved': 1,
    'ci_completed': 2,
    'assigned_to_ci': 3,
    'submitted': 4,
    'deferred': 5,
    'disapproved': 6,
    'rejected': 6,
}


def _member_name_dedupe_rank(status):
    st = (status or '').strip().lower()
    return _MEMBER_NAME_DEDUPE_STATUS_RANK.get(st, 50)


def dedupe_loan_applications_by_member_name(conn):
    """
    For each normalized member_name that appears more than once, keep a single row:
    best workflow status (approved > ci_completed > …), then highest id as tie-breaker.
    Removes related documents/messages/sms rows and adjusts CI workload when needed.
    Returns number of loan_applications rows deleted.
    """
    dup_keys = conn.execute(
        '''
        SELECT nk FROM (
            SELECT LOWER(TRIM(COALESCE(member_name, ''))) AS nk
            FROM loan_applications
            WHERE LENGTH(TRIM(COALESCE(member_name, ''))) >= 2
        ) x
        GROUP BY nk
        HAVING COUNT(*) > 1
        '''
    ).fetchall()
    deleted = 0
    for drow in dup_keys or []:
        nk = (drow['nk'] if drow else '') or ''
        nk = str(nk).strip()
        if not nk:
            continue
        apps = conn.execute(
            '''
            SELECT id, status, assigned_ci_staff FROM loan_applications
            WHERE LOWER(TRIM(COALESCE(member_name, ''))) = ?
            ''',
            (nk,),
        ).fetchall()
        if not apps or len(apps) < 2:
            continue
        apps_sorted = sorted(
            apps,
            key=lambda r: (
                _member_name_dedupe_rank(r.get('status')),
                -int(r['id']),
            ),
        )
        for r in apps_sorted[1:]:
            if _delete_loan_application_cascade(
                conn, r['id'], r.get('status'), r.get('assigned_ci_staff')
            ):
                deleted += 1
    return deleted


def _purge_nonfinal_duplicate_applications(conn, member_name):
    """
    Remove non-final rows with the same member name (trimmed, case-insensitive)
    before a new submit so duplicate pipeline records are not kept.
    Decrements CI workload when deleting assigned_to_ci rows.
    Returns number of loan_applications rows deleted.
    """
    key = (member_name or '').strip()
    if len(key) < 2:
        return 0
    rows = conn.execute(
        '''
        SELECT id, assigned_ci_staff, status FROM loan_applications
        WHERE LOWER(TRIM(COALESCE(member_name, ''))) = LOWER(TRIM(?))
          AND status IN ('submitted', 'assigned_to_ci', 'deferred')
        ''',
        (key,),
    ).fetchall()
    deleted = 0
    for r in rows or []:
        if _delete_loan_application_cascade(conn, r['id'], r.get('status'), r.get('assigned_ci_staff')):
            deleted += 1
    return deleted


def _insert_loan_application(
    conn,
    member_name,
    member_contact,
    member_address,
    loan_amount,
    loan_type,
    lps_remarks,
    needs_ci,
    submitted_by_id,
):
    """
    Insert a new row into loan_applications and return the new id.
    PostgreSQL: psycopg2 cursors have no lastrowid — must use RETURNING id.
    """
    status = "submitted"
    # Coerce amount for DB drivers (RealDictCursor / numeric columns).
    try:
        amt = float(loan_amount) if loan_amount is not None and str(loan_amount).strip() != "" else 0.0
    except (TypeError, ValueError):
        amt = 0.0
    needs_flag = 1 if int(needs_ci) else 0

    if is_postgresql():
        cursor = conn.execute(
            """
            INSERT INTO loan_applications
            (member_name, member_contact, member_address, loan_amount, loan_type,
             lps_remarks, needs_ci_interview, submitted_by, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                member_name,
                member_contact,
                member_address,
                amt,
                loan_type,
                lps_remarks or "",
                needs_flag,
                submitted_by_id,
                status,
            ),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        try:
            return int(row["id"])
        except Exception:
            try:
                return int(row[0])
            except Exception:
                return None

    cursor = conn.execute(
        """
        INSERT INTO loan_applications
        (member_name, member_contact, member_address, loan_amount, loan_type,
         lps_remarks, needs_ci_interview, submitted_by, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            member_name,
            member_contact,
            member_address,
            amt,
            loan_type,
            lps_remarks or "",
            needs_flag,
            submitted_by_id,
            status,
        ),
    )
    return getattr(cursor, "lastrowid", None)


def _insert_direct_message(conn, sender_id, receiver_id, message, message_type='text', file_path=None, file_name=None):
    """Insert a direct message in a DB-agnostic way and return the new id."""
    if is_postgresql():
        cursor = conn.execute('''
            INSERT INTO direct_messages (sender_id, receiver_id, message, message_type, file_path, file_name)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
        ''', (sender_id, receiver_id, message, message_type, file_path, file_name))
        row = cursor.fetchone()
        msg_id = None
        if row is not None:
            try:
                msg_id = row['id']
            except Exception:
                try:
                    msg_id = row[0]
                except Exception:
                    msg_id = None
        return msg_id
    cursor = conn.execute('''
        INSERT INTO direct_messages (sender_id, receiver_id, message, message_type, file_path, file_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (sender_id, receiver_id, message, message_type, file_path, file_name))
    return getattr(cursor, 'lastrowid', None)


@app.route('/api/send_direct_message', methods=['POST'])
@login_required
def send_direct_message():
    data = request.get_json(silent=True) or {}
    try:
        receiver_id_raw = data.get('receiver_id')
        message = (data.get('message') or '').strip()
        if not receiver_id_raw or not message:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        try:
            receiver_id = int(receiver_id_raw)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid receiver'}), 400
        if receiver_id == current_user.id:
            return jsonify({'success': False, 'error': 'Cannot message yourself'}), 400

        conn = get_db()
        try:
            receiver = conn.execute('SELECT id FROM users WHERE id=?', (receiver_id,)).fetchone()
            if not receiver:
                return jsonify({'success': False, 'error': 'Receiver not found'}), 404

            msg_id = _insert_direct_message(conn, current_user.id, receiver_id, message)
            conn.commit()
        finally:
            conn.close()

        payload = {
            'message_id': msg_id,
            'sender_id': current_user.id,
            'sender_name': current_user.name,
            'receiver_id': receiver_id,
            'message': message,
            'timestamp': naive_utc_iso_z(),
        }
        try:
            socketio.emit('new_direct_message', payload, room=str(receiver_id))
            socketio.emit('new_direct_message', payload, room=str(current_user.id))
        except Exception as emit_err:
            print(f"WARN socket emit failed in send_direct_message: {emit_err}")

        return jsonify({'success': True, 'message_id': msg_id})
    except Exception as e:
        print(f"ERROR send_direct_message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Could not send message'}), 500

@app.route('/api/send_image_message', methods=['POST'])
@login_required
def send_image_message():
    try:
        receiver_id_raw = request.form.get('receiver_id')
        if not receiver_id_raw or 'image' not in request.files:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        try:
            receiver_id = int(receiver_id_raw)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid receiver'}), 400

        file = request.files['image']
        if not file or not file.filename:
            return jsonify({'success': False, 'error': 'No file'}), 400

        filename = secure_filename(file.filename) or 'image.bin'
        unique_filename = f"dm_img_{current_user.id}_{uuid.uuid4().hex[:8]}_{filename}"
        os.makedirs('message_attachments', exist_ok=True)
        filepath = os.path.join('message_attachments', unique_filename)
        file.save(filepath)

        conn = get_db()
        try:
            msg_id = _insert_direct_message(
                conn, current_user.id, receiver_id, '[Image]',
                message_type='image', file_path=filepath, file_name=filename,
            )
            conn.commit()
        finally:
            conn.close()

        payload = {
            'message_id': msg_id,
            'sender_id': current_user.id,
            'sender_name': current_user.name,
            'receiver_id': receiver_id,
            'message': '[Image]',
            'message_type': 'image',
            'file_name': filename,
            'timestamp': naive_utc_iso_z(),
        }
        try:
            socketio.emit('new_direct_message', payload, room=str(receiver_id))
            socketio.emit('new_direct_message', payload, room=str(current_user.id))
        except Exception:
            pass

        return jsonify({'success': True, 'message_id': msg_id})
    except Exception as e:
        print(f"ERROR send_image_message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Could not send image'}), 500

@app.route('/api/send_voice_message', methods=['POST'])
@login_required
def send_voice_message():
    try:
        receiver_id_raw = request.form.get('receiver_id')
        if not receiver_id_raw or 'voice' not in request.files:
            return jsonify({'success': False, 'error': 'Missing data'}), 400
        try:
            receiver_id = int(receiver_id_raw)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid receiver'}), 400

        file = request.files['voice']
        if not file:
            return jsonify({'success': False, 'error': 'No file'}), 400

        unique_filename = f"voice_dm_{current_user.id}_{uuid.uuid4().hex[:8]}.webm"
        os.makedirs('voice_messages', exist_ok=True)
        filepath = os.path.join('voice_messages', unique_filename)
        file.save(filepath)

        conn = get_db()
        try:
            msg_id = _insert_direct_message(
                conn, current_user.id, receiver_id, '[Voice Message]',
                message_type='voice', file_path=filepath,
            )
            conn.commit()
        finally:
            conn.close()

        payload = {
            'message_id': msg_id,
            'sender_id': current_user.id,
            'sender_name': current_user.name,
            'receiver_id': receiver_id,
            'message': '[Voice Message]',
            'message_type': 'voice',
            'timestamp': naive_utc_iso_z(),
        }
        try:
            socketio.emit('new_direct_message', payload, room=str(receiver_id))
            socketio.emit('new_direct_message', payload, room=str(current_user.id))
        except Exception:
            pass

        return jsonify({'success': True, 'message_id': msg_id})
    except Exception as e:
        print(f"ERROR send_voice_message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Could not send voice message'}), 500

@app.route('/api/edit_direct_message', methods=['POST'])
@login_required
def edit_direct_message():
    try:
        data = request.get_json(silent=True) or {}
        message_id = data.get('message_id')
        new_text = (data.get('new_text') or '').strip()
        if not message_id or not new_text:
            return jsonify({'success': False, 'error': 'Missing data'}), 400

        conn = get_db()
        try:
            msg = conn.execute(
                'SELECT sender_id, receiver_id FROM direct_messages WHERE id=?',
                (message_id,)
            ).fetchone()
            if not msg or msg['sender_id'] != current_user.id:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
            conn.execute('''
                UPDATE direct_messages
                SET message=?, is_edited=1, edited_at=?
                WHERE id=?
            ''', (new_text, now_ph().isoformat(), message_id))
            conn.commit()
            receiver_id = msg['receiver_id']
        finally:
            conn.close()

        payload = {'message_id': message_id, 'new_text': new_text}
        try:
            socketio.emit('message_edited', payload, room=str(current_user.id))
            socketio.emit('message_edited', payload, room=str(receiver_id))
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR edit_direct_message: {e}")
        return jsonify({'success': False, 'error': 'Could not edit message'}), 500

@app.route('/api/delete_direct_message', methods=['POST'])
@login_required
def delete_direct_message():
    try:
        data = request.get_json(silent=True) or {}
        message_id = data.get('message_id')
        if not message_id:
            return jsonify({'success': False, 'error': 'Missing message id'}), 400

        conn = get_db()
        try:
            msg = conn.execute(
                'SELECT sender_id, receiver_id FROM direct_messages WHERE id=?',
                (message_id,)
            ).fetchone()
            if not msg or msg['sender_id'] != current_user.id:
                return jsonify({'success': False, 'error': 'Unauthorized'}), 403
            conn.execute('UPDATE direct_messages SET is_deleted=1 WHERE id=?', (message_id,))
            conn.commit()
            receiver_id = msg['receiver_id']
        finally:
            conn.close()

        payload = {'message_id': message_id}
        try:
            socketio.emit('message_deleted', payload, room=str(current_user.id))
            socketio.emit('message_deleted', payload, room=str(receiver_id))
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR delete_direct_message: {e}")
        return jsonify({'success': False, 'error': 'Could not delete message'}), 500

@app.route('/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    conn = get_db()
    doc = conn.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
    conn.close()
    
    if not doc:
        flash('Document not found', 'danger')
        return redirect(url_for('index'))
    if not _user_can_access_application(current_user.id, current_user.role, doc['loan_application_id']):
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    bd = blob_bytes(doc)
    if bd is not None:
        mime = mime_type_from_document_row(doc)
        return send_file(
            BytesIO(bd),
            mimetype=mime,
            as_attachment=True,
            download_name=(doc['file_name'] or 'document').strip() or 'document',
        )

    # Validate file path is within upload folder (prevent path traversal)
    file_path = doc['file_path']
    upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
    requested_path = os.path.abspath(file_path)
    
    if not _is_path_within_directory(upload_folder, requested_path):
        flash('Invalid file path', 'danger')
        return redirect(url_for('index'))
    
    try:
        return send_file(file_path, as_attachment=True, download_name=doc['file_name'])
    except Exception:
        flash('File not found on server', 'danger')
        return redirect(url_for('index'))


@app.route('/view_document/<int:doc_id>')
@login_required
def view_loan_document(doc_id):
    """
    Serve a loan application document inline (images, PDF).
    Prefer bytes in DB (file_data) when present; else filesystem path.
    """
    conn = get_db()
    doc = conn.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
    conn.close()
    if not doc:
        abort(404)
    app_id = doc['loan_application_id']
    if not _user_can_access_application(current_user.id, current_user.role, app_id):
        abort(403)

    bd = blob_bytes(doc)
    fname = (doc['file_name'] or '') or 'document'
    if bd is not None:
        mt = mime_type_from_document_row(doc, fname)
        try:
            return send_file(
                BytesIO(bd),
                mimetype=mt,
                as_attachment=False,
                download_name=fname,
                max_age=0,
            )
        except Exception:
            abort(404)

    file_path = doc['file_path']
    if not file_path:
        abort(404)
    upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
    requested_path = os.path.abspath(str(file_path))
    if not _is_path_within_directory(upload_folder, requested_path):
        abort(403)
    if not os.path.isfile(requested_path):
        abort(404)
    fname = (doc['file_name'] or '') or os.path.basename(requested_path)
    mimetype, _ = mimetypes.guess_type(fname)
    if not mimetype:
        low = fname.lower()
        if low.endswith(('.jpg', '.jpeg')):
            mimetype = 'image/jpeg'
        elif low.endswith('.png'):
            mimetype = 'image/png'
        elif low.endswith('.gif'):
            mimetype = 'image/gif'
        elif low.endswith('.webp'):
            mimetype = 'image/webp'
        elif low.endswith('.pdf'):
            mimetype = 'application/pdf'
        else:
            mimetype = 'application/octet-stream'
    try:
        return send_file(
            requested_path,
            mimetype=mimetype,
            as_attachment=False,
            download_name=fname,
            max_age=0,
        )
    except OSError:
        abort(404)


@app.route('/loan/application/<int:app_id>/document/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_lps_document(app_id, doc_id):
    """Allow LPS to remove their own uploaded document while app is editable."""
    if current_user.role != 'loan_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        app_data = conn.execute(
            'SELECT id, submitted_by, status FROM loan_applications WHERE id=? AND submitted_by=?',
            (app_id, current_user.id),
        ).fetchone()
        if not app_data:
            flash('Application not found or you do not have permission to edit it', 'danger')
            conn.close()
            return redirect(url_for('loan_dashboard'))

        if app_data['status'] not in ['submitted', 'assigned_to_ci']:
            flash('Cannot remove photos after CI/Admin processing has started', 'warning')
            conn.close()
            return redirect(url_for('loan_application', id=app_id))

        doc = conn.execute(
            'SELECT * FROM documents WHERE id=? AND loan_application_id=?',
            (doc_id, app_id),
        ).fetchone()
        if not doc:
            flash('Document not found', 'warning')
            conn.close()
            return redirect(url_for('loan_application', id=app_id))

        uploaded_by = doc['uploaded_by'] if 'uploaded_by' in doc.keys() else None
        if uploaded_by is not None and int(uploaded_by) != int(current_user.id):
            flash('You can only remove files uploaded by your account', 'danger')
            conn.close()
            return redirect(url_for('loan_application', id=app_id))

        file_path = doc['file_path']
        if not file_path:
            conn.execute('DELETE FROM documents WHERE id=? AND loan_application_id=?', (doc_id, app_id))
            conn.commit()
            conn.close()
            flash('Photo/document removed successfully.', 'success')
            return redirect(url_for('loan_application', id=app_id))

        upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
        requested_path = os.path.abspath(file_path)
        if not _is_path_within_directory(upload_folder, requested_path):
            flash('Invalid file path', 'danger')
            conn.close()
            return redirect(url_for('loan_application', id=app_id))

        conn.execute('DELETE FROM documents WHERE id=? AND loan_application_id=?', (doc_id, app_id))
        conn.commit()
        conn.close()

        try:
            if os.path.isfile(requested_path):
                os.remove(requested_path)
        except Exception as remove_err:
            app.logger.debug('LPS document file delete skipped: %s', remove_err)

        socketio.emit('application_updated', {
            'id': app_id,
            'submitted_by': int(current_user.id),
            'documents_updated': True,
        })
        flash('Photo/document removed successfully.', 'success')
        return redirect(url_for('loan_application', id=app_id))
    except Exception as e:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        app.logger.exception('delete_lps_document failed: %s', e)
        flash('Could not remove the selected photo/document. Please try again.', 'danger')
        return redirect(url_for('loan_application', id=app_id))

@app.route('/signatures/<path:filename>')
@login_required
def serve_signature(filename):
    """Serve signature images (auth required; no directory listing)."""
    sig_folder = os.path.abspath(app.config['SIGNATURE_FOLDER'])
    file_path = os.path.normpath(os.path.join(sig_folder, filename))
    if not _is_path_within_directory(sig_folder, file_path):
        return "Access denied", 403
    if not os.path.isfile(file_path):
        return "File not found", 404
    return send_from_directory(app.config['SIGNATURE_FOLDER'], filename)

@app.route('/uploads/<path:filename>')
@login_required
def serve_upload(filename):
    """Serve uploaded files — requires login; blocks path traversal."""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        base_abs = os.path.abspath(upload_folder)
        file_path = os.path.normpath(os.path.join(base_abs, filename))
        if not _is_path_within_directory(base_abs, file_path):
            print(f"ERROR: Security violation - path outside uploads: {filename!r}")
            return "Access denied", 403
        if not os.path.isfile(file_path):
            print(f"ERROR: File not found: {file_path}")
            return "File not found", 404
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        print(f"ERROR serving upload {filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error loading file: {str(e)}", 500

@app.route('/serve_message_file/<path:filename>')
@login_required
def serve_message_file(filename):
    """Serve message media files (images and voice messages)"""
    if '..' in filename.replace('\\', '/').split('/'):
        return "Access denied", 403
    rel = os.path.normpath(filename)
    if rel.startswith('..') or (len(rel) > 0 and rel[0] in (os.sep, '/')):
        return "Access denied", 403
    for folder_name in ('message_attachments', 'voice_messages'):
        base = os.path.abspath(folder_name)
        full = os.path.normpath(os.path.join(base, rel))
        if not _is_path_within_directory(base, full):
            continue
        if os.path.isfile(full):
            return send_from_directory(folder_name, rel)
    return "File not found", 404

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.get_json(silent=True) or {}
        app_id = data.get('application_id')
        message = (data.get('message') or '').strip()
        if not app_id or not message:
            return jsonify({'error': 'Missing data'}), 400
        try:
            app_id = int(app_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'Invalid application id'}), 400
        if not _user_can_access_application(current_user.id, current_user.role, app_id):
            return jsonify({'error': 'Unauthorized'}), 403

        conn = get_db()
        try:
            conn.execute(
                'INSERT INTO messages (loan_application_id, sender_id, message) VALUES (?, ?, ?)',
                (app_id, current_user.id, message)
            )
            app_data = conn.execute(
                'SELECT submitted_by, assigned_ci_staff FROM loan_applications WHERE id=?',
                (app_id,)
            ).fetchone()
            conn.commit()
        finally:
            conn.close()

        if app_data:
            users_to_notify = []
            submitted_by = app_data['submitted_by'] if app_data else None
            assigned_ci = app_data['assigned_ci_staff'] if app_data else None
            if submitted_by and submitted_by != current_user.id:
                users_to_notify.append(submitted_by)
            if assigned_ci and assigned_ci != current_user.id:
                users_to_notify.append(assigned_ci)
            for user_id in users_to_notify:
                enqueue_notification(
                    user_id,
                    f'New message from {current_user.name}',
                    f'/application/{app_id}'
                )

        try:
            socketio.emit('new_message', {
                'application_id': app_id,
                'sender': current_user.name,
                'message': message,
                'timestamp': now_ph().isoformat(),
            }, room=f'app_{app_id}')
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR send_message: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Could not send message'}), 500

# Modern Messenger Routes
@app.route('/api/send_message_with_attachment', methods=['POST'])
@login_required
def send_message_with_attachment():
    try:
        app_id_raw = request.form.get('application_id')
        message = (request.form.get('message') or '').strip()
        message_type = request.form.get('message_type', 'text')
        if not app_id_raw:
            return jsonify({'success': False, 'error': 'Missing application id'}), 400
        try:
            app_id = int(app_id_raw)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'Invalid application id'}), 400
        if not _user_can_access_application(current_user.id, current_user.role, app_id):
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        file_path = None
        file_name = None
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                filename = secure_filename(file.filename) or 'attachment.bin'
                if message_type == 'voice':
                    folder = 'voice_messages'
                    unique_filename = f"voice_{app_id}_{uuid.uuid4().hex[:8]}.webm"
                elif message_type == 'image':
                    folder = 'message_attachments'
                    unique_filename = f"img_{app_id}_{uuid.uuid4().hex[:8]}_{filename}"
                else:
                    folder = 'message_attachments'
                    unique_filename = f"file_{app_id}_{uuid.uuid4().hex[:8]}_{filename}"
                os.makedirs(folder, exist_ok=True)
                file_path = os.path.join(folder, unique_filename)
                file.save(file_path)
                file_name = filename

        conn = get_db()
        try:
            conn.execute('''
                INSERT INTO messages (loan_application_id, sender_id, message, message_type, file_path, file_name)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (app_id, current_user.id, message, message_type, file_path, file_name))
            app_data = conn.execute(
                'SELECT submitted_by, assigned_ci_staff FROM loan_applications WHERE id=?',
                (app_id,)
            ).fetchone()
            conn.commit()
        finally:
            conn.close()

        if app_data:
            users_to_notify = []
            submitted_by = app_data['submitted_by']
            assigned_ci = app_data['assigned_ci_staff']
            if submitted_by and submitted_by != current_user.id:
                users_to_notify.append(submitted_by)
            if assigned_ci and assigned_ci != current_user.id:
                users_to_notify.append(assigned_ci)
            for user_id in users_to_notify:
                enqueue_notification(
                    user_id,
                    f'New message from {current_user.name}',
                    f'/application/{app_id}'
                )

        try:
            socketio.emit('new_message', {
                'application_id': app_id,
                'sender': current_user.name,
                'message': message,
                'timestamp': now_ph().isoformat(),
            }, room=f'app_{app_id}')
        except Exception:
            pass
        return jsonify({'success': True})
    except Exception as e:
        print(f"ERROR send_message_with_attachment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': 'Could not send message'}), 500

@app.route('/api/edit_message', methods=['POST'])
@login_required
def edit_message():
    data = request.json
    message_id = data.get('message_id')
    new_text = data.get('new_text')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id FROM messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('''
            UPDATE messages 
            SET message=?, is_edited=1, edited_at=? 
            WHERE id=?
        ''', (new_text, now_ph().isoformat(), message_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/api/delete_message', methods=['POST'])
@login_required
def delete_message():
    data = request.json
    message_id = data.get('message_id')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id FROM messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('UPDATE messages SET is_deleted=1 WHERE id=?', (message_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/download_message_file/<int:msg_id>')
@login_required
def download_message_file(msg_id):
    conn = get_db()
    msg = conn.execute('SELECT * FROM messages WHERE id=?', (msg_id,)).fetchone()
    conn.close()
    
    if not msg or not msg['file_path']:
        flash('File not found', 'danger')
        return redirect(url_for('index'))
    if not _user_can_access_application(current_user.id, current_user.role, msg['loan_application_id']):
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    # Validate file path (prevent path traversal)
    file_path = msg['file_path']
    allowed_folders = [
        os.path.abspath('voice_messages'),
        os.path.abspath('message_attachments')
    ]
    requested_path = os.path.abspath(file_path)
    
    is_valid = any(
        _is_path_within_directory(folder, requested_path) for folder in allowed_folders
    )
    if not is_valid:
        flash('Invalid file path', 'danger')
        return redirect(url_for('index'))
    
    try:
        return send_file(msg['file_path'], as_attachment=True, download_name=msg['file_name'])
    except:
        flash('File not found on server', 'danger')
        return redirect(url_for('index'))

@app.route('/api/get_messages/<int:app_id>')
@login_required
def get_messages_api(app_id):
    if not _user_can_access_application(current_user.id, current_user.role, app_id):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    conn = get_db()
    messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.loan_application_id=?
        ORDER BY m.sent_at ASC
    ''', (app_id,)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'messages': [dict(msg) for msg in messages]
    })

# SocketIO events
@socketio.on('connect')
def handle_connect(auth=None):
    if not current_user.is_authenticated:
        disconnect()
        return
    join_room(str(current_user.id))
    # Mark user as online
    online_users[current_user.id] = {
        'name': current_user.name,
        'role': current_user.role,
        'last_seen': now_ph().isoformat()
    }
    # Update database
    conn = get_db()
    conn.execute('UPDATE users SET last_seen=?, is_online=1 WHERE id=?', 
                (now_ph().isoformat(), current_user.id))
    conn.commit()
    conn.close()
    # Broadcast to all users that this user is online
    socketio.emit('user_online', {
        'user_id': current_user.id,
        'name': current_user.name,
        'role': current_user.role
    }, to=None, include_self=True)

@socketio.on('disconnect')
def handle_disconnect(reason=None):
    if current_user.is_authenticated:
        # Mark user as offline
        if current_user.id in online_users:
            del online_users[current_user.id]
        # Update database
        conn = get_db()
        conn.execute('UPDATE users SET last_seen=?, is_online=0 WHERE id=?', 
                    (now_ph().isoformat(), current_user.id))
        conn.commit()
        conn.close()
        # Broadcast to all users that this user is offline
        socketio.emit('user_offline', {
            'user_id': current_user.id
        }, to=None, include_self=True)

@socketio.on('join_application')
def handle_join_application(data):
    if not current_user.is_authenticated:
        return
    if not isinstance(data, dict):
        return
    app_id = data.get('application_id')
    try:
        app_id = int(app_id)
    except (TypeError, ValueError):
        return
    if _user_can_access_application(current_user.id, current_user.role, app_id):
        join_room(f'app_{app_id}')

@socketio.on('join')
def handle_join(data):
    if not current_user.is_authenticated:
        return
    if not isinstance(data, dict):
        return
    room = str(data.get('room') or '').strip()
    if not room:
        return
    if room == str(current_user.id):
        join_room(room)
        return
    if room == 'admin_tracking' and current_user.role in ['admin', 'loan_officer']:
        join_room(room)
        return
    if room.startswith('app_'):
        try:
            app_id = int(room.split('_', 1)[1])
        except (TypeError, ValueError):
            return
        if _user_can_access_application(current_user.id, current_user.role, app_id):
            join_room(room)

@socketio.on('join_tracking')
def handle_join_tracking(data):
    if current_user.is_authenticated and current_user.role in ['admin', 'loan_officer']:
        join_room('admin_tracking')

# Flutter Mobile App API Endpoints
@app.route('/api/user_info')
@login_required
def user_info():
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'role': current_user.role
    })

@app.route('/api/ci_applications')
@login_required
def ci_applications():
    if current_user.role != 'ci_staff':
        return jsonify([])
    
    conn = get_db()
    apps = conn.execute('''
        SELECT * FROM loan_applications 
        WHERE assigned_ci_staff = ? 
        ORDER BY submitted_at ASC, id ASC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return jsonify([dict(app) for app in apps])

@app.route('/api/ci_application/<int:id>')
@login_required
def ci_application_api(id):
    if not _user_can_access_application(current_user.id, current_user.role, id):
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    app = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    documents = conn.execute(
        'SELECT id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at, mime_type '
        'FROM documents WHERE loan_application_id=? ORDER BY uploaded_at DESC',
        (id,),
    ).fetchall()
    conn.close()
    
    return jsonify({
        'application': dict(app) if app else None,
        'documents': [dict(doc) for doc in documents],
    })

# OFFLINE PWA API ENDPOINTS
@app.route('/api/ci/download_applications', methods=['GET'])
@login_required
def api_download_applications():
    """Get all applications assigned to current CI staff for offline download"""
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    apps = conn.execute('''
        SELECT * FROM loan_applications 
        WHERE assigned_ci_staff = ? AND status = 'assigned_to_ci'
        ORDER BY submitted_at ASC, id ASC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'applications': [dict(app) for app in apps],
        'count': len(apps)
    })

@app.route('/api/ci/upload_checklist', methods=['POST'])
@login_required
def api_upload_checklist():
    """Upload completed checklist from offline storage"""
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        application_id = data.get('application_id')
        checklist_data = data.get('checklist_data')
        signature = data.get('signature')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not all([application_id, checklist_data, signature]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db()
        
        # Update application
        conn.execute('''
            UPDATE loan_applications 
            SET status = 'ci_completed',
                ci_checklist_data = ?,
                ci_signature = ?,
                ci_completed_at = ?,
                ci_notes = 'Submitted offline'
            WHERE id = ? AND assigned_ci_staff = ?
        ''', (checklist_data, signature, now_ph().strftime('%Y-%m-%d %H:%M:%S'), 
              application_id, current_user.id))
        
        # Track location if provided
        if latitude and longitude:
            conn.execute('''
                INSERT INTO location_tracking (user_id, latitude, longitude, activity, tracked_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, latitude, longitude, 'CI Checklist Submitted', 
                  now_ph().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Checklist uploaded successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ci/sync_status', methods=['GET'])
@login_required
def api_sync_status():
    """Get sync status for offline PWA"""
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    
    # Count pending applications
    pending = conn.execute('''
        SELECT COUNT(*) as count FROM loan_applications 
        WHERE assigned_ci_staff = ? AND status = 'assigned_to_ci'
    ''', (current_user.id,)).fetchone()
    
    # Count completed applications
    completed = conn.execute('''
        SELECT COUNT(*) as count FROM loan_applications 
        WHERE assigned_ci_staff = ? AND status = 'ci_completed'
    ''', (current_user.id,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'pending_count': pending['count'] if pending else 0,
        'completed_count': completed['count'] if completed else 0,
        'is_online': True
    })

# --- Signup: hand-sign captcha (session-bound) + honeypot + min submit time ---------
# Stops simple scripted registration; correct answer is only checked server-side.
_HAND_SIGN_OPTIONS = [
    ('wave', 'The open hand — “hello” or “stop”', '🖐'),
    ('thumbs', 'Thumbs up — “good” or “yes”', '👍'),
    ('peace', 'Two fingers: peace or victory', '✌️'),
    ('ok', 'Fingers in an “OK” circle', '👌'),
    ('fist', 'A closed, tight fist', '✊'),
]
_SIGNUP_CAPTCHA_TTL = 20 * 60
_SIGNUP_MIN_SUBMIT_SEC = 4


def _prepare_signup_hand_captcha():
    import random
    order = _HAND_SIGN_OPTIONS[:]
    random.shuffle(order)
    expected = random.choice(_HAND_SIGN_OPTIONS)
    session['signup_hand_captcha'] = {
        'expected_id': expected[0],
        'issued_at': time.time(),
    }
    return {
        'hand_sign_prompt': expected[1],
        'hand_choices': order,
        'captcha_expected_id': expected[0],
        'captcha_target_emoji': expected[2],
    }


# USER REGISTRATION & APPROVAL ROUTES
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Honeypot (should stay empty — bots often fill all fields)
        if (request.form.get('website') or '').strip():
            return redirect(url_for('login'))

        cap = session.get('signup_hand_captcha')
        if not cap:
            flash('This page expired. Please open the form again and try once more.', 'warning')
            return redirect(url_for('signup'))
        if time.time() - cap.get('issued_at', 0) > _SIGNUP_CAPTCHA_TTL:
            session.pop('signup_hand_captcha', None)
            flash('The form took too long. Please try again with a new hand-sign check.', 'info')
            return redirect(url_for('signup'))

        _hs = (request.form.get('hand_sign') or '').strip()
        if not _hs or _hs != cap.get('expected_id'):
            session.pop('signup_hand_captcha', None)
            flash('The hand sign did not match. Please try the check again.', 'warning')
            return redirect(url_for('signup'))
        if (time.time() - cap.get('issued_at', 0)) < _SIGNUP_MIN_SUBMIT_SEC:
            session.pop('signup_hand_captcha', None)
            flash('Please take a few seconds to complete the form, then try again.', 'info')
            return redirect(url_for('signup'))

        # One-time: prevent replay; further validation below
        session.pop('signup_hand_captcha', None)

        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        signature_data = request.form.get('signature_data')
        
        # Validation
        if not all([name, email, password, confirm_password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('signup'))
        
        if not signature_data:
            flash('Signature is required', 'danger')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signup'))
        
        # Validate password strength
        is_valid, message = validate_password_strength(password)
        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('signup'))
        
        conn = get_db()
        
        # Check if email already exists
        existing = conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if existing:
            flash('Email already registered', 'danger')
            conn.close()
            return redirect(url_for('signup'))
        
        # Save signature
        signature_path = None
        if signature_data and signature_data.startswith('data:image'):
            import base64
            signature_base64 = signature_data.split(',')[1]
            signature_bytes = base64.b64decode(signature_base64)
            signature_filename = f"signature_{email.replace('@', '').replace('.', '')}_{uuid.uuid4().hex[:8]}.png"
            signature_path = os.path.join(app.config['SIGNATURE_FOLDER'], signature_filename)
            with open(signature_path, 'wb') as f:
                f.write(signature_bytes)
        
        # Create new user (not approved yet, no role assigned - admin will assign)
        try:
            password_hash = generate_password_hash(password)
            conn.execute('''
                INSERT INTO users (email, password_hash, name, role, signature_path, assigned_route, is_approved, created_at)
                VALUES (?, ?, ?, NULL, ?, NULL, 0, ?)
            ''', (email, password_hash, name, signature_path, now_ph().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            # Notify admin
            admin = conn.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
            conn.close()
            
            if admin:
                enqueue_notification(
                    admin['id'],
                    f'New staff registration: {name} - Role and route assignment required',
                    '/manage_users'
                )
            
            flash('Registration successful! Please wait for admin to assign your role and approve your account.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html', **_prepare_signup_hand_captcha())

@app.route('/manage_users')
@login_required
def manage_users():
    # Check if user has permission
    if current_user.role == 'admin':
        # Super admin always has access
        pass
    elif current_user.role == 'loan_officer':
        # Check if loan officer has manage_users permission
        if not has_permission(current_user, 'manage_users'):
            flash('Access Denied - You do not have permission to manage users. Contact super admin.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get pending users
    pending_users = conn.execute('''
        SELECT id, name, email, role, assigned_route, created_at, approval_type
        FROM users
        WHERE is_approved = 0
        ORDER BY created_at DESC
    ''').fetchall()
    
    # Get active users
    active_users = conn.execute('''
        SELECT id, name, email, role, assigned_route, created_at
        FROM users
        WHERE is_approved = 1
        ORDER BY name ASC
    ''').fetchall()
    
    row = conn.execute("SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'",
                                (current_user.id,)).fetchone()
    unread_count = row['count'] if row else 0

    claims_by_uid = _ci_staff_route_claims_by_user(conn)
    conn.close()

    ci_routes = list_ci_routes_for_ui()
    pending_route_options = {}
    for pu in pending_users:
        pu_id = int(pu['id'])
        blocked = _ci_route_keys_claimed_by_other_ci_staff(claims_by_uid, pu_id)
        sel = frozenset(route_tokens_filter(pu['assigned_route']))
        pending_route_options[pu_id] = [
            dict(r) for r in ci_routes
            if r['route_key'] not in blocked or r['route_key'] in sel
        ]

    return render_template(
        'manage_users.html',
        pending_users=pending_users,
        active_users=active_users,
        unread_count=unread_count,
        ci_routes=ci_routes,
        pending_route_options=pending_route_options,
    )

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('manage_users'))
        if not user['role']:
            flash(f'Cannot approve {user["name"]} - Please assign a role first!', 'warning')
            return redirect(url_for('manage_users'))
        _ar = (user['assigned_route'] or '').strip() if user.get('assigned_route') else ''
        if user['role'] == 'ci_staff' and not _ar:
            flash(f'Cannot approve {user["name"]} - CI staff must have a route assigned!', 'warning')
            return redirect(url_for('manage_users'))

        conn.execute('UPDATE users SET is_approved = 1 WHERE id=?', (user_id,))
        conn.commit()
        _invalidate_ci_staff_cache()
        display_name = user['name'] or user['email'] or f'User #{user_id}'
    except Exception as e:
        print(f"ERROR approve_user: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        flash(f'Could not approve user: {e}', 'danger')
        return redirect(url_for('manage_users'))
    finally:
        try:
            conn.close()
        except Exception:
            pass

    try:
        enqueue_notification(
            user_id,
            'Your account has been approved! You can now login.',
            '/login',
        )
    except Exception:
        pass
    flash(f'User {display_name} approved successfully!', 'success')
    return redirect(url_for('manage_users'))


def _purge_user_dependencies(conn, user_id):
    """Remove dependent rows so we can cleanly delete/disapprove a user on PostgreSQL."""
    cleanup_statements = [
        ("DELETE FROM direct_messages WHERE sender_id=? OR receiver_id=?", (user_id, user_id)),
        ("DELETE FROM messages WHERE sender_id=?", (user_id,)),
        ("DELETE FROM notifications WHERE user_id=?", (user_id,)),
        ("DELETE FROM location_tracking WHERE user_id=?", (user_id,)),
        ("DELETE FROM documents WHERE uploaded_by=?", (user_id,)),
        ("UPDATE loan_applications SET submitted_by=NULL WHERE submitted_by=?", (user_id,)),
        ("UPDATE loan_applications SET assigned_ci_staff=NULL WHERE assigned_ci_staff=?", (user_id,)),
    ]
    for sql, params in cleanup_statements:
        try:
            conn.execute(sql, params)
        except Exception as sub_err:
            print(f"  cleanup skipped ({sql.split()[0:2]}): {sub_err}")


@app.route('/disapprove_user/<int:user_id>', methods=['POST'])
@login_required
def disapprove_user(user_id):
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        user = conn.execute('SELECT id, name, email, role FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('manage_users'))

        display_name = user['name'] or user['email'] or f'User #{user_id}'
        protected_emails = {
            'superadmin@dccco.test',
            'admin@dccco.test',
            'loan@dccco.test',
            'ci@dccco.test',
        }
        if (user['email'] or '').lower() in protected_emails:
            flash(f'Cannot remove the protected default account {display_name}.', 'danger')
            return redirect(url_for('manage_users'))

        _purge_user_dependencies(conn, user_id)

        try:
            conn.execute('DELETE FROM users WHERE id=?', (user_id,))
            conn.commit()
            flash(f'User {display_name} disapproved and removed.', 'info')
        except Exception as delete_err:
            print(f"WARN hard delete failed, falling back to soft disapprove: {delete_err}")
            try:
                conn.rollback()
            except Exception:
                pass
            conn.execute('UPDATE users SET is_approved = 0 WHERE id=?', (user_id,))
            conn.commit()
            _invalidate_ci_staff_cache()
            flash(f'User {display_name} disapproved (kept for history).', 'warning')
    except Exception as e:
        print(f"ERROR disapprove_user: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except Exception:
            pass
        flash(f'Could not disapprove user: {e}', 'danger')
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_users'))

@app.route('/assign_role/<int:user_id>', methods=['POST'])
@login_required
def assign_role(user_id):
    if not can_access_manage_users_actions():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    data = request.get_json(silent=True) or {}
    role = data.get('role')
    # Restrict assignment from Manage Users to LPS and CI/BI only.
    if not role or role not in MANAGE_USERS_ASSIGNABLE_ROLES:
        return jsonify({'success': False, 'error': 'Invalid role'}), 400

    conn = get_db()
    try:
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        conn.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
        if user['role'] == 'ci_staff' and role != 'ci_staff':
            conn.execute('UPDATE users SET assigned_route=NULL WHERE id=?', (user_id,))
        conn.commit()
        _invalidate_ci_staff_cache()
        return jsonify({'success': True, 'message': 'Role assigned successfully'})
    except Exception as e:
        print(f"ERROR assign_role: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return jsonify({'success': False, 'error': 'Could not assign role'}), 500
    finally:
        try:
            conn.close()
        except Exception:
            pass


@app.route('/deactivate_user/<int:user_id>', methods=['POST'])
@login_required
def deactivate_user(user_id):
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        user = conn.execute(
            'SELECT id, name, email, role FROM users WHERE id=?', (user_id,)
        ).fetchone()
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('manage_users'))
        if user['role'] == 'admin':
            flash('Cannot deactivate admin users', 'danger')
            return redirect(url_for('manage_users'))
        conn.execute('UPDATE users SET is_approved = 0 WHERE id=?', (user_id,))
        conn.commit()
        display_name = user['name'] or user['email'] or f'User #{user_id}'
        flash(f'User {display_name} deactivated.', 'warning')
    except Exception as e:
        print(f"ERROR deactivate_user: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        flash(f'Could not deactivate user: {e}', 'danger')
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return redirect(url_for('manage_users'))

@app.route('/update_ci_route', methods=['POST'])
@login_required
def update_ci_route():
    def _wants_json_client_response() -> bool:
        # fetch() with FormData + Accept: application/json must still get JSON back
        if 'application/json' in (request.headers.get('Accept') or ''):
            return True
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return True
        if bool(request.is_json) or (
            (request.content_type or '').lower().find('application/json') >= 0
        ):
            return True
        return False

    def _use_form_data() -> bool:
        ct = (request.content_type or '').lower()
        if 'multipart/form-data' in ct or 'application/x-www-form-urlencoded' in ct:
            return True
        uid = request.form.get('user_id')
        return bool(uid is not None and str(uid).strip() != '')

    if not can_access_manage_users_actions():
        if _wants_json_client_response():
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        flash('Access denied - You do not have permission to manage user routes.', 'danger')
        return redirect(url_for('admin_dashboard' if current_user.role == 'loan_officer' else 'index'))

    def _allowed_route_set():
        return set(get_ci_route_label_dict().keys())

    def _parts_from_json_body(data: dict) -> list:
        if not data:
            return []
        if isinstance(data.get('assigned_routes'), list):
            return [str(x).strip() for x in data['assigned_routes'] if str(x).strip()]
        raw = data.get('assigned_route')
        if raw is None:
            return []
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
        return [p.strip() for p in str(raw).split(',') if p.strip()]

    def _parts_from_form() -> list:
        parts = request.form.getlist('assigned_route')
        if not parts:
            single = request.form.get('assigned_route')
            if single:
                return [p.strip() for p in str(single).split(',') if p.strip()]
        return [p.strip() for p in parts if p.strip()]

    def _build_assigned_route_string(parts: list) -> str | None:
        allowed = _allowed_route_set()
        seen = set()
        ordered: list = []
        for p in parts:
            if p and p in allowed and p not in seen:
                seen.add(p)
                ordered.append(p)
        return ','.join(ordered) if ordered else None

    wants_json = _wants_json_client_response()
    if _use_form_data():
        user_id = request.form.get('user_id')
        raw_parts = _parts_from_form()
    else:
        json_data = request.get_json(silent=True) or {}
        if not isinstance(json_data, dict):
            json_data = {}
        user_id = json_data.get('user_id')
        raw_parts = _parts_from_json_body(json_data)
    is_json_client = bool(wants_json)

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        user_id = None

    if not user_id:
        if is_json_client:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        flash('Invalid request', 'danger')
        return redirect(url_for('manage_users'))

    assigned_route = _build_assigned_route_string(raw_parts)
    if raw_parts and not assigned_route and is_json_client:
        return jsonify({'success': False, 'error': 'No valid route ids in request'}), 400

    conn = get_db()
    try:
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        if not user:
            if is_json_client:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            flash('User not found', 'danger')
            return redirect(url_for('manage_users'))

        if user['role'] != 'ci_staff':
            if is_json_client:
                return jsonify({'success': False, 'error': 'User must be CI/BI to have routes'}), 400
            flash('Only CI/BI users can be assigned coverage routes.', 'warning')
            return redirect(url_for('manage_users'))

        if not user['is_approved'] and assigned_route:
            claims_map = _ci_staff_route_claims_by_user(conn)
            blocked_other = _ci_route_keys_claimed_by_other_ci_staff(claims_map, user_id)
            clash_keys = [
                x.strip()
                for x in str(assigned_route).split(',')
                if x.strip() and x.strip() in blocked_other
            ]
            if clash_keys:
                clash_keys = list(dict.fromkeys(clash_keys))
                labels = get_ci_route_label_dict()
                human = ', '.join(labels.get(k, k) for k in clash_keys)
                detail = (
                    'One or more routes are already assigned to another CI/BI user '
                    '(active or pending). '
                    + human
                )
                if is_json_client:
                    return jsonify(
                        {
                            'success': False,
                            'error': 'routes_unavailable',
                            'route_keys': clash_keys,
                            'message': detail,
                        }
                    ), 409
                flash(detail, 'danger')
                return redirect(url_for('manage_users'))

        conn.execute('UPDATE users SET assigned_route=? WHERE id=?', (assigned_route, user_id))
        conn.commit()
    except Exception as err:
        app.logger.exception('update_ci_route: %s', err)
        if is_json_client:
            return jsonify({'success': False, 'error': 'Could not save routes'}), 500
        flash('Could not save routes.', 'danger')
        return redirect(url_for('manage_users'))

    _invalidate_ci_staff_cache()

    if assigned_route:
        try:
            enqueue_notification(
                int(user_id),
                'Your assigned route has been updated',
                '/ci/dashboard',
            )
        except Exception:
            pass

    if is_json_client:
        return jsonify(
            {
                'success': True,
                'message': 'Route assigned successfully',
                'assigned_route': assigned_route or '',
            }
        )

    flash('Route assigned successfully!', 'success')
    return redirect(url_for('manage_users'))


@app.route('/api/admin/ci_coverage_routes', methods=['GET', 'POST'])
@login_required
def api_ci_coverage_routes():
    """List coverage routes (GET) or create a custom route (POST: label, optional keywords)."""
    if not can_access_manage_users_actions():
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403

    if request.method == 'GET':
        return jsonify({'success': True, 'routes': list_ci_routes_for_ui()})

    data = request.get_json(silent=True) or {}
    label = (data.get('label') or '').strip()
    if not label or len(label) > 200:
        return jsonify({'success': False, 'error': 'Label is required (max 200 characters).'}), 400
    raw_kw = data.get('keywords')
    if isinstance(raw_kw, list):
        kws = [str(x).strip() for x in raw_kw if str(x).strip()]
    else:
        kws = [x.strip() for x in str(raw_kw or '').split(',') if x.strip()]
    keywords_json = json.dumps([x.lower() for x in kws], ensure_ascii=False) if kws else None
    base = re.sub(r'[^a-z0-9]+', '_', label.lower())[:32].strip('_') or 'area'
    route_key = f'route_{base}_{uuid.uuid4().hex[:8]}'
    try:
        conn = get_db()
        row = conn.execute('SELECT COALESCE(MAX(sort_order), 0) AS m FROM ci_coverage_routes').fetchone()
        next_order = int(row['m'] if row and row['m'] is not None else 0) + 10
        conn.execute(
            """
            INSERT INTO ci_coverage_routes (route_key, label, sort_order, keywords, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            (route_key, label, next_order, keywords_json),
        )
        conn.commit()
    except Exception as e:
        app.logger.exception('api_ci_coverage_routes')
        return jsonify({'success': False, 'error': str(e)}), 500
    invalidate_ci_route_label_cache()
    return jsonify(
        {
            'success': True,
            'route': {'route_key': route_key, 'label': label},
        }
    )


# REPORT GENERATION ROUTES
@app.route('/reports')
@login_required
def reports():
    """Reports dashboard page"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    ci_staff = conn.execute("SELECT id, name FROM users WHERE role='ci_staff' ORDER BY name").fetchall()
    conn.close()
    
    return render_template('reports.html', ci_staff=ci_staff)

@app.route('/system_settings')
@login_required
def system_settings():
    """System configuration page (admin only or loan officer with permission)"""
    import time as _time
    _t0 = _time.monotonic()

    if current_user.role == 'admin':
        pass
    elif current_user.role == 'loan_officer':
        if not has_permission(current_user, 'system_settings'):
            flash('Access Denied - You do not have permission to access system settings. Contact super admin.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('Unauthorized - Admin access required', 'danger')
        return redirect(url_for('index'))

    ensure_system_activity_log_table()
    conn = get_db()

    _t_q1 = _time.monotonic()

    # User + application stats (single pass each; includes status guide counts).
    stats_row = conn.execute('''
        SELECT
            SUM(CASE WHEN is_approved=1 THEN 1 ELSE 0 END) AS total_users
        FROM users
    ''').fetchone()
    app_stats = conn.execute('''
        SELECT
            COUNT(*) AS total_applications,
            SUM(CASE WHEN status='submitted' THEN 1 ELSE 0 END) AS cnt_submitted,
            SUM(CASE WHEN status='assigned_to_ci' THEN 1 ELSE 0 END) AS pending_ci,
            SUM(CASE WHEN status='ci_completed' THEN 1 ELSE 0 END) AS cnt_ci_completed,
            SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved_loans,
            SUM(CASE WHEN status IN ('disapproved', 'rejected') THEN 1 ELSE 0 END) AS cnt_rejected,
            COALESCE(SUM(CASE WHEN status='approved' THEN loan_amount ELSE 0 END), 0) AS total_loan_amount
        FROM loan_applications
    ''').fetchone()
    _t_q2 = _time.monotonic()

    stats = {
        'total_users': (stats_row['total_users'] or 0) if stats_row else 0,
        'total_applications': (app_stats['total_applications'] or 0) if app_stats else 0,
        'cnt_submitted': (app_stats['cnt_submitted'] or 0) if app_stats else 0,
        'pending_ci': (app_stats['pending_ci'] or 0) if app_stats else 0,
        'cnt_ci_completed': (app_stats['cnt_ci_completed'] or 0) if app_stats else 0,
        'approved_loans': (app_stats['approved_loans'] or 0) if app_stats else 0,
        'cnt_rejected': (app_stats['cnt_rejected'] or 0) if app_stats else 0,
        'total_loan_amount': (app_stats['total_loan_amount'] or 0) if app_stats else 0,
    }

    log_role = (request.args.get('log_role') or '').strip()
    log_name = (request.args.get('log_name') or '').strip()
    log_action = (request.args.get('log_action') or '').strip()
    log_from = (request.args.get('log_from') or '').strip()
    log_to = (request.args.get('log_to') or '').strip()

    def _parse_date_start(s):
        if not s:
            return None
        try:
            return datetime.strptime(s, '%Y-%m-%d')
        except Exception:
            return None

    def _parse_date_end_exclusive(s):
        start = _parse_date_start(s)
        if not start:
            return None
        return start + timedelta(days=1)

    where = []
    params = []
    if log_role:
        where.append('role = ?')
        params.append(log_role)
    if log_name:
        where.append('full_name = ?')
        params.append(log_name)
    if log_action:
        where.append('action = ?')
        params.append(log_action)
    dt_from = _parse_date_start(log_from)
    if dt_from:
        where.append('created_at >= ?')
        params.append(dt_from.strftime('%Y-%m-%d %H:%M:%S'))
    dt_to = _parse_date_end_exclusive(log_to)
    if dt_to:
        where.append('created_at < ?')
        params.append(dt_to.strftime('%Y-%m-%d %H:%M:%S'))

    # Default limit 50; filtered views allow up to 200.
    _log_limit = 200 if any([log_role, log_name, log_action, log_from, log_to]) else 50
    sql_logs = (
        'SELECT id, role, full_name, action, actor_user_id, created_at FROM system_activity_log'
    )
    if where:
        sql_logs += ' WHERE ' + ' AND '.join(where)
    sql_logs += f' ORDER BY created_at DESC LIMIT {_log_limit}'
    recent_logs = conn.execute(sql_logs, tuple(params)).fetchall()
    _t_q3 = _time.monotonic()

    # Filter-dropdown options: fetch from a small materialized subquery so we
    # don't do three full-table scans on a potentially large log table.
    # Capped at 100 distinct values each — more than enough for dropdowns.
    role_options = conn.execute(
        "SELECT DISTINCT role FROM system_activity_log"
        " WHERE COALESCE(TRIM(role), '') <> '' ORDER BY role LIMIT 100"
    ).fetchall()
    name_options = conn.execute(
        "SELECT DISTINCT full_name FROM system_activity_log"
        " WHERE COALESCE(TRIM(full_name), '') <> '' ORDER BY full_name LIMIT 100"
    ).fetchall()
    action_options = conn.execute(
        "SELECT DISTINCT action FROM system_activity_log"
        " WHERE COALESCE(TRIM(action), '') <> '' ORDER BY action LIMIT 100"
    ).fetchall()
    _t_q4 = _time.monotonic()

    conn.close()

    _total = _time.monotonic() - _t0
    if _total > 0.5:
        _perf_logger.warning(
            'system_settings slow %.3fs | stats=%.0fms logs=%.0fms opts=%.0fms',
            _total,
            (_t_q2 - _t_q1) * 1000,
            (_t_q3 - _t_q2) * 1000,
            (_t_q4 - _t_q3) * 1000,
        )
    
    return render_template(
        'system_settings.html',
        stats=stats,
        recent_logs=recent_logs,
        role_options=role_options,
        name_options=name_options,
        action_options=action_options,
        log_filters={
            'role': log_role,
            'name': log_name,
            'action': log_action,
            'from': log_from,
            'to': log_to,
        },
    )


def _redirect_back_to_system_settings_logs():
    """Return to filtered Recent Logs; prefer safe same-origin referrer."""
    from urllib.parse import urlparse

    ref = (request.referrer or '').strip()
    try:
        cand = urlparse(ref)
        here = urlparse(request.url_root)
        if (
            cand.scheme in ('http', 'https')
            and cand.netloc == here.netloc
            and '/system_settings' in (cand.path or '')
        ):
            base = ref.split('#')[0]
            return redirect(base + '#logs-section')
    except Exception:
        pass
    return redirect(url_for('system_settings') + '#logs-section')


@app.route('/system_settings/force_logout/<int:target_user_id>', methods=['POST'])
@login_required
def system_settings_force_logout_user(target_user_id):
    """Super admin only: invalidate DB-backed sessions so the user is signed out on next request."""
    if current_user.role != 'admin':
        flash('Only the super administrator can force sign-out from activity logs.', 'danger')
        return redirect(url_for('system_settings') + '#logs-section')

    if target_user_id == current_user.id:
        flash('To sign yourself out, use Sign out from the menu.', 'info')
        return redirect(url_for('system_settings') + '#logs-section')

    conn = get_db()
    row = None
    try:
        row = conn.execute(
            'SELECT id, role, name, email FROM users WHERE id = ? LIMIT 1',
            (target_user_id,),
        ).fetchone()
        if not row:
            flash('User not found.', 'warning')
            return redirect(url_for('system_settings') + '#logs-section')
        role_norm = str(row['role'] or '').strip().lower()
        if role_norm == 'admin':
            flash('Cannot force sign out another super admin account.', 'warning')
            return redirect(url_for('system_settings') + '#logs-section')
        display_name = row['name'] if 'name' in row.keys() else ''
    finally:
        try:
            conn.close()
        except Exception:
            pass

    try:
        _deactivate_user_session(target_user_id, None)
        conn = get_db()
        conn.execute(
            'UPDATE users SET is_online = 0, last_seen = ? WHERE id = ?',
            (now_ph().isoformat(), target_user_id),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        app.logger.exception('system_settings_force_logout_user: %s', exc)
        flash('Could not invalidate sessions. Try again.', 'danger')
        return _redirect_back_to_system_settings_logs()

    try:
        _log_system_activity(
            current_user.role.replace('_', ' ').upper() if current_user.role else 'ADMIN',
            getattr(current_user, 'name', None)
            or getattr(current_user, 'email', None)
            or 'Admin',
            'FORCE SIGN OUT USER',
            actor_user_id=current_user.id,
            metadata={
                'target_user_id': target_user_id,
                'target_name': dict(row).get('name') if row else None,
            },
        )
    except Exception:
        pass

    flash(
        '{0}\'s active session was cleared. They must sign in again on their next visit.'.format(
            (display_name or '').strip() or f'User #{target_user_id}',
        ),
        'success',
    )
    return _redirect_back_to_system_settings_logs()


@app.route('/system_settings/dedupe_member_applications', methods=['POST'])
@login_required
def system_settings_dedupe_member_applications():
    """Remove duplicate loan_applications rows that share the same member name (DB cleanup)."""
    if current_user.role == 'admin':
        pass
    elif current_user.role == 'loan_officer' and has_permission(current_user, 'system_settings'):
        pass
    else:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('index'))

    conn = None
    try:
        conn = get_db()
        removed = dedupe_loan_applications_by_member_name(conn)
        conn.commit()
        flash(
            f'Removed {removed} duplicate application(s). '
            'One record per member name was kept (best status wins; ties use newest id).',
            'success',
        )
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        flash(f'Deduplication failed: {e}', 'danger')
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
    return redirect(url_for('system_settings') + '#quick-section')


@app.route('/update_system_settings', methods=['POST'])
@login_required
def update_system_settings():
    """Update system settings (admin only or loan officer with permission)"""
    # Check if user has permission
    if current_user.role == 'admin':
        pass
    elif current_user.role == 'loan_officer':
        if not has_permission(current_user, 'system_settings'):
            flash('Access Denied - You do not have permission to update system settings.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('Unauthorized - Admin access required', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get all settings
    settings = conn.execute('SELECT id FROM system_settings').fetchall()
    
    # Update each setting
    for setting in settings:
        setting_id = setting['id']
        new_value = request.form.get(f'setting_{setting_id}')
        if new_value is not None:
            conn.execute('UPDATE system_settings SET setting_value=? WHERE id=?', (new_value, setting_id))
    
    conn.commit()
    conn.close()
    # Bust the settings cache so the next GET sees updated values.
    _system_settings_cache['data'] = None
    _system_settings_cache['ts'] = 0.0

    _log_system_activity(
        current_user.role.replace('_', ' ').upper() if hasattr(current_user, 'role') else 'SYSTEM',
        getattr(current_user, 'name', None) or getattr(current_user, 'email', None) or 'System Admin',
        'UPDATE SETTINGS',
        actor_user_id=current_user.id if hasattr(current_user, 'id') else None,
    )
    
    flash('System settings updated successfully!', 'success')
    return redirect(url_for('system_settings'))

@app.route('/manage_permissions')
@login_required
def manage_permissions():
    """Manage loan officer permissions (super admin only)"""
    if current_user.role != 'admin':
        flash('Unauthorized - Super Admin access required', 'danger')
        return redirect(url_for('index'))

    conn = get_db()
    try:
        loan_officers = conn.execute('''
            SELECT id, name, email, permissions
            FROM users
            WHERE role = 'loan_officer' AND is_approved = 1
            ORDER BY name ASC
        ''').fetchall()

        row = conn.execute('''
            SELECT COUNT(*) as count
            FROM notifications
            WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'
        ''', (current_user.id,)).fetchone()
        unread_count = row['count'] if row else 0

        return render_template(
            'manage_permissions.html',
            loan_officers=loan_officers,
            unread_count=unread_count,
        )
    except Exception as e:
        print(f"ERROR manage_permissions: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except Exception:
            pass
        flash('Could not load permissions right now. Please try again.', 'warning')
        return redirect(url_for('admin_dashboard'))
    finally:
        try:
            conn.close()
        except Exception:
            pass

@app.route('/update_permissions/<int:user_id>', methods=['POST'])
@login_required
def update_permissions(user_id):
    """Update loan officer permissions (super admin only)"""
    if current_user.role != 'admin':
        flash('Unauthorized - Super Admin access required', 'danger')
        return redirect(url_for('index'))
    
    try:
        conn = get_db()
        
        # Get selected permissions
        permissions = []
        if request.form.get('manage_users'):
            permissions.append('manage_users')
        if request.form.get('system_settings'):
            permissions.append('system_settings')
        if request.form.get('manage_loan_types'):
            permissions.append('manage_loan_types')
        
        # Update user permissions
        permissions_str = ','.join(permissions) if permissions else None
        conn.execute("UPDATE users SET permissions=? WHERE id=? AND role='loan_officer'", 
                     (permissions_str, user_id))
        conn.commit()
        
        # Get user name for flash message
        user = conn.execute('SELECT name FROM users WHERE id=?', (user_id,)).fetchone()
        conn.close()
        
        flash(f'Permissions updated successfully for {user["name"]}!', 'success')
        return redirect(url_for('manage_permissions'))
    
    except Exception as e:
        flash(f'Error updating permissions: {str(e)}', 'danger')
        return redirect(url_for('manage_permissions'))

# Migration route removed - permissions column already exists in database
# Superadmin has full access without needing migrations

@app.route('/get_user_permissions/<int:user_id>', methods=['GET'])
@login_required
def get_user_permissions(user_id):
    """Get current permissions for a user (super admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        conn = get_db()
        user = conn.execute("SELECT permissions FROM users WHERE id=? AND role='loan_officer'", (user_id,)).fetchone()
        conn.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        permissions = (
            [p.strip() for p in user['permissions'].split(',') if p.strip()]
            if user['permissions']
            else []
        )
        return jsonify({'success': True, 'permissions': permissions})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_permissions_inline/<int:user_id>', methods=['POST'])
@login_required
def update_permissions_inline(user_id):
    """Update loan officer permissions inline (super admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        permissions = data.get('permissions', [])
        
        # Validate permissions
        valid_permissions = ['manage_users', 'system_settings', 'manage_loan_types']
        for perm in permissions:
            if perm not in valid_permissions:
                return jsonify({'success': False, 'error': f'Invalid permission: {perm}'}), 400
        
        conn = get_db()
        
        # Verify user is a loan officer
        user = conn.execute("SELECT name FROM users WHERE id=? AND role='loan_officer'", (user_id,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found or not a loan officer'}), 404
        
        # Update permissions
        permissions_str = ','.join(permissions) if permissions else None
        conn.execute('UPDATE users SET permissions=? WHERE id=?', (permissions_str, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Permissions updated for {user["name"]}',
            'permissions': permissions
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _report_date(value):
    """Format DB date values (datetime or string or None) as YYYY-MM-DD for reports."""
    if value is None or value == '':
        return 'N/A'
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    try:
        return str(value)[:10]
    except Exception:
        return 'N/A'


def _report_text(value, max_len=None, fallback='N/A'):
    """Safely format any DB value as a short report string."""
    if value is None:
        return fallback
    try:
        text = str(value)
    except Exception:
        return fallback
    if max_len and len(text) > max_len:
        text = text[:max_len]
    return text or fallback


def _report_money(value):
    try:
        return f"₱{float(value):,.2f}"
    except Exception:
        return '₱0.00'


@app.route('/generate_report/<report_type>', methods=['POST'])
@login_required
def generate_report(report_type):
    """Generate PDF reports with date range filters"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from io import BytesIO
    except Exception as import_err:
        print(f"ERROR loading reportlab: {import_err}")
        flash('PDF engine is not available on this server.', 'danger')
        return redirect(url_for('reports'))

    from_date = (request.form.get('from_date') or '').strip()
    to_date = (request.form.get('to_date') or '').strip()

    today_str = datetime.now().strftime('%Y-%m-%d')
    if not from_date:
        from_date = '2000-01-01'
    if not to_date:
        to_date = today_str

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e3a5f'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    conn = get_db()

    if report_type == 'applications':
        # Application List Report
        status_filter = request.form.get('status_filter', 'all')

        elements.append(Paragraph('DCCCO - Loan Application Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))

        if status_filter == 'all':
            apps = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.loan_type, la.status,
                       la.submitted_at, u.name as submitted_by_name
                FROM loan_applications la
                LEFT JOIN users u ON la.submitted_by = u.id
                WHERE DATE(la.submitted_at) BETWEEN ? AND ?
                ORDER BY la.submitted_at DESC
            ''', (from_date, to_date)).fetchall()
        else:
            apps = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.loan_type, la.status,
                       la.submitted_at, u.name as submitted_by_name
                FROM loan_applications la
                LEFT JOIN users u ON la.submitted_by = u.id
                WHERE DATE(la.submitted_at) BETWEEN ? AND ? AND la.status = ?
                ORDER BY la.submitted_at DESC
            ''', (from_date, to_date, status_filter)).fetchall()

        data = [['ID', 'Member Name', 'Amount', 'Type', 'Status', 'Submitted By', 'Date']]
        for app_row in apps:
            data.append([
                _report_text(app_row['id']),
                _report_text(app_row['member_name'], 20),
                _report_money(app_row['loan_amount']),
                _report_text(app_row['loan_type'], 15),
                _report_text(app_row['status'], 20),
                _report_text(app_row['submitted_by_name'], 15),
                _report_date(app_row['submitted_at']),
            ])
        
        table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f'Total Applications: {len(apps)}', styles['Normal']))
        
    elif report_type == 'ci_reports':
        # CI Reports
        ci_staff_filter = request.form.get('ci_staff_filter', 'all')
        
        elements.append(Paragraph('DCCCO - Credit Investigation Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        if ci_staff_filter == 'all':
            cis = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.ci_completed_at,
                       u.name as ci_staff_name, la.ci_latitude, la.ci_longitude
                FROM loan_applications la
                LEFT JOIN users u ON la.assigned_ci_staff = u.id
                WHERE la.status = 'ci_completed' 
                AND DATE(la.ci_completed_at) BETWEEN ? AND ?
                ORDER BY la.ci_completed_at DESC
            ''', (from_date, to_date)).fetchall()
        else:
            cis = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.ci_completed_at,
                       u.name as ci_staff_name, la.ci_latitude, la.ci_longitude
                FROM loan_applications la
                LEFT JOIN users u ON la.assigned_ci_staff = u.id
                WHERE la.status = 'ci_completed' 
                AND DATE(la.ci_completed_at) BETWEEN ? AND ?
                AND la.assigned_ci_staff = ?
                ORDER BY la.ci_completed_at DESC
            ''', (from_date, to_date, ci_staff_filter)).fetchall()
        
        data = [['ID', 'Member Name', 'Amount', 'CI Staff', 'Completed Date', 'Location']]
        for ci in cis:
            location = 'N/A'
            lat = ci['ci_latitude']
            lon = ci['ci_longitude']
            if lat and lon:
                try:
                    location = f"{str(lat)[:8]}, {str(lon)[:8]}"
                except Exception:
                    location = 'N/A'

            data.append([
                _report_text(ci['id']),
                _report_text(ci['member_name'], 25),
                _report_money(ci['loan_amount']),
                _report_text(ci['ci_staff_name'], 20),
                _report_date(ci['ci_completed_at']),
                location,
            ])
        
        table = Table(data, colWidths=[0.5*inch, 1.8*inch, 1*inch, 1.5*inch, 1.2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f'Total CI Completed: {len(cis)}', styles['Normal']))
        
    elif report_type == 'user_reports':
        # User Reports
        role_filter = request.form.get('role_filter', 'all')
        
        elements.append(Paragraph('DCCCO - User Activity Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        if role_filter == 'all':
            users = conn.execute('''
                SELECT u.id, u.name, u.email, u.role, u.created_at,
                       COUNT(DISTINCT la.id) as app_count
                FROM users u
                LEFT JOIN loan_applications la ON 
                    (u.id = la.submitted_by OR u.id = la.assigned_ci_staff)
                    AND DATE(la.submitted_at) BETWEEN ? AND ?
                WHERE u.is_approved = 1
                GROUP BY u.id
                ORDER BY app_count DESC, u.name
            ''', (from_date, to_date)).fetchall()
        else:
            users = conn.execute('''
                SELECT u.id, u.name, u.email, u.role, u.created_at,
                       COUNT(DISTINCT la.id) as app_count
                FROM users u
                LEFT JOIN loan_applications la ON 
                    (u.id = la.submitted_by OR u.id = la.assigned_ci_staff)
                    AND DATE(la.submitted_at) BETWEEN ? AND ?
                WHERE u.is_approved = 1 AND u.role = ?
                GROUP BY u.id
                ORDER BY app_count DESC, u.name
            ''', (from_date, to_date, role_filter)).fetchall()
        
        data = [['ID', 'Name', 'Email', 'Role', 'Applications', 'Joined']]
        for user in users:
            data.append([
                _report_text(user['id']),
                _report_text(user['name'], 20),
                _report_text(user['email'], 25),
                _report_text(user['role'], 20),
                _report_text(user['app_count']),
                _report_date(user['created_at']),
            ])
        
        table = Table(data, colWidths=[0.5*inch, 1.5*inch, 2*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f'Total Users: {len(users)}', styles['Normal']))
        
    elif report_type == 'transaction_summary':
        # Transaction Summary
        group_by = request.form.get('group_by', 'status')
        
        elements.append(Paragraph('DCCCO - Transaction Summary Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        if group_by == 'status':
            summary = conn.execute('''
                SELECT status, COUNT(*) as count, SUM(loan_amount) as total_amount
                FROM loan_applications
                WHERE DATE(submitted_at) BETWEEN ? AND ?
                GROUP BY status
                ORDER BY count DESC
            ''', (from_date, to_date)).fetchall()
            
            data = [['Status', 'Count', 'Total Amount']]
            for row in summary:
                data.append([
                    _report_text(row['status']),
                    _report_text(row['count']),
                    _report_money(row['total_amount']) if row['total_amount'] else '₱0.00',
                ])

        elif group_by == 'loan_type':
            summary = conn.execute('''
                SELECT loan_type, COUNT(*) as count, SUM(loan_amount) as total_amount
                FROM loan_applications
                WHERE DATE(submitted_at) BETWEEN ? AND ?
                GROUP BY loan_type
                ORDER BY count DESC
            ''', (from_date, to_date)).fetchall()
            
            data = [['Loan Type', 'Count', 'Total Amount']]
            for row in summary:
                data.append([
                    _report_text(row['loan_type']),
                    _report_text(row['count']),
                    _report_money(row['total_amount']) if row['total_amount'] else '₱0.00',
                ])
                
        else:  # month
            if is_postgresql():
                month_sql = '''
                    SELECT TO_CHAR(submitted_at, 'YYYY-MM') as month,
                           COUNT(*) as count, SUM(loan_amount) as total_amount
                    FROM loan_applications
                    WHERE DATE(submitted_at) BETWEEN ? AND ?
                    GROUP BY TO_CHAR(submitted_at, 'YYYY-MM')
                    ORDER BY month DESC
                '''
            else:
                month_sql = '''
                    SELECT strftime('%Y-%m', submitted_at) as month,
                           COUNT(*) as count, SUM(loan_amount) as total_amount
                    FROM loan_applications
                    WHERE DATE(submitted_at) BETWEEN ? AND ?
                    GROUP BY month
                    ORDER BY month DESC
                '''
            summary = conn.execute(month_sql, (from_date, to_date)).fetchall()

            data = [['Month', 'Count', 'Total Amount']]
            for row in summary:
                data.append([
                    _report_text(row['month']),
                    _report_text(row['count']),
                    _report_money(row['total_amount']) if row['total_amount'] else '₱0.00',
                ])
        
        table = Table(data, colWidths=[3*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)
        
        total = conn.execute('''
            SELECT COUNT(*) as count, SUM(loan_amount) as total_amount
            FROM loan_applications
            WHERE DATE(submitted_at) BETWEEN ? AND ?
        ''', (from_date, to_date)).fetchone()

        elements.append(Spacer(1, 0.3*inch))
        total_count = total['count'] if total else 0
        total_amount_val = total['total_amount'] if total else 0
        elements.append(
            Paragraph(
                f'<b>Grand Total:</b> {total_count} applications, {_report_money(total_amount_val)}',
                styles['Normal'],
            )
        )

    else:
        conn.close()
        flash(f'Unknown report type: {report_type}', 'warning')
        return redirect(url_for('reports'))

    try:
        conn.close()
    except Exception:
        pass

    if not elements:
        flash('No data available for the selected range.', 'info')
        return redirect(url_for('reports'))

    try:
        doc.build(elements)
    except Exception as build_err:
        print(f"ERROR building report PDF: {build_err}")
        import traceback
        traceback.print_exc()
        flash('Could not build the report. Please try a different date range.', 'danger')
        return redirect(url_for('reports'))

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'DCCCO_{report_type}_{from_date}_to_{to_date}.pdf',
    )

# PASSWORD CHANGE & RESET ROUTES
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    import time as _time
    _t0 = _time.monotonic()
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('change_password'))
        
        # Verify current password
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=?', (current_user.id,)).fetchone()
        conn.close()
        
        if not check_password_hash(user['password_hash'], current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('change_password'))
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('change_password'))
        
        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('change_password'))
        
        # Update password
        conn = get_db()
        new_hash = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password_hash=? WHERE id=?', (new_hash, current_user.id))
        conn.commit()
        conn.close()
        
        flash('Password updated successfully!', 'success')
        return redirect(url_for('index'))
    
    conn = get_db()
    _t_q0 = _time.monotonic()
    row = conn.execute(
        "SELECT COUNT(*) as count FROM notifications"
        " WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'",
        (current_user.id,)
    ).fetchone()
    unread_count = row['count'] if row else 0
    conn.close()

    _total = _time.monotonic() - _t0
    if _total > 0.3:
        _perf_logger.warning(
            'change_password GET slow %.3fs | notif_count=%.0fms'
            ' — if this is slow, check before_request / context_processor',
            _total, (_time.monotonic() - _t_q0) * 1000,
        )

    return render_template('change_password.html', unread_count=unread_count)

@app.route('/update_backup_email', methods=['POST'])
@login_required
def update_backup_email():
    backup_email = request.form.get('backup_email', '').strip()
    
    conn = get_db()
    conn.execute('UPDATE users SET backup_email=? WHERE id=?', (backup_email, current_user.id))
    conn.commit()
    conn.close()
    
    flash('Backup email updated successfully!', 'success')
    return redirect(url_for('change_password'))

@app.route('/update_signature', methods=['POST'])
@login_required
def update_signature():
    signature_data = request.form.get('signature_data')
    
    if not signature_data or not signature_data.startswith('data:image'):
        flash('Invalid signature data', 'danger')
        return redirect(url_for('change_password'))
    
    try:
        import base64
        # Delete old signature if exists
        conn = get_db()
        old_sig = conn.execute('SELECT signature_path FROM users WHERE id=?', (current_user.id,)).fetchone()
        if old_sig and old_sig['signature_path']:
            try:
                os.remove(old_sig['signature_path'])
            except:
                pass
        
        # Save new signature
        signature_base64 = signature_data.split(',')[1]
        signature_bytes = base64.b64decode(signature_base64)
        signature_filename = f"signature_{current_user.email.replace('@', '').replace('.', '')}_{uuid.uuid4().hex[:8]}.png"
        signature_path = os.path.join(app.config['SIGNATURE_FOLDER'], signature_filename)
        with open(signature_path, 'wb') as f:
            f.write(signature_bytes)
        
        # Update database
        conn.execute('UPDATE users SET signature_path=? WHERE id=?', (signature_path, current_user.id))
        conn.commit()
        conn.close()
        
        flash('Signature updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating signature: {str(e)}', 'danger')
    
    return redirect(url_for('change_password'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    
    if not name or not email:
        flash('Name and email are required', 'danger')
        return redirect(url_for('change_password'))
    
    # Check if email is already taken by another user
    conn = get_db()
    existing = conn.execute('SELECT id FROM users WHERE email=? AND id!=?', (email, current_user.id)).fetchone()
    if existing:
        conn.close()
        flash('Email already in use by another account', 'danger')
        return redirect(url_for('change_password'))
    
    # Handle profile photo upload
    profile_photo_path = None
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and file.filename:
            if not allowed_file(file.filename):
                conn.close()
                flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF', 'danger')
                return redirect(url_for('change_password'))
            
            # Delete old photo if exists
            old_photo = conn.execute('SELECT profile_photo FROM users WHERE id=?', (current_user.id,)).fetchone()
            if old_photo and old_photo['profile_photo']:
                try:
                    os.remove(old_photo['profile_photo'])
                except:
                    pass
            
            # Save new photo
            filename = sanitize_filename(file.filename)
            unique_filename = f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}_{filename}"
            profile_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(profile_photo_path)
    
    # Update database
    if profile_photo_path:
        conn.execute('UPDATE users SET name=?, email=?, profile_photo=? WHERE id=?', 
                    (name, email, profile_photo_path, current_user.id))
    else:
        conn.execute('UPDATE users SET name=?, email=? WHERE id=?', 
                    (name, email, current_user.id))
    conn.commit()
    conn.close()
    
    # Update current_user object
    current_user.name = name
    current_user.email = email
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('change_password'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        try:
            step = request.form.get('step', 'send_code')
            email = request.form.get('email', '').strip()
            
            if not email:
                flash('Please enter your email address.', 'danger')
                return render_template('forgot_password.html', email='', code='')
            
            conn = get_db()
            
            if step == 'send_code':
                # ONLY use the registered email (not backup email)
                user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                
                if user:
                    import random
                    code = str(random.randint(100000, 999999))
                    expires = (now_ph() + timedelta(minutes=15)).isoformat()
                    
                    conn.execute('UPDATE users SET password_reset_token=?, password_reset_expires=? WHERE id=?',
                                (code, expires, user['id']))
                    conn.commit()
                    
                    # Send code to the registered email only
                    email_sent = send_verification_email(user['email'], code, user['name'])
                    conn.close()
                    
                    if email_sent == True:
                        flash('Verification code sent to your registered email! Check your inbox.', 'success')
                        return render_template('forgot_password.html', show_code_input=True, email=email, code='')
                    elif email_sent == "RESEND_LIMIT":
                        flash(f'Testing Mode: Email can only be sent to tangentejerremiah9@gmail.com. For production use, a domain needs to be verified. Please contact admin.', 'info')
                        return redirect(url_for('forgot_password'))
                    else:
                        flash('Unable to send email. Please try again later.', 'danger')
                        return redirect(url_for('forgot_password'))
                else:
                    conn.close()
                    flash('If that email exists, a verification code has been sent.', 'info')
                    return redirect(url_for('forgot_password'))
            
            elif step == 'verify_code':
                code = request.form.get('code', '').strip()
                
                if not code:
                    flash('Please enter the verification code.', 'danger')
                    conn.close()
                    return render_template('forgot_password.html', show_code_input=True, email=email, code='')
                
                # ONLY check registered email (not backup email)
                user = conn.execute('SELECT * FROM users WHERE email=? AND password_reset_token=?', 
                                  (email, code)).fetchone()
                
                if user and user['password_reset_expires']:
                    expires = datetime.fromisoformat(user['password_reset_expires'])
                    if now_ph() <= expires:
                        conn.close()
                        flash('Code verified! Enter your new password.', 'success')
                        return render_template('forgot_password.html', show_password_input=True, email=email, code=code)
                    else:
                        conn.close()
                        flash('Verification code has expired. Please request a new one.', 'danger')
                        return redirect(url_for('forgot_password'))
                else:
                    conn.close()
                    flash('Invalid verification code. Please try again.', 'danger')
                    return render_template('forgot_password.html', show_code_input=True, email=email, code='')
            
            elif step == 'reset_password':
                code = request.form.get('code', '').strip()
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')
                
                if not new_password or not confirm_password:
                    flash('Please enter both password fields.', 'danger')
                    conn.close()
                    return render_template('forgot_password.html', show_password_input=True, email=email, code=code)
                
                if new_password != confirm_password:
                    flash('Passwords do not match!', 'danger')
                    conn.close()
                    return render_template('forgot_password.html', show_password_input=True, email=email, code=code)
                
                # ONLY check registered email (not backup email)
                user = conn.execute('SELECT * FROM users WHERE email=? AND password_reset_token=?', 
                                  (email, code)).fetchone()
                
                if user:
                    hashed = generate_password_hash(new_password)
                    # Update password without changing approval status
                    conn.execute('UPDATE users SET password_hash=?, password_reset_token=NULL, password_reset_expires=NULL WHERE id=?',
                                (hashed, user['id']))
                    conn.commit()
                    conn.close()
                    
                    flash('Password reset successful! You can now login with your new password.', 'success')
                    return redirect(url_for('login'))
                else:
                    conn.close()
                    flash('Session expired. Please start over.', 'danger')
                    return redirect(url_for('forgot_password'))
            
            conn.close()
            return redirect(url_for('forgot_password'))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html', email='', code='')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE password_reset_token=?', (token,)).fetchone()
    
    if not user:
        flash('Invalid or expired reset link', 'danger')
        conn.close()
        return redirect(url_for('login'))
    
    # Check if token expired
    if user['password_reset_expires']:
        expires = datetime.fromisoformat(user['password_reset_expires'])
        if now_ph() > expires:
            flash('Reset link has expired', 'danger')
            conn.close()
            return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            conn.close()
            return redirect(url_for('reset_password', token=token))
        
        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            flash(message, 'danger')
            conn.close()
            return redirect(url_for('reset_password', token=token))
        
        # Update password and clear reset token
        new_hash = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password_hash=?, password_reset_token=NULL, password_reset_expires=NULL WHERE id=?',
                    (new_hash, user['id']))
        conn.commit()
        conn.close()
        
        flash('Password reset successfully! You can now login.', 'success')
        return redirect(url_for('login'))
    
    conn.close()
    return render_template('reset_password.html')

# Real-time Dashboard API Endpoints
@app.route('/api/admin/applications')
@login_required
def api_admin_applications():
    """Dashboard-shaped snapshot for realtime refresh (matches admin_dashboard queries)."""
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db()
    _LA_COLS = (
        'la.id, la.status, la.member_name, la.loan_amount, la.loan_type,'
        ' la.submitted_at, la.needs_ci_interview, la.assigned_ci_staff,'
        ' u1.name AS loan_staff_name, u2.name AS ci_staff_name'
    )
    _LA_JOIN = (
        'FROM loan_applications la'
        ' LEFT JOIN users u1 ON la.submitted_by = u1.id'
        ' LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id'
    )
    applications = conn.execute(
        f'SELECT {_LA_COLS} {_LA_JOIN}'
        " WHERE la.status IN ('ci_completed','approved','disapproved','deferred')"
        " OR (la.needs_ci_interview = 0 AND la.status = 'submitted')"
        ' ORDER BY la.submitted_at ASC, la.id ASC'
    ).fetchall()
    in_process_applications = conn.execute(
        f'SELECT {_LA_COLS} {_LA_JOIN}'
        " WHERE la.status IN ('submitted','assigned_to_ci')"
        ' ORDER BY la.submitted_at ASC, la.id ASC'
    ).fetchall()
    conn.close()

    return jsonify({
        'applications': [dict(app) for app in applications],
        'in_process_applications': [dict(app) for app in in_process_applications],
    })

@app.route('/api/loan/applications')
@login_required
def api_loan_applications():
    if current_user.role != 'loan_staff':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db()
    applications = conn.execute('''
        SELECT la.id, la.status, la.member_name, la.loan_amount, la.loan_type,
               la.submitted_at, la.needs_ci_interview, la.assigned_ci_staff,
               u.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.assigned_ci_staff = u.id
        WHERE la.submitted_by = ?
        ORDER BY la.submitted_at ASC, la.id ASC
    ''', (current_user.id,)).fetchall()
    conn.close()

    return jsonify([dict(app) for app in applications])

@app.route('/api/ci/applications')
@login_required
def api_ci_applications():
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db()
    applications = conn.execute('''
        SELECT la.id, la.status, la.member_name, la.member_address, la.loan_amount,
               la.loan_type, la.submitted_at, la.needs_ci_interview, la.assigned_ci_staff,
               u.name as loan_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.submitted_by = u.id
        WHERE la.assigned_ci_staff = ?
        ORDER BY la.submitted_at ASC, la.id ASC
    ''', (current_user.id,)).fetchall()
    conn.close()

    return jsonify([dict(app) for app in applications])

# LOAN TYPES MANAGEMENT ROUTES
@app.route('/admin/loan-types')
@login_required
def manage_loan_types():
    if not can_manage_loan_types(current_user):
        flash('Unauthorized — Loan Types requires permission from Manage Permissions (Loan Types or System Settings).', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    loan_types = _fetch_loan_types_flexible(conn, active_only=False)
    row = conn.execute("SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'",
                                (current_user.id,)).fetchone()
    unread_count = row['count'] if row else 0
    conn.close()
    
    return render_template('manage_loan_types.html', loan_types=loan_types, unread_count=unread_count)

@app.route('/api/loan-types')
def get_loan_types():
    """Get all active loan types for dropdowns - Public API for submit form"""
    conn = get_db()
    loan_types = _fetch_loan_types_flexible(conn, active_only=True)
    conn.close()
    return jsonify([{'id': lt.get('id'), 'name': lt.get('name')} for lt in loan_types])

@app.route('/api/loan-types/add', methods=['POST'])
@login_required
def add_loan_type():
    if not can_manage_loan_types(current_user):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    
    conn = get_db()
    try:
        schema = _loan_types_schema_info(conn)
        name_key = schema['name_key']
        cols = schema['columns']

        if 'description' in cols:
            conn.execute(f'INSERT INTO loan_types ({name_key}, description) VALUES (?, ?)', (name, description))
        else:
            conn.execute(f'INSERT INTO loan_types ({name_key}) VALUES (?)', (name,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Loan type added successfully'})
    except Exception as e:
        conn.close()
        msg = str(e).lower()
        if 'duplicate' in msg or 'unique' in msg:
            return jsonify({'success': False, 'error': 'Loan type already exists'}), 400
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/loan-types/update/<int:id>', methods=['POST'])
@login_required
def update_loan_type(id):
    if not can_manage_loan_types(current_user):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    
    conn = get_db()
    try:
        schema = _loan_types_schema_info(conn)
        name_key = schema['name_key']
        cols = schema['columns']

        set_parts = [f"{name_key}=?"]
        values = [name]
        if 'description' in cols:
            set_parts.append('description=?')
            values.append(description)
        if 'updated_at' in cols:
            set_parts.append('updated_at=CURRENT_TIMESTAMP')
        values.append(id)

        conn.execute(f"UPDATE loan_types SET {', '.join(set_parts)} WHERE id=?", tuple(values))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Loan type updated successfully'})
    except Exception as e:
        conn.close()
        msg = str(e).lower()
        if 'duplicate' in msg or 'unique' in msg:
            return jsonify({'success': False, 'error': 'Loan type name already exists'}), 400
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/loan-types/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_loan_type(id):
    if not can_manage_loan_types(current_user):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db()
    loan_type = conn.execute('SELECT is_active FROM loan_types WHERE id=?', (id,)).fetchone()
    
    if not loan_type:
        conn.close()
        return jsonify({'success': False, 'error': 'Loan type not found'}), 404
    
    new_status = 0 if loan_type['is_active'] == 1 else 1
    conn.execute('UPDATE loan_types SET is_active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (new_status, id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Loan type status updated', 'is_active': new_status})

@app.route('/api/loan-types/delete/<int:id>', methods=['POST'])
@login_required
def delete_loan_type(id):
    if not can_manage_loan_types(current_user):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db()
    try:
        conn.execute('DELETE FROM loan_types WHERE id=?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Loan type deleted successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Autocomplete API Endpoints - Auto-fill from previous applications
@app.route('/api/autocomplete/names', methods=['GET'])
@login_required
def autocomplete_names():
    """Get member names matching query"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    if is_postgresql():
        results = conn.execute('''
            SELECT DISTINCT ON (member_name) member_name, member_contact, member_address
            FROM loan_applications
            WHERE member_name ILIKE %s
            ORDER BY member_name, submitted_at DESC
            LIMIT 10
        ''', (f'%{query}%',)).fetchall()
    else:
        results = conn.execute('''
            SELECT member_name, member_contact, member_address
            FROM loan_applications
            WHERE member_name LIKE ?
            GROUP BY member_name
            ORDER BY MAX(submitted_at) DESC
            LIMIT 10
        ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    suggestions = [{
        'value': row['member_name'],
        'context': '',
    } for row in results]
    
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/contacts', methods=['GET'])
@login_required
def autocomplete_contacts():
    """Get contact numbers matching query"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    if is_postgresql():
        results = conn.execute('''
            SELECT DISTINCT ON (member_contact) member_contact, member_name
            FROM loan_applications
            WHERE member_contact ILIKE %s
            ORDER BY member_contact, submitted_at DESC
            LIMIT 10
        ''', (f'%{query}%',)).fetchall()
    else:
        results = conn.execute('''
            SELECT member_contact, member_name
            FROM loan_applications
            WHERE member_contact LIKE ?
            GROUP BY member_contact
            ORDER BY MAX(submitted_at) DESC
            LIMIT 10
        ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    suggestions = [{
        'value': row['member_contact'],
        'context': row['member_name']
    } for row in results if row['member_contact']]
    
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/addresses', methods=['GET'])
@login_required
def autocomplete_addresses():
    """Get addresses matching query"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    # PostgreSQL: ORDER BY columns must appear in the SELECT list when using DISTINCT.
    # Use a subquery to rank by recency, then deduplicate in the outer query.
    if is_postgresql():
        results = conn.execute('''
            SELECT DISTINCT ON (member_address) member_address, member_name
            FROM loan_applications
            WHERE member_address ILIKE %s
            ORDER BY member_address, submitted_at DESC
            LIMIT 10
        ''', (f'%{query}%',)).fetchall()
    else:
        results = conn.execute('''
            SELECT member_address, member_name
            FROM loan_applications
            WHERE member_address LIKE ?
            GROUP BY member_address
            ORDER BY MAX(submitted_at) DESC
            LIMIT 10
        ''', (f'%{query}%',)).fetchall()
    conn.close()

    suggestions = [{
        'value': row['member_address'],
        'context': row['member_name']
    } for row in results if row['member_address']]

    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/member_details', methods=['GET'])
@login_required
def autocomplete_member_details():
    """Get full member details by name for auto-fill"""
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Name required'})
    
    conn = get_db()
    # Get most recent application for this member
    result = conn.execute('''
        SELECT member_name, member_contact, member_address
        FROM loan_applications
        WHERE member_name = ?
        ORDER BY submitted_at DESC
        LIMIT 1
    ''', (name,)).fetchone()
    conn.close()
    
    if result:
        return jsonify({
            'success': True,
            'details': {
                'name': result['member_name'],
                'contact': result['member_contact'],
                'address': result['member_address']
            }
        })
    
    return jsonify({'success': False, 'error': 'Member not found'})

@app.route('/api/autocomplete/last_names', methods=['GET'])
@login_required
def autocomplete_last_names():
    """Get last names from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    # Search in ci_checklist_data JSON field
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    last_names = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'applicant_last_name' in data and query.lower() in data['applicant_last_name'].lower():
                last_names.add(data['applicant_last_name'])
            if 'spouse_last_name' in data and query.lower() in data['spouse_last_name'].lower():
                last_names.add(data['spouse_last_name'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(last_names)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/first_names', methods=['GET'])
@login_required
def autocomplete_first_names():
    """Get first names from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    first_names = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'applicant_first_name' in data and query.lower() in data['applicant_first_name'].lower():
                first_names.add(data['applicant_first_name'])
            if 'spouse_first_name' in data and query.lower() in data['spouse_first_name'].lower():
                first_names.add(data['spouse_first_name'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(first_names)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/middle_names', methods=['GET'])
@login_required
def autocomplete_middle_names():
    """Get middle names from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    middle_names = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'applicant_middle_name' in data and query.lower() in data['applicant_middle_name'].lower():
                middle_names.add(data['applicant_middle_name'])
            if 'spouse_middle_name' in data and query.lower() in data['spouse_middle_name'].lower():
                middle_names.add(data['spouse_middle_name'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(middle_names)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/barangays', methods=['GET'])
@login_required
def autocomplete_barangays():
    """Get barangays from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    barangays = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'barangay' in data and query.lower() in data['barangay'].lower():
                barangays.add(data['barangay'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(barangays)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/municipalities', methods=['GET'])
@login_required
def autocomplete_municipalities():
    """Get municipalities from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    municipalities = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'municipality' in data and query.lower() in data['municipality'].lower():
                municipalities.add(data['municipality'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(municipalities)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/provinces', methods=['GET'])
@login_required
def autocomplete_provinces():
    """Get provinces from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    provinces = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'province' in data and query.lower() in data['province'].lower():
                provinces.add(data['province'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(provinces)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

# SMS Templates Management Routes
@app.route('/manage_sms_templates')
@login_required
def manage_sms_templates():
    """Manage SMS templates page"""
    import time as _time
    _t0 = _time.monotonic()

    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

    try:
        ensure_sms_templates_table()
        ensure_sms_sent_log_table()
        conn = get_db()

        # Fetch only the columns the template renders; avoids pulling large message bodies for all rows.
        templates = conn.execute(
            'SELECT id, name, category, message, is_active, created_at'
            ' FROM sms_templates ORDER BY category, name'
        ).fetchall()
        _t_q1 = _time.monotonic()

        approved_templates = [t for t in templates if t['category'] == 'approved']
        disapproved_templates = [t for t in templates if t['category'] == 'disapproved']
        deferred_templates = [t for t in templates if t['category'] == 'deferred']
        custom_templates = [t for t in templates if t['category'] == 'custom']

        approved_count = len(approved_templates)
        disapproved_count = len(disapproved_templates)
        deferred_count = len(deferred_templates)
        custom_count = len(custom_templates)

        # SMS sent-log: limit initial load to 50 rows. Search allows up to 200.
        search_q = (request.args.get('q') or '').strip()
        if search_q:
            like = f'%{search_q}%'
            sent_rows = conn.execute(
                '''
                SELECT s.id, s.phone_number, s.message_body, s.member_name,
                       s.category, s.status, s.sent_at, u.name AS sent_by_name
                FROM sms_sent_log s
                LEFT JOIN users u ON s.sent_by_user_id = u.id
                WHERE (
                    LOWER(s.phone_number) LIKE LOWER(?) OR
                    LOWER(s.message_body) LIKE LOWER(?) OR
                    LOWER(COALESCE(s.member_name, '')) LIKE LOWER(?) OR
                    LOWER(COALESCE(s.category, '')) LIKE LOWER(?) OR
                    LOWER(COALESCE(s.status, '')) LIKE LOWER(?)
                )
                ORDER BY s.sent_at DESC
                LIMIT 200
                ''',
                (like, like, like, like, like),
            ).fetchall()
        else:
            sent_rows = conn.execute(
                '''
                SELECT s.id, s.phone_number, s.message_body, s.member_name,
                       s.category, s.status, s.sent_at, u.name AS sent_by_name
                FROM sms_sent_log s
                LEFT JOIN users u ON s.sent_by_user_id = u.id
                ORDER BY s.sent_at DESC
                LIMIT 50
                '''
            ).fetchall()
        _t_q2 = _time.monotonic()

        sent_log_count = conn.execute('SELECT COUNT(*) AS c FROM sms_sent_log').fetchone()
        total_sent_ever = sent_log_count['c'] if sent_log_count else 0

        sent_messages = [dict(r) for r in sent_rows]

        row = conn.execute(
            "SELECT COUNT(*) as count FROM notifications"
            " WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%'",
            (current_user.id,)
        ).fetchone()
        unread_count = row['count'] if row else 0

        conn.close()

        _total = _time.monotonic() - _t0
        if _total > 0.5:
            _perf_logger.warning(
                'manage_sms_templates slow %.3fs | templates=%.0fms sent_log=%.0fms',
                _total, (_t_q1 - _t0) * 1000, (_t_q2 - _t_q1) * 1000,
            )
        
        return render_template('manage_sms_templates.html', 
                             templates=templates,
                             approved_templates=approved_templates,
                             disapproved_templates=disapproved_templates,
                             deferred_templates=deferred_templates,
                             custom_templates=custom_templates,
                             approved_count=approved_count,
                             disapproved_count=disapproved_count,
                             deferred_count=deferred_count,
                             custom_count=custom_count,
                             sent_messages=sent_messages,
                             search_q=search_q,
                             total_sent_ever=total_sent_ever,
                             unread_count=unread_count)
    
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        flash(f'Error loading SMS templates: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/api/get_sms_templates/<category>')
@login_required
def get_sms_templates(category):
    """Get SMS templates by category (approved, disapproved, deferred)"""
    ensure_sms_templates_table()
    conn = get_db()
    templates = conn.execute('''
        SELECT id, name, message, category 
        FROM sms_templates 
        WHERE category = ? AND is_active = 1
        ORDER BY name
    ''', (category,)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'templates': [dict(t) for t in templates]
    })

@app.route('/send_sms_and_update_status/<int:app_id>', methods=['POST'])
@login_required
def send_sms_and_update_status(app_id):
    """Send SMS and update application status (approve/disapprove/defer)"""
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        action = data.get('action')  # 'approved', 'disapproved', or 'deferred'
        message = data.get('message', '').strip()
        notes = data.get('notes', '').strip()
        
        if not action or action not in ['approved', 'disapproved', 'deferred']:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        if not message:
            return jsonify({'success': False, 'error': 'SMS message is required'}), 400
        
        conn = get_db()
        
        # Get application details
        app_data = conn.execute('''
            SELECT * FROM loan_applications WHERE id = ?
        ''', (app_id,)).fetchone()
        
        if not app_data:
            conn.close()
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Update application status
        conn.execute('''
            UPDATE loan_applications 
            SET status = ?, admin_notes = ?, admin_decision_at = ?
            WHERE id = ?
        ''', (action, notes, now_ph().isoformat(), app_id))
        
        conn.commit()
        conn.close()

        # Snap values for background work (row may be closed)
        _name = app_data['member_name']
        _lamount = app_data['loan_amount']
        _contact = app_data['member_contact']
        try:
            _raw_sb = app_data['submitted_by']
            _sub_by = int(_raw_sb) if _raw_sb is not None else None
        except (TypeError, ValueError, KeyError):
            _sub_by = None

        # SMS in-process so the client gets real success/fail from Semaphore (not background)
        sms_sent = None
        sms_error = None
        if _contact and message:
            _tid = data.get('template_id')
            try:
                _tid = int(_tid) if _tid is not None and str(_tid).strip() != '' else None
            except (TypeError, ValueError):
                _tid = None
            sent_ok, sent_err = send_sms(
                _contact,
                message,
                loan_application_id=app_id,
                sent_by_user_id=current_user.id,
                category=action,
                template_id=_tid,
                member_name=_name,
            )
            sms_sent = bool(sent_ok)
            if not sent_ok:
                sms_error = sent_err or 'SMS could not be sent (see Sent log on SMS Templates).'
        elif not _contact and message:
            sms_error = 'No member phone on file; SMS not sent.'

        def _emit_update():
            try:
                la = float(_lamount) if _lamount is not None else 0.0
                socketio.emit('application_updated', {
                    'id': app_id,
                    'status': action,
                    'member_name': _name,
                    'loan_amount': la,
                    'submitted_by': _sub_by,
                    'timestamp': now_ph().isoformat()
                })
            except Exception as ex:
                app.logger.debug('background emit application_updated: %s', ex)

        run_background_task(_emit_update)

        msg = f'Application {action} and saved.'
        if _contact and message:
            msg = f'Application {action}. ' + (
                'SMS was sent to the member.'
                if sms_sent
                else (sms_error or 'SMS was not sent.')
            )
        return jsonify({
            'success': True,
            'message': msg,
            'sms_sent': sms_sent,
            'sms_error': sms_error,
        })
        
    except Exception as e:
        print(f"Error in send_sms_and_update_status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/send_bulk_sms', methods=['POST'])
@login_required
def send_bulk_sms_route():
    """Send SMS to multiple phone numbers at once"""
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        phone_numbers = data.get('phone_numbers', '')  # Comma-separated or list
        message = data.get('message', '').strip()
        
        if not phone_numbers:
            return jsonify({'success': False, 'error': 'Phone numbers are required'}), 400
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # Send bulk SMS
        results = send_bulk_sms(phone_numbers, message, sent_by_user_id=current_user.id)
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'Sent to {results["success"]} of {results["total"]} numbers'
        })
        
    except Exception as e:
        print(f"Error in send_bulk_sms_route: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add_sms_template', methods=['POST'])
@login_required
def add_sms_template():
    """Add new SMS template"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    try:
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        message = request.form.get('message', '').strip()
        
        if not name or not category or not message:
            flash('All fields are required', 'danger')
            return redirect(url_for('manage_sms_templates'))
        
        conn = get_db()
        
        # Check if template with same name already exists
        existing = conn.execute('SELECT id FROM sms_templates WHERE name = ? AND category = ?', (name, category)).fetchone()
        if existing:
            conn.close()
            flash(f'Template "{name}" already exists in {category} category', 'warning')
            return redirect(url_for('manage_sms_templates'))
        
        conn.execute('''
            INSERT INTO sms_templates (name, category, message, is_active)
            VALUES (?, ?, ?, 1)
        ''', (name, category, message))
        conn.commit()
        conn.close()
        
        flash('SMS template added successfully', 'success')
        return redirect(url_for('manage_sms_templates'))
        
    except Exception as e:
        print(f"Error adding SMS template: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error adding template: {str(e)}', 'danger')
        return redirect(url_for('manage_sms_templates'))

@app.route('/update_sms_template', methods=['POST'])
@login_required
def update_sms_template():
    """Update existing SMS template"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    try:
        template_id = request.form.get('template_id')
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        message = request.form.get('message', '').strip()
        
        if not template_id or not name or not category or not message:
            flash('All fields are required', 'danger')
            return redirect(url_for('manage_sms_templates'))
        
        conn = get_db()
        
        # Check if template exists
        existing = conn.execute('SELECT id FROM sms_templates WHERE id = ?', (template_id,)).fetchone()
        if not existing:
            conn.close()
            flash('Template not found', 'danger')
            return redirect(url_for('manage_sms_templates'))
        
        conn.execute('''
            UPDATE sms_templates 
            SET name = ?, category = ?, message = ?
            WHERE id = ?
        ''', (name, category, message, template_id))
        conn.commit()
        conn.close()
        
        flash('SMS template updated successfully', 'success')
        return redirect(url_for('manage_sms_templates'))
        
    except Exception as e:
        print(f"Error updating SMS template: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error updating template: {str(e)}', 'danger')
        return redirect(url_for('manage_sms_templates'))

@app.route('/delete_sms_template/<int:template_id>', methods=['POST'])
@login_required
def delete_sms_template(template_id):
    """Delete SMS template"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    conn.execute('DELETE FROM sms_templates WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()
    
    flash('SMS template deleted successfully', 'success')
    return redirect(url_for('manage_sms_templates'))

@app.route('/toggle_sms_template/<int:template_id>', methods=['POST'])
@login_required
def toggle_sms_template(template_id):
    """Toggle SMS template active status"""
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db()
    template = conn.execute('SELECT is_active FROM sms_templates WHERE id = ?', (template_id,)).fetchone()
    
    if not template:
        conn.close()
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    
    new_status = 0 if template['is_active'] else 1
    conn.execute('UPDATE sms_templates SET is_active = ? WHERE id = ?', (new_status, template_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'is_active': new_status})

if __name__ == '__main__':
    import os
    
    # Create required folders if they don't exist
    folders = [
        app.config['UPLOAD_FOLDER'],
        app.config['SIGNATURE_FOLDER'],
        'message_attachments',
        'voice_messages'
    ]
    
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")
    
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 to accept connections from all interfaces
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
