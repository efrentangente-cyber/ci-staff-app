"""
Idempotent CI interview completion for offline WebView / PWA sync.
Registers POST /api/ci/complete_interview (same contract as MyCi flask_app).
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

from flask import jsonify, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from database import get_db


def _upload_root():
    rel = current_app.config.get("UPLOAD_FOLDER", "uploads")
    if os.path.isabs(rel):
        return rel
    return os.path.join(os.getcwd(), rel)


def ensure_ci_idempotent_migrations():
    """Create idempotency table (SQLite + PostgreSQL)."""
    conn = get_db()
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
        conn.commit()
    finally:
        conn.close()


def init_offline_interview_api(app, csrf):
    """Call once after app + csrf exist."""

    ensure_ci_idempotent_migrations()

    @app.route("/api/ci/complete_interview", methods=["POST"])
    @csrf.exempt
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

        upload_root = _upload_root()
        os.makedirs(upload_root, exist_ok=True)
        conn = get_db()
        out_status = 200
        out_body = None

        try:
            app_row = conn.execute(
                "SELECT * FROM loan_applications WHERE id=? AND assigned_ci_staff=?",
                (app_id, current_user.id),
            ).fetchone()
            if not app_row:
                out_status = 404
                out_body = jsonify({"error": "Application not found"})
            else:
                try:
                    member_name = app_row["member_name"]
                except Exception:
                    member_name = ""

                cur = conn.execute(
                    "SELECT 1 AS x FROM ci_idempotent_complete WHERE client_request_id=?",
                    (client_request_id,),
                )
                exists = cur.fetchone() if cur else None
                if exists:
                    out_body = jsonify(
                        {
                            "success": True,
                            "duplicate": True,
                            "message": "Already processed",
                        }
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO ci_idempotent_complete (client_request_id, application_id, received_at)
                        VALUES (?, ?, ?)
                        """,
                        (client_request_id, app_id, datetime.now().isoformat()),
                    )
                    conn.execute(
                        """
                        UPDATE loan_applications
                        SET status=?, ci_notes=?, ci_checklist_data=?, ci_signature=?, ci_completed_at=?
                        WHERE id=?
                        """,
                        (
                            "ci_completed",
                            ci_notes,
                            checklist_data,
                            current_user.name,
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

                    try:
                        conn.execute(
                            "UPDATE users SET current_workload = current_workload - 1 WHERE id=?",
                            (current_user.id,),
                        )
                    except Exception:
                        pass

                    admin = conn.execute(
                        "SELECT id FROM users WHERE role = ? LIMIT 1", ("admin",)
                    ).fetchone()
                    if admin is not None:
                        try:
                            aid = admin["id"]
                        except Exception:
                            aid = admin[0]
                        if aid is not None:
                            conn.execute(
                                "INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)",
                                (
                                    aid,
                                    f"CI interview completed for: {member_name}",
                                    f"/admin/application/{app_id}",
                                ),
                            )

                    conn.commit()
                    out_body = jsonify(
                        {
                            "success": True,
                            "duplicate": False,
                            "message": "Interview saved",
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
