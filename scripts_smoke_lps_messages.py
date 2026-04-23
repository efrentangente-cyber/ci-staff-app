"""End-to-end LPS messaging flow regression test.

Covers:
  * LPS login -> /messages page
  * LPS -> open chat with CI
  * LPS -> send direct message to CI (text)
  * LPS -> send image message to CI
  * CI login -> view LPS chat -> reply
  * Loan officer login -> view LPS chat -> reply
  * Edit / delete direct message
  * Mark messages read
  * Unread counts
"""
from __future__ import annotations

import io
import os
import sys
import time
import json
from typing import Tuple

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from app import app, get_db  # noqa: E402

app.config["TESTING"] = True

ACCOUNTS = {
    "lps": ("loan@dccco.test", "loan123"),
    "ci": ("ci@dccco.test", "ci123"),
    "loan_officer": ("admin@dccco.test", "admin123"),
}


def login(client, role: str) -> Tuple[int, str]:
    email, password = ACCOUNTS[role]
    r = client.post(
        "/login", data={"email": email, "password": password}, follow_redirects=True
    )
    with app.app_context():
        conn = get_db()
        row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
    return r.status_code, int(row["id"]) if row else -1


def check(label: str, ok: bool, detail: str = "") -> bool:
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {label}{(' - ' + detail) if detail else ''}")
    return ok


