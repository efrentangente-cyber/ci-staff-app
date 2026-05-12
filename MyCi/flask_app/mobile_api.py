"""
Mobile/native client API. Token-based (no Flask-Login session needed).

Design choices:
- Token = signed (HMAC) string with user_id + role + issued_at, kept stateless to avoid a new table.
- Idempotency-Key required on POST /api/loan_applications and POST /api/upload so
  WorkManager retries from the Android app never create duplicates.
- Same SQLite tables as the website (loan_applications, documents, users).
"""
from __future__ import annotations

import hmac
import hashlib
import json
import os
import sqlite3
import time
import uuid
from functools import wraps
from typing import Any, Dict, Optional, Tuple

from flask import Blueprint, current_app, g, jsonify, request
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename


mobile_api_bp = Blueprint("mobile_api", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# DB helper (mirrors get_db() in app.py to stay decoupled).
# ---------------------------------------------------------------------------
def _db() -> sqlite3.Connection:
    db_path = current_app.config["DATABASE"]
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error:
        pass
    return conn


def _ensure_idempotency_table(conn: sqlite3.Connection) -> None:
    """Stores Idempotency-Key -> response so duplicate POSTs return the same result."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS api_idempotency_keys (
            key TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            route TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )


# ---------------------------------------------------------------------------
# Token signing — stateless. Format:  base64url(payload_json).hex_signature
# ---------------------------------------------------------------------------
def _secret() -> bytes:
    s = current_app.config.get("SECRET_KEY") or os.environ.get("SECRET_KEY") or "dev-secret"
    return s.encode("utf-8")


def _sign(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_secret(), raw, hashlib.sha256).hexdigest()
    import base64
    body = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"{body}.{sig}"


def _verify(token: str) -> Optional[Dict[str, Any]]:
    if not token or "." not in token:
        return None
    body, sig = token.split(".", 1)
    import base64
    pad = "=" * (-len(body) % 4)
    try:
        raw = base64.urlsafe_b64decode(body + pad)
    except Exception:
        return None
    expected = hmac.new(_secret(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None


def require_token(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return jsonify({"error": "missing_token"}), 401
        payload = _verify(auth[7:].strip())
        if not payload:
            return jsonify({"error": "invalid_token"}), 401
        # Token TTL: 30 days. Web cookies live longer; native re-login is cheap.
        if int(time.time()) - int(payload.get("iat", 0)) > 60 * 60 * 24 * 30:
            return jsonify({"error": "expired_token"}), 401
        g.user_id = int(payload["sub"])
        g.role = payload.get("role")
        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Auth — JSON login is registered on the main Flask app (app.py) so POST /api/login
# is always reachable even if blueprint registration fails on a stale deploy.
# ---------------------------------------------------------------------------
def json_login_handler():
    """POST JSON { email, password } -> token; GET -> small discovery payload (helps 404 debugging)."""
    if request.method == "GET":
        return jsonify(
            {
                "ok": True,
                "login": "POST with application/json: {\"email\":\"...\",\"password\":\"...\"}",
            }
        ), 200

    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "email_password_required"}), 400

    conn = _db()
    row = conn.execute(
        "SELECT id, email, name, role, password_hash FROM users WHERE LOWER(email) = ?",
        (email,),
    ).fetchone()
    conn.close()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "invalid_credentials"}), 401

    token = _sign({"sub": row["id"], "role": row["role"], "iat": int(time.time())})
    return jsonify({
        "token": token,
        "userId": row["id"],
        "name": row["name"],
        "role": row["role"],
    })


@mobile_api_bp.get("/me")
@require_token
def me():
    conn = _db()
    row = conn.execute(
        "SELECT id, name, role FROM users WHERE id = ?", (g.user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not_found"}), 404
    return jsonify({"id": row["id"], "name": row["name"], "role": row["role"]})


# ---------------------------------------------------------------------------
# Loan applications
# ---------------------------------------------------------------------------
def _idem_lookup(conn: sqlite3.Connection, key: str, user_id: int, route: str) -> Optional[Dict[str, Any]]:
    _ensure_idempotency_table(conn)
    r = conn.execute(
        "SELECT response_json FROM api_idempotency_keys WHERE key = ? AND user_id = ? AND route = ?",
        (key, user_id, route),
    ).fetchone()
    return json.loads(r["response_json"]) if r else None


def _idem_save(conn: sqlite3.Connection, key: str, user_id: int, route: str, payload: Dict[str, Any]) -> None:
    _ensure_idempotency_table(conn)
    conn.execute(
        "INSERT OR REPLACE INTO api_idempotency_keys (key, user_id, route, response_json, created_at) VALUES (?, ?, ?, ?, ?)",
        (key, user_id, route, json.dumps(payload), int(time.time())),
    )


@mobile_api_bp.post("/loan_applications")
@require_token
def create_loan_application():
    if g.role != "loan_staff" and g.role != "admin":
        return jsonify({"error": "forbidden"}), 403

    idem = request.headers.get("Idempotency-Key")
    if not idem:
        return jsonify({"error": "missing_idempotency_key"}), 400

    data = request.get_json(silent=True) or {}
    name = (data.get("memberName") or "").strip()
    if not name:
        return jsonify({"error": "memberName_required"}), 400

    contact = data.get("memberContact")
    address = data.get("memberAddress")
    amount = data.get("loanAmount")
    needs_ci = int(data.get("needsCi") or 1)

    conn = _db()
    cached = _idem_lookup(conn, idem, g.user_id, "create_loan")
    if cached:
        conn.close()
        return jsonify(cached)

    dup = conn.execute(
        """
        SELECT id FROM loan_applications
        WHERE LOWER(member_name) = LOWER(?)
          AND status NOT IN ('rejected', 'approved')
        LIMIT 1
        """,
        (name,),
    ).fetchone()
    if dup:
        conn.close()
        return (
            jsonify(
                {"error": "duplicate_active_application", "existingId": dup["id"]}
            ),
            409,
        )

    cursor = conn.execute(
        """
        INSERT INTO loan_applications
          (member_name, member_contact, member_address, loan_amount, needs_ci_interview, submitted_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, contact, address, amount, needs_ci, g.user_id),
    )
    new_id = cursor.lastrowid
    response = {"id": new_id, "updatedAt": _iso_now()}
    _idem_save(conn, idem, g.user_id, "create_loan", response)
    conn.commit()
    conn.close()
    return jsonify(response)


