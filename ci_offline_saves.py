"""
Server-side store for CI offline field packages (synced from PWA / asset WebView).
Each row = one local save: JSON payload (e.g. version, review, checklist, notes, evidence)
+ optional loan_application_id for Continue into the online checklist flow.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from database import get_db, get_database_type


def ensure_ci_offline_packages_table() -> None:
    """Idempotent: ci_offline_packages (SQLite + PostgreSQL)."""
    try:
        conn = get_db()
        db_type = get_database_type()
        if db_type == "sqlite":
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ci_offline_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ci_user_id INTEGER NOT NULL,
                    loan_application_id INTEGER,
                    client_package_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    member_name TEXT,
                    source_label TEXT,
                    package_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE (client_package_id)
                )
                """
            )
        else:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ci_offline_packages (
                    id SERIAL PRIMARY KEY,
                    ci_user_id INTEGER NOT NULL,
                    loan_application_id INTEGER,
                    client_package_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL DEFAULT 'pending',
                    member_name TEXT,
                    source_label TEXT,
                    package_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ci_offline_user_created
            ON ci_offline_packages(ci_user_id, created_at DESC)
            """
        )
        conn.commit()
        conn.close()
        print("✓ ci_offline_packages table ensured")
    except Exception as e:
        print(f"⚠️  ci_offline_packages migration warning: {e}")


def _ts_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _parse_package_json_row(row) -> dict:
    d = dict(row)
    try:
        d["package"] = json.loads(d.get("package_json") or "{}")
    except Exception:
        d["package"] = {}
    d.pop("package_json", None)
    return d


def _unread_count(user_id) -> int:
    try:
        c = get_db()
        try:
            r = c.execute(
                "SELECT COUNT(*) as count FROM notifications "
                "WHERE user_id = ? AND is_read = 0 AND message NOT LIKE 'New message from%'",
                (user_id,),
            ).fetchone()
        except Exception:
            r = c.execute(
                "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0",
                (user_id,),
            ).fetchone()
        c.close()
        return int(r["count"]) if r and r.get("count") is not None else 0
    except Exception:
        return 0


def get_offline_package_for_wizard(
    package_row_id: int, ci_user_id: int, loan_application_id: int
) -> dict | None:
    """
    Return parsed package body for merging into the checklist wizard.
    Enforces: row belongs to CI user and loan_application_id matches.
    """
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT * FROM ci_offline_packages
            WHERE id = ? AND ci_user_id = ? AND loan_application_id = ?
            """,
            (package_row_id, ci_user_id, loan_application_id),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    try:
        return json.loads(row["package_json"] or "{}")
    except Exception:
        return {}


def init_ci_offline_saves(app, csrf) -> None:
    @app.route("/ci/offline_saves", methods=["GET"])
    @login_required
    def ci_offline_saves_list():
        if current_user.role != "ci_staff":
            flash("Unauthorized", "danger")
            return redirect(url_for("index"))
        conn = get_db()
        try:
            rows = conn.execute(
                """
                SELECT id, client_package_id, loan_application_id, status, member_name,
                       source_label, created_at, updated_at
                FROM ci_offline_packages
                WHERE ci_user_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (current_user.id,),
            ).fetchall()
        finally:
            conn.close()
        return render_template(
            "ci_offline_saves.html",
            rows=rows,
            unread_count=_unread_count(current_user.id),
        )

    @app.route("/ci/offline_saves/continue/<int:pkg_id>", methods=["GET"])
    @login_required
    def ci_offline_saves_continue(pkg_id: int):
        if current_user.role != "ci_staff":
            flash("Unauthorized", "danger")
            return redirect(url_for("index"))
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM ci_offline_packages WHERE id = ? AND ci_user_id = ?",
                (pkg_id, current_user.id),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            flash("Offline save not found.", "warning")
            return redirect(url_for("ci_offline_saves_list"))
        la_id = row["loan_application_id"]
        if not la_id:
            flash(
                "This save has no loan application id yet. Re-sync from the device after it is linked.",
                "warning",
            )
            return redirect(url_for("ci_offline_saves_list"))
        conn = get_db()
        try:
            a = conn.execute(
                "SELECT id FROM loan_applications WHERE id = ? AND assigned_ci_staff = ?",
                (la_id, current_user.id),
            ).fetchone()
        finally:
            conn.close()
        if not a:
            flash("That application is not assigned to you.", "warning")
            return redirect(url_for("ci_offline_saves_list"))
        t = _ts_now()
        conn = get_db()
        try:
            conn.execute(
                "UPDATE ci_offline_packages SET status = ?, updated_at = ? WHERE id = ?",
                ("continued", t, pkg_id),
            )
            conn.commit()
        except Exception as e:
            current_app.logger.debug("ci_offline_saves status update: %s", e)
        finally:
            conn.close()
        flash(
            "Loaded offline package into the checklist. Review and submit when done.",
            "info",
        )
        return redirect(
            url_for("ci_checklist_wizard", id=la_id) + f"?import_offline_package={pkg_id}"
        )

    @app.route("/ci/offline_saves/dismiss/<int:pkg_id>", methods=["POST"])
    @login_required
    def ci_offline_saves_dismiss(pkg_id: int):
        if current_user.role != "ci_staff":
            flash("Unauthorized", "danger")
            return redirect(url_for("index"))
        conn = get_db()
        try:
            r = conn.execute(
                "SELECT id FROM ci_offline_packages WHERE id = ? AND ci_user_id = ?",
                (pkg_id, current_user.id),
            ).fetchone()
            if not r:
                flash("Save not found.", "warning")
                return redirect(url_for("ci_offline_saves_list"))
            t = _ts_now()
            conn.execute(
                "UPDATE ci_offline_packages SET status = ?, updated_at = ? WHERE id = ?",
                ("dismissed", t, pkg_id),
            )
            conn.commit()
        except Exception as e:
            flash("Could not dismiss.", "danger")
            current_app.logger.debug("ci_offline_saves_dismiss: %s", e)
        finally:
            conn.close()
        return redirect(url_for("ci_offline_saves_list"))

    @app.route("/api/ci/offline_packages", methods=["GET"])
    @login_required
    def api_ci_offline_packages_list():
        if current_user.role != "ci_staff":
            return jsonify({"ok": False, "error": "Unauthorized"}), 403
        conn = get_db()
        try:
            rows = conn.execute(
                """
                SELECT id, client_package_id, loan_application_id, status, member_name,
                       source_label, created_at, updated_at, package_json
                FROM ci_offline_packages
                WHERE ci_user_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (current_user.id,),
            ).fetchall()
        finally:
            conn.close()
        out = []
        for r in rows:
            o = {
                "id": r["id"],
                "client_package_id": r["client_package_id"],
                "loan_application_id": r["loan_application_id"],
                "status": r["status"],
                "member_name": r["member_name"],
                "source_label": r["source_label"],
                "created_at": str(r["created_at"]) if r["created_at"] is not None else None,
                "updated_at": str(r["updated_at"]) if r["updated_at"] is not None else None,
            }
            if request.args.get("include_package") == "1":
                try:
                    o["package"] = json.loads(r["package_json"] or "{}")
                except Exception:
                    o["package"] = {}
            out.append(o)
        return jsonify({"ok": True, "items": out})

    @app.route("/api/ci/offline_package/<int:pkg_id>", methods=["GET"])
    @login_required
    def api_ci_offline_package_get(pkg_id: int):
        if current_user.role != "ci_staff":
            return jsonify({"ok": False, "error": "Unauthorized"}), 403
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM ci_offline_packages WHERE id = ? AND ci_user_id = ?",
                (pkg_id, current_user.id),
            ).fetchone()
        finally:
            conn.close()
        if not row:
            return jsonify({"ok": False, "error": "Not found"}), 404
        return jsonify({"ok": True, "item": _parse_package_json_row(row)})

    @app.route("/api/ci/offline_package", methods=["POST"])
    @csrf.exempt
    @login_required
    def api_ci_offline_package_upsert():
        """
        Sync from PWA. JSON body:
        { "client_package_id", "loan_application_id"?, "member_name"?, "source_label"?, "package": { ... } }
        """
        if current_user.role != "ci_staff":
            return jsonify({"ok": False, "error": "Unauthorized"}), 403
        data = request.get_json(silent=True) or {}
        client_package_id = (data.get("client_package_id") or "").strip()
        if not client_package_id:
            return jsonify({"ok": False, "error": "Missing client_package_id"}), 400
        package = data.get("package")
        if package is None:
            return jsonify({"ok": False, "error": "Missing package"}), 400
        member_name = (data.get("member_name") or "").strip() or None
        source_label = (data.get("source_label") or "").strip() or None
        loan_application_id = data.get("loan_application_id")
        la_id = None
        if loan_application_id is not None and str(loan_application_id).strip() != "":
            try:
                la_id = int(loan_application_id)
            except (TypeError, ValueError):
                return jsonify({"ok": False, "error": "Invalid loan_application_id"}), 400
            c2 = get_db()
            try:
                a = c2.execute(
                    "SELECT id FROM loan_applications WHERE id = ? AND assigned_ci_staff = ?",
                    (la_id, current_user.id),
                ).fetchone()
            finally:
                c2.close()
            if not a:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "error": "Application not found or not assigned to you",
                        }
                    ),
                    404,
                )
        try:
            package_json = json.dumps(package, default=str, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            return jsonify({"ok": False, "error": f"Invalid package: {e}"}), 400
        t = _ts_now()
        new_id: int | None = None
        conn = get_db()
        try:
            ex = conn.execute(
                "SELECT id, ci_user_id FROM ci_offline_packages WHERE client_package_id = ?",
                (client_package_id,),
            ).fetchone()
            if ex is not None:
                if ex["ci_user_id"] != current_user.id:
                    return (
                        jsonify(
                            {
                                "ok": False,
                                "error": "client_package_id already used by another account",
                            }
                        ),
                        409,
                    )
                conn.execute(
                    """
                    UPDATE ci_offline_packages
                    SET loan_application_id = ?, member_name = ?, source_label = ?,
                        package_json = ?, status = 'pending', updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        la_id,
                        member_name,
                        source_label,
                        package_json,
                        t,
                        ex["id"],
                    ),
                )
                new_id = ex["id"]
            else:
                conn.execute(
                    """
                    INSERT INTO ci_offline_packages
                    (ci_user_id, loan_application_id, client_package_id, status, member_name,
                     source_label, package_json, created_at, updated_at)
                    VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                    """,
                    (
                        current_user.id,
                        la_id,
                        client_package_id,
                        member_name,
                        source_label,
                        package_json,
                        t,
                        t,
                    ),
                )
                r2 = conn.execute(
                    "SELECT id FROM ci_offline_packages WHERE client_package_id = ?",
                    (client_package_id,),
                ).fetchone()
                new_id = r2["id"] if r2 else None
            conn.commit()
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            current_app.logger.exception("api_ci_offline_package_upsert: %s", e)
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            conn.close()
        return jsonify(
            {
                "ok": True,
                "id": new_id,
                "client_package_id": client_package_id,
            }
        )

    @app.route("/api/ci/offline_package/<int:pkg_id>/dismiss", methods=["POST"])
    @csrf.exempt
    @login_required
    def api_ci_offline_package_dismiss_api(pkg_id: int):
        if current_user.role != "ci_staff":
            return jsonify({"ok": False, "error": "Unauthorized"}), 403
        conn = get_db()
        try:
            r = conn.execute(
                "SELECT id FROM ci_offline_packages WHERE id = ? AND ci_user_id = ?",
                (pkg_id, current_user.id),
            ).fetchone()
            if not r:
                return jsonify({"ok": False, "error": "Not found"}), 404
            t = _ts_now()
            conn.execute(
                "UPDATE ci_offline_packages SET status = ?, updated_at = ? WHERE id = ?",
                ("dismissed", t, pkg_id),
            )
            conn.commit()
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
        finally:
            conn.close()
        return jsonify({"ok": True})