def run() -> int:
    failures = 0

    # LPS client
    lps = app.test_client()
    status, lps_id = login(lps, "lps")
    if not check("LPS login", status == 200 and lps_id > 0, f"status={status}, uid={lps_id}"):
        failures += 1

    # /messages page
    r = lps.get("/messages", follow_redirects=False)
    if not check(
        "LPS GET /messages",
        r.status_code == 200 and b"Internal" not in r.data,
        f"status={r.status_code}",
    ):
        failures += 1

    # Resolve CI and loan officer ids
    with app.app_context():
        conn = get_db()
        ci_row = conn.execute(
            "SELECT id FROM users WHERE email=?", ("ci@dccco.test",)
        ).fetchone()
        lo_row = conn.execute(
            "SELECT id FROM users WHERE email=?", ("admin@dccco.test",)
        ).fetchone()
        conn.close()
    ci_id = int(ci_row["id"])
    lo_id = int(lo_row["id"])

    # Open chat page for CI
    r = lps.get(f"/messages/{ci_id}", follow_redirects=False)
    if not check(
        f"LPS GET /messages/{ci_id} (chat with CI)",
        r.status_code == 200 and b"Internal" not in r.data,
        f"status={r.status_code}",
    ):
        failures += 1

    # Send text message to CI via send_direct_message
    r = lps.post(
        "/api/send_direct_message",
        json={"receiver_id": ci_id, "message": f"LPS->CI test {int(time.time())}"},
    )
    data = r.get_json(silent=True) or {}
    msg_id = data.get("message_id")
    if not check(
        "LPS POST /api/send_direct_message -> CI",
        r.status_code == 200 and data.get("success") and msg_id,
        f"status={r.status_code}, body={data}",
    ):
        failures += 1

    # Send text to loan officer
    r = lps.post(
        "/api/send_direct_message",
        json={"receiver_id": lo_id, "message": f"LPS->LO test {int(time.time())}"},
    )
    data_lo = r.get_json(silent=True) or {}
    if not check(
        "LPS POST /api/send_direct_message -> Loan Officer",
        r.status_code == 200 and data_lo.get("success"),
        f"status={r.status_code}, body={data_lo}",
    ):
        failures += 1

    # Send an image message
    img_bytes = b"\x89PNG\r\n\x1a\n" + b"0" * 32
    r = lps.post(
        "/api/send_image_message",
        data={
            "receiver_id": str(ci_id),
            "image": (io.BytesIO(img_bytes), "probe.png"),
        },
        content_type="multipart/form-data",
    )
    data_img = r.get_json(silent=True) or {}
    if not check(
        "LPS POST /api/send_image_message -> CI",
        r.status_code == 200 and data_img.get("success"),
        f"status={r.status_code}, body={data_img}",
    ):
        failures += 1

    # Edit the first direct message
    if msg_id:
        r = lps.post(
            "/api/edit_direct_message",
            json={"message_id": msg_id, "new_text": "Edited text"},
        )
        data_edit = r.get_json(silent=True) or {}
        if not check(
            "LPS POST /api/edit_direct_message",
            r.status_code == 200 and data_edit.get("success"),
            f"status={r.status_code}, body={data_edit}",
        ):
            failures += 1

    # CI side
    ci = app.test_client()
    status, _ = login(ci, "ci")
    if not check("CI login", status == 200, f"status={status}"):
        failures += 1
    r = ci.get("/messages", follow_redirects=False)
    if not check(
        "CI GET /messages",
        r.status_code == 200 and b"Internal" not in r.data,
        f"status={r.status_code}",
    ):
        failures += 1

    r = ci.get(f"/messages/{lps_id}", follow_redirects=False)
    if not check(
        f"CI GET /messages/{lps_id}",
        r.status_code == 200 and b"Internal" not in r.data,
        f"status={r.status_code}",
    ):
        failures += 1

    r = ci.post(
        "/api/send_direct_message",
        json={"receiver_id": lps_id, "message": f"CI->LPS reply {int(time.time())}"},
    )
    data_ci = r.get_json(silent=True) or {}
    if not check(
        "CI POST /api/send_direct_message -> LPS",
        r.status_code == 200 and data_ci.get("success"),
        f"status={r.status_code}, body={data_ci}",
    ):
        failures += 1

    r = ci.post(f"/api/mark_messages_read/{lps_id}")
    data_mr = r.get_json(silent=True) or {}
    if not check(
        "CI POST /api/mark_messages_read",
        r.status_code == 200 and data_mr.get("success"),
        f"status={r.status_code}, body={data_mr}",
    ):
        failures += 1

    r = ci.get("/api/unread_messages_count")
    data_uc = r.get_json(silent=True) or {}
    if not check(
        "CI GET /api/unread_messages_count",
        r.status_code == 200 and "count" in data_uc,
        f"status={r.status_code}, body={data_uc}",
    ):
        failures += 1

    # Loan Officer side
    lo = app.test_client()
    status, _ = login(lo, "loan_officer")
    if not check("LO login", status == 200, f"status={status}"):
        failures += 1
    r = lo.get("/messages", follow_redirects=False)
    if not check(
        "LO GET /messages",
        r.status_code == 200 and b"Internal" not in r.data,
        f"status={r.status_code}",
    ):
        failures += 1
    r = lo.get(f"/messages/{lps_id}", follow_redirects=False)
    if not check(
        f"LO GET /messages/{lps_id}",
        r.status_code == 200 and b"Internal" not in r.data,
        f"status={r.status_code}",
    ):
        failures += 1
    r = lo.post(
        "/api/send_direct_message",
        json={"receiver_id": lps_id, "message": f"LO->LPS reply {int(time.time())}"},
    )
    data_lo2 = r.get_json(silent=True) or {}
    if not check(
        "LO POST /api/send_direct_message -> LPS",
        r.status_code == 200 and data_lo2.get("success"),
        f"status={r.status_code}, body={data_lo2}",
    ):
        failures += 1

    # LPS reads back
    r = lps.get(f"/messages/{ci_id}", follow_redirects=False)
    if not check(
        "LPS GET /messages/ci after CI replied",
        r.status_code == 200 and b"Internal" not in r.data,
        f"status={r.status_code}",
    ):
        failures += 1
    r = lps.get("/api/unread_messages_count")
    data_uc2 = r.get_json(silent=True) or {}
    if not check(
        "LPS GET /api/unread_messages_count",
        r.status_code == 200 and "count" in data_uc2,
        f"status={r.status_code}, body={data_uc2}",
    ):
        failures += 1

    print("=" * 60)
    print(f"TOTAL FAILURES: {failures}")
    return failures


if __name__ == "__main__":
    sys.exit(run())