@mobile_api_bp.post("/upload")
@require_token
def upload_document():
    if g.role not in ("loan_staff", "ci_staff", "admin"):
        return jsonify({"error": "forbidden"}), 403

    idem = request.headers.get("Idempotency-Key")
    if not idem:
        return jsonify({"error": "missing_idempotency_key"}), 400

    loan_app_id = request.form.get("loan_application_id")
    if not loan_app_id:
        return jsonify({"error": "loan_application_id_required"}), 400
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "file_required"}), 400

    conn = _db()
    cached = _idem_lookup(conn, idem, g.user_id, "upload")
    if cached:
        conn.close()
        return jsonify(cached)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    safe = secure_filename(file.filename)
    unique = f"{loan_app_id}_{uuid.uuid4().hex[:8]}_{safe}"
    path = os.path.join(upload_folder, unique)
    file.save(path)

    cursor = conn.execute(
        "INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by) VALUES (?, ?, ?, ?)",
        (loan_app_id, safe, path, g.user_id),
    )
    response = {"fileId": cursor.lastrowid, "loanApplicationId": int(loan_app_id)}
    _idem_save(conn, idem, g.user_id, "upload", response)
    conn.commit()
    conn.close()
    return jsonify(response)


@mobile_api_bp.get("/loan_applications")
@require_token
def list_loan_applications():
    conn = _db()
    rows = conn.execute(
        """
        SELECT id, member_name, member_contact, member_address, loan_amount,
               needs_ci_interview, status, submitted_at
        FROM loan_applications
        ORDER BY submitted_at DESC
        LIMIT 200
        """
    ).fetchall()
    conn.close()
    return jsonify({
        "loans": [_loan_dto(r) for r in rows],
        "serverNow": _iso_now(),
    })


@mobile_api_bp.get("/sync")
@require_token
def sync_delta():
    """Naive delta: returns recent rows. Optimize later by filtering on ?since=ISO."""
    return list_loan_applications()


