"""
Offline / idempotent CI interview completion — register in main app.

    from offline_interview_api import offline_interview_bp, ensure_offline_migrations
    ensure_offline_migrations()
    app.register_blueprint(offline_interview_bp)
"""
from __future__ import annotations

import base64
import os
import sqlite3
import uuid
from datetime import datetime

import json

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

_DIR = os.path.dirname(os.path.abspath(__file__))
# Same default as other scripts: app.db in process cwd (e.g. flask_app/ on Render and local)
UPLOAD_FOLDER = os.path.join(_DIR, "uploads")


def _db_path() -> str:
    try:
        custom = current_app.config.get("DATABASE")
        if custom:
            if os.path.isabs(custom):
                return custom
            return os.path.normpath(os.path.join(_DIR, custom))
    except RuntimeError:
        pass
    return os.path.join(_DIR, "app.db")

offline_interview_bp = Blueprint("offline_interview", __name__)


def _upload_folder() -> str:
    """Prefer main app.config['UPLOAD_FOLDER'] (same as HTML interview POST)."""
    try:
        rel = current_app.config.get("UPLOAD_FOLDER", "uploads")
        if os.path.isabs(rel):
            return rel
        return os.path.normpath(os.path.join(_DIR, rel))
    except RuntimeError:
        return UPLOAD_FOLDER


def _signature_folder() -> str:
    """Same folder as ci_application POST (profile / interview PNG snapshots)."""
    try:
        rel = current_app.config.get("SIGNATURE_FOLDER", "signatures")
        if os.path.isabs(rel):
            return rel
        return os.path.normpath(os.path.join(_DIR, rel))
    except RuntimeError:
        return os.path.join(_DIR, "signatures")


def _resolve_ci_signature_for_completion(request_form, application_id: int) -> str:
    """
    Align with ci_application POST: optional signature_data data-URL PNG, then profile file path,
    then display name fallback.
    """
    sig_raw = request_form.get("signature_data")
    if sig_raw and isinstance(sig_raw, str) and sig_raw.startswith("data:image"):
        try:
            comma = sig_raw.find(",")
            payload = sig_raw[comma + 1 :] if comma >= 0 else sig_raw
            png = base64.b64decode(payload)
            sig_dir = _signature_folder()
            os.makedirs(sig_dir, exist_ok=True)
            fname = f"ci_signature_{application_id}_{uuid.uuid4().hex[:8]}.png"
            full_path = os.path.join(sig_dir, fname)
            with open(full_path, "wb") as fh:
                fh.write(png)
            return full_path
        except Exception:
            pass
    prof = getattr(current_user, "signature_path", None)
    if prof and str(prof).strip():
        return str(prof).strip()
    return current_user.name


def _review_snapshot_from_loan_app_row(ar: sqlite3.Row) -> dict:
    """Match keys used by offline shell merge / package.json reviewers."""

    def _g(key: str):
        try:
            return ar[key]
        except (KeyError, IndexError):
            return None

    return {
        "serverId": _g("id"),
        "memberName": _g("member_name"),
        "memberAddress": _g("member_address"),
        "memberContact": _g("member_contact"),
        "loanAmount": _g("loan_amount"),
        "loanPurpose": _g("loan_purpose") or "",
        "lpsRemarks": _g("lps_remarks") or "",
        "caseStatus": _g("status"),
        "submittedAt": _g("submitted_at"),
    }