# ---------------------------------------------------------------------------
# CI workflow
# ---------------------------------------------------------------------------
@mobile_api_bp.get("/ci/assigned")
@require_token
def ci_assigned():
    if g.role not in ("ci_staff", "admin"):
        return jsonify({"loans": [], "serverNow": _iso_now()})
    conn = _db()
    rows = conn.execute(
        """
        SELECT id, member_name, member_contact, member_address, loan_amount,
               needs_ci_interview, status, submitted_at, assigned_ci_staff,
               ci_notes, ci_checklist_data, ci_completed_at
        FROM loan_applications
        WHERE (status = 'assigned_to_ci' OR status = 'ci_completed')
          AND (assigned_ci_staff = ? OR ? = 'admin')
        ORDER BY submitted_at DESC
        LIMIT 200
        """,
        (g.user_id, g.role),
    ).fetchall()
    conn.close()
    return jsonify({"loans": [_loan_dto(r) for r in rows], "serverNow": _iso_now()})


@mobile_api_bp.post("/ci/complete")
@require_token
def ci_complete():
    """Mirrors website /ci/complete_interview/<id> POST: ci_notes, checklist_data,
    optional interview photos. Token-auth + Idempotency-Key for retry safety.
    """
    if g.role not in ("ci_staff", "admin"):
        return jsonify({"error": "forbidden"}), 403

    idem = request.headers.get("Idempotency-Key")
    if not idem:
        return jsonify({"error": "missing_idempotency_key"}), 400

    loan_app_id = request.form.get("loan_application_id", type=int)
    if not loan_app_id:
        return jsonify({"error": "loan_application_id_required"}), 400
    ci_notes = request.form.get("ci_notes") or ""
    checklist_data = request.form.get("checklist_data") or ""

    conn = _db()
    cached = _idem_lookup(conn, idem, g.user_id, "ci_complete")
    if cached:
        conn.close()
        return jsonify(cached)

    row = conn.execute(
        "SELECT status, assigned_ci_staff FROM loan_applications WHERE id = ?",
        (loan_app_id,),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "not_found"}), 404
    if g.role == "ci_staff" and row["assigned_ci_staff"] is not None and int(row["assigned_ci_staff"]) != int(g.user_id):
        conn.close()
        return jsonify({"error": "not_assigned_to_you"}), 403

    prev_status = row["status"]
    completed_at = _iso_now()
    conn.execute(
        """
        UPDATE loan_applications
        SET status = ?, ci_notes = ?, ci_checklist_data = ?, ci_completed_at = ?
        WHERE id = ?
        """,
        ("ci_completed", ci_notes, checklist_data, completed_at, loan_app_id),
    )

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)
    files = request.files.getlist("interview_photos") or []
    for f in files:
        if not f or not f.filename:
            continue
        safe = secure_filename(f.filename)
        unique = f"{loan_app_id}_interview_{uuid.uuid4().hex[:8]}_{safe}"
        path = os.path.join(upload_folder, unique)
        f.save(path)
        conn.execute(
            "INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by) VALUES (?, ?, ?, ?)",
            (loan_app_id, safe, path, g.user_id),
        )

    if prev_status != "ci_completed":
        conn.execute(
            "UPDATE users SET current_workload = current_workload - 1 WHERE id = ?",
            (g.user_id,),
        )

    response = {"id": loan_app_id, "updatedAt": completed_at}
    _idem_save(conn, idem, g.user_id, "ci_complete", response)
    conn.commit()
    conn.close()
    return jsonify(response)


def _loan_dto(r: sqlite3.Row) -> Dict[str, Any]:
    keys = r.keys()
    def _opt(name: str):
        return r[name] if name in keys else None
    return {
        "id": r["id"],
        "memberName": r["member_name"],
        "memberContact": r["member_contact"],
        "memberAddress": r["member_address"],
        "loanAmount": r["loan_amount"],
        "needsCi": r["needs_ci_interview"],
        "status": r["status"],
        "assignedCiStaffId": _opt("assigned_ci_staff"),
        "submittedAt": r["submitted_at"],
        "updatedAt": _opt("ci_completed_at") or r["submitted_at"],
        "ciNotes": _opt("ci_notes"),
        "ciChecklistJson": _opt("ci_checklist_data"),
        "ciCompletedAt": _opt("ci_completed_at"),
    }


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