def upsert_offline_package_row_after_complete(
    conn: sqlite3.Connection,
    *,
    ci_staff_id: int,
    application_id: int,
    client_request_id: str,
    ci_notes: str | None,
    checklist_data: str | None,
    app_row: sqlite3.Row,
) -> None:
    """
    Always queue a row on /ci/offline_saves after a successful online complete_interview,
    so the CI sees the case under "Queued packages" (Continue / audit) even if the
    separate /api/ci/offline_package request from the app failed.
    """
    try:
        checklist_obj: object
        if checklist_data:
            try:
                checklist_obj = json.loads(checklist_data)
            except (json.JSONDecodeError, TypeError):
                checklist_obj = {"_raw": str(checklist_data)}
        else:
            checklist_obj = {}
    except Exception:
        checklist_obj = {}

    now_iso = datetime.now().isoformat()
    review = _review_snapshot_from_loan_app_row(app_row)

    existing = conn.execute(
        """
        SELECT id, package_id, status FROM ci_offline_packages
        WHERE ci_staff_id = ? AND application_id = ? AND client_request_id = ?
        """,
        (ci_staff_id, application_id, client_request_id),
    ).fetchone()

    stable_pkg = "online-" + str(uuid.uuid5(uuid.NAMESPACE_URL, "crc:" + client_request_id))

    payload_dict = {
        "packageId": existing["package_id"] if existing else stable_pkg,
        "applicationId": application_id,
        "clientRequestId": client_request_id,
        "format": "ci_online_complete_v1",
        "notes": (ci_notes or "").strip(),
        "checklist": checklist_obj,
        "reviewSnapshot": review,
    }
    payload_json = json.dumps(payload_dict, ensure_ascii=False)

    if existing:
        if existing["status"] in ("done", "dismissed"):
            return
        conn.execute(
            """
            UPDATE ci_offline_packages
            SET payload_json = ?, updated_at = ?, format = COALESCE(?, format)
            WHERE id = ?
            """,
            (payload_json, now_iso, "ci_online_complete_v1", existing["id"]),
        )
        return

    dup = conn.execute("SELECT id FROM ci_offline_packages WHERE package_id = ?", (stable_pkg,)).fetchone()
    if dup:
        stable_pkg = stable_pkg + "-" + uuid.uuid4().hex[:10]
        payload_dict["packageId"] = stable_pkg
        payload_json = json.dumps(payload_dict, ensure_ascii=False)

    conn.execute(
        """
        INSERT INTO ci_offline_packages
        (package_id, application_id, ci_staff_id, client_request_id, status, format, payload_json, evidence_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'queued', ?, ?, NULL, ?, ?)
        """,
        (
            stable_pkg,
            application_id,
            ci_staff_id,
            client_request_id,
            "ci_online_complete_v1",
            payload_json,
            now_iso,
            now_iso,
        ),
    )


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_offline_migrations() -> None:
    conn = _get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ci_idempotent_complete (
                client_request_id TEXT PRIMARY KEY,
                application_id INTEGER NOT NULL,
                received_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ci_offline_packages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_id TEXT NOT NULL UNIQUE,
                application_id INTEGER NOT NULL,
                ci_staff_id INTEGER NOT NULL,
                client_request_id TEXT,
                status TEXT NOT NULL DEFAULT 'queued'
                    CHECK (status IN ('queued', 'in_progress', 'done', 'dismissed')),
                format TEXT,
                payload_json TEXT NOT NULL,
                evidence_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (application_id) REFERENCES loan_applications (id),
                FOREIGN KEY (ci_staff_id) REFERENCES users (id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ci_offline_pkg_staff "
            "ON ci_offline_packages (ci_staff_id, status, updated_at)"
        )
        conn.commit()
    finally:
        conn.close()


@offline_interview_bp.route("/api/ci/complete_interview", methods=["POST"])
@login_required
def api_ci_complete_interview():
    if current_user.role != "ci_staff":
        return jsonify({"error": "Unauthorized"}), 403

    application_id = request.form.get("application_id")
    ci_notes = request.form.get("ci_notes", "")
    checklist_data = request.form.get("checklist_data")
    client_request_id = (request.form.get("client_request_id") or "").strip()

    if not application_id or checklist_data is None:
        return jsonify({"error": "Missing application_id or checklist_data"}), 400
    if not client_request_id:
        return jsonify({"error": "Missing client_request_id"}), 400

    try:
        app_id = int(application_id)
    except ValueError:
        return jsonify({"error": "Invalid application_id"}), 400

    upload_root = _upload_folder()
    os.makedirs(upload_root, exist_ok=True)
    conn = _get_db()
    out_status = 200
    out_body = None

    try:
        app_row = conn.execute(
            "SELECT * FROM loan_applications WHERE id = ? AND assigned_ci_staff = ?",
            (app_id, current_user.id),
        ).fetchone()
        if not app_row:
            out_status = 404
            out_body = jsonify({"error": "Application not found"})
        else:
            member_name = app_row["member_name"]

            conn.execute("BEGIN EXCLUSIVE")
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO ci_idempotent_complete
                (client_request_id, application_id, received_at)
                VALUES (?, ?, ?)
                """,
                (client_request_id, app_id, datetime.now().isoformat()),
            )
            if cur.rowcount == 0:
                conn.rollback()
                try:
                    conn.execute("BEGIN")
                    upsert_offline_package_row_after_complete(
                        conn,
                        ci_staff_id=current_user.id,
                        application_id=app_id,
                        client_request_id=client_request_id,
                        ci_notes=ci_notes,
                        checklist_data=checklist_data,
                        app_row=app_row,
                    )
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                out_body = jsonify({"success": True, "duplicate": True, "message": "Already processed"})
            else:
                ci_signature_val = _resolve_ci_signature_for_completion(request.form, app_id)
                conn.execute(
                    """
                    UPDATE loan_applications
                    SET status = ?, ci_notes = ?, ci_checklist_data = ?, ci_signature = ?, ci_completed_at = ?
                    WHERE id = ?
                    """,
                    (
                        "ci_completed",
                        ci_notes,
                        checklist_data,
                        ci_signature_val,
                        datetime.now().isoformat(),
                        app_id,
                    ),
                )

                for key in request.files:
                    if not str(key).startswith("photo_"):
                        continue
                    file = request.files[key]
                    if not file or not file.filename:
                        continue
                    filename = secure_filename(file.filename)
                    unique_filename = f"{app_id}_interview_{uuid.uuid4().hex[:8]}_{filename}"
                    filepath = os.path.join(upload_root, unique_filename)
                    file.save(filepath)
                    conn.execute(
                        """
                        INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by)
                        VALUES (?, ?, ?, ?)
                        """,
                        (app_id, filename, filepath, current_user.id),
                    )

                conn.execute(
                    "UPDATE users SET current_workload = current_workload - 1 WHERE id = ?",
                    (current_user.id,),
                )

                admin = conn.execute('SELECT id FROM users WHERE role = "admin" LIMIT 1').fetchone()
                if admin:
                    conn.execute(
                        "INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)",
                        (admin["id"], f"CI interview completed for: {member_name}", f"/admin/application/{app_id}"),
                    )

                upsert_offline_package_row_after_complete(
                    conn,
                    ci_staff_id=current_user.id,
                    application_id=app_id,
                    client_request_id=client_request_id,
                    ci_notes=ci_notes,
                    checklist_data=checklist_data,
                    app_row=app_row,
                )

                conn.commit()
                out_body = jsonify({"success": True, "duplicate": False, "message": "Interview saved"})
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        out_status = 500
        out_body = jsonify({"error": str(e)})
    finally:
        conn.close()

    return out_body, out_status


@offline_interview_bp.route("/api/ci/signature_for_interview", methods=["GET"])
@login_required
def api_ci_signature_for_interview():
    """Return profile signature as a data URL so /api/ci/complete_interview multipart can store a PNG snapshot."""
    if current_user.role != "ci_staff":
        return jsonify({"error": "Unauthorized"}), 403
    sp = getattr(current_user, "signature_path", None)
    if not sp or not str(sp).strip():
        return jsonify({"signature_data_url": None})
    path = str(sp).strip()
    if not os.path.isfile(path):
        alt = os.path.join(_signature_folder(), os.path.basename(path.replace("\\", "/")))
        path = alt if os.path.isfile(alt) else path
    if not os.path.isfile(path):
        return jsonify({"signature_data_url": None})
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
        b64 = base64.b64encode(raw).decode("ascii")
        lower = path.lower()
        mime = "image/png"
        if lower.endswith((".jpg", ".jpeg", ".jpe")):
            mime = "image/jpeg"
        elif lower.endswith(".webp"):
            mime = "image/webp"
        elif lower.endswith(".gif"):
            mime = "image/gif"
        return jsonify({"signature_data_url": f"data:{mime};base64,{b64}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@offline_interview_bp.route("/api/ci/offline_package", methods=["POST"])
@login_required
def api_ci_offline_package():
    """Receive a local-only CI field package (asset app / PWA) + evidence files; idempotent on package_id."""
    if current_user.role != "ci_staff":
        return jsonify({"error": "Unauthorized"}), 403

    payload_str = request.form.get("payload")
    if not payload_str:
        return jsonify({"error": "Missing payload"}), 400
    try:
        data = json.loads(payload_str)
    except (json.JSONDecodeError, TypeError):
        return jsonify({"error": "Invalid JSON in payload"}), 400

    application_id = data.get("applicationId") or data.get("application_id")
    package_id = (data.get("packageId") or "").strip()
    if application_id is None or not package_id:
        return jsonify({"error": "Missing applicationId or packageId"}), 400
    try:
        application_id = int(application_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid applicationId"}), 400

    client_request_id = (data.get("clientRequestId") or data.get("client_request_id") or "").strip() or None
    fmt = (data.get("format") or "ci_offline_v1").strip()
    now = datetime.now().isoformat()
    upload_root = _upload_folder()
    os.makedirs(upload_root, exist_ok=True)
    conn = _get_db()
    out_status = 200
    out_body = None
    try:
        app_row = conn.execute(
            "SELECT * FROM loan_applications WHERE id = ? AND assigned_ci_staff = ?",
            (application_id, current_user.id),
        ).fetchone()
        if not app_row:
            return jsonify(
                {
                    "error": "Loan not found or not assigned to your CI account on the server. "
                    "Ask an admin to assign this application to you, then tap Sync again.",
                    "code": "not_assigned_or_missing",
                    "application_id": application_id,
                }
            ), 404

        ex = conn.execute("SELECT id FROM ci_offline_packages WHERE package_id = ?", (package_id,)).fetchone()
        if ex:
            return jsonify({"success": True, "duplicate": True, "id": ex["id"]})

        evidence_meta: list[dict] = []
        for key in request.files:
            if not str(key).startswith("evidence_"):
                continue
            file = request.files[key]
            if not file or not file.filename:
                continue
            filename = secure_filename(file.filename) or f"file_{key}"
            unique = f"off_{application_id}_{uuid.uuid4().hex[:8]}_{filename}"
            path = os.path.join(upload_root, unique)
            file.save(path)
            cur = conn.execute(
                """
                INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by)
                VALUES (?, ?, ?, ?)
                """,
                (application_id, filename, path, current_user.id),
            )
            last_id = cur.lastrowid
            evidence_meta.append(
                {
                    "document_id": int(last_id),
                    "file_name": filename,
                }
            )

        store_payload = json.dumps(data, ensure_ascii=False)
        ev_json = json.dumps(evidence_meta, ensure_ascii=False) if evidence_meta else None
        cur = conn.execute(
            """
            INSERT INTO ci_offline_packages
            (package_id, application_id, ci_staff_id, client_request_id, status, format, payload_json, evidence_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?)
            """,
            (package_id, application_id, current_user.id, client_request_id, fmt, store_payload, ev_json, now, now),
        )
        new_id = int(cur.lastrowid)
        conn.commit()
        out_body = jsonify(
            {
                "success": True,
                "id": new_id,
                "application_id": application_id,
                "evidence_count": len(evidence_meta),
            }
        )
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        out_status = 500
        out_body = jsonify({"error": str(e)})
    finally:
        conn.close()

    return out_body, out_status


@offline_interview_bp.route("/api/ci/offline_packages", methods=["GET"])
@login_required
def api_ci_offline_packages_list():
    if current_user.role != "ci_staff":
        return jsonify({"error": "Unauthorized"}), 403
    conn = _get_db()
    try:
        rows = conn.execute(
            """
            SELECT op.id, op.package_id, op.application_id, op.client_request_id, op.status, op.format,
                   op.created_at, op.updated_at, la.member_name
            FROM ci_offline_packages op
            JOIN loan_applications la ON la.id = op.application_id
            WHERE op.ci_staff_id = ?
            ORDER BY op.updated_at DESC
            LIMIT 200
            """,
            (current_user.id,),
        ).fetchall()
        out = [dict(r) for r in rows]
        return jsonify(out)
    finally:
        conn.close()


@offline_interview_bp.route("/api/ci/offline_package/<int:pkg_id>", methods=["GET"])
@login_required
def api_ci_offline_package_get(pkg_id: int):
    if current_user.role != "ci_staff":
        return jsonify({"error": "Unauthorized"}), 403
    conn = _get_db()
    try:
        row = conn.execute(
            """
            SELECT op.*, la.member_name
            FROM ci_offline_packages op
            JOIN loan_applications la ON la.id = op.application_id
            WHERE op.id = ? AND op.ci_staff_id = ?
            """,
            (pkg_id, current_user.id),
        ).fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        r = dict(row)
        try:
            r["payload"] = json.loads(r.pop("payload_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            r["payload"] = {}
        try:
            r["evidence"] = json.loads(r.pop("evidence_json") or "[]")
        except (json.JSONDecodeError, TypeError):
            r["evidence"] = []
        return jsonify(r)
    finally:
        conn.close()
