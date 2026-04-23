import time
import traceback

from app import app, get_db


ROLE_CREDENTIALS = [
    ("admin", "superadmin@dccco.test", "admin@2024"),
    ("loan", "loan@dccco.test", "loan123"),
    ("ci", "ci@dccco.test", "ci123"),
]


ROLE_PATHS = {
    "admin": [
        "/admin/dashboard",
        "/manage_users",
        "/manage_permissions",
        "/reports",
        "/system_settings",
        "/manage_sms_templates",
        "/admin/loan-types",
        "/messages",
        "/notifications",
        "/ci-tracking",
        "/api/online_users",
        "/api/unread_messages_count",
        "/api/loan-types",
    ],
    "loan": [
        "/loan/dashboard",
        "/loan/submit",
        "/messages",
        "/notifications",
        "/api/loan-types",
    ],
    "ci": [
        "/ci/dashboard",
        "/messages",
        "/notifications",
        "/notifications/count",
    ],
}


def login(client, email, password):
    start = time.perf_counter()
    resp = client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
    elapsed_ms = (time.perf_counter() - start) * 1000
    return resp, elapsed_ms


def timed_get(client, path):
    start = time.perf_counter()
    resp = client.get(path, follow_redirects=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return resp, elapsed_ms


def timed_post(client, path, data):
    start = time.perf_counter()
    resp = client.post(path, data=data, follow_redirects=True)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return resp, elapsed_ms


def find_any_ci_checklist_id():
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT id
            FROM loan_applications
            WHERE ci_checklist_data IS NOT NULL AND ci_checklist_data != ''
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


def main():
    app.config["TESTING"] = True
    failures = []
    slow = []

    with app.test_client() as client:
        for role, email, password in ROLE_CREDENTIALS:
            resp, login_ms = login(client, email, password)
            if resp.status_code >= 500 or b"Logged in successfully" not in resp.data:
                failures.append((f"{role}:login", resp.status_code, login_ms))
                print(f"FAIL {role} LOGIN status={resp.status_code} time_ms={login_ms:.1f}")
                continue

            print(f"OK   {role} LOGIN status={resp.status_code} time_ms={login_ms:.1f}")
            if login_ms > 1200:
                slow.append((f"{role}:login", login_ms))

            for path in ROLE_PATHS[role]:
                try:
                    r, elapsed_ms = timed_get(client, path)
                    label = f"{role} GET {path}"
                    if r.status_code >= 500:
                        failures.append((label, r.status_code, elapsed_ms))
                        print(f"FAIL {label} status={r.status_code} time_ms={elapsed_ms:.1f}")
                    else:
                        print(f"OK   {label} status={r.status_code} time_ms={elapsed_ms:.1f}")
                        if elapsed_ms > 1200:
                            slow.append((label, elapsed_ms))
                except Exception:
                    failures.append((f"{role} GET {path}", "EXCEPTION", 0))
                    print(f"EXC  {role} GET {path}")
                    traceback.print_exc()

            # role-specific transaction checks
            if role == "loan":
                submit_data = {
                    "member_name": "Full Smoke Member",
                    "member_contact": "09123456789",
                    "member_address": "Poblacion, Bayawan, Negros Oriental",
                    "loan_amount": "12000",
                    "loan_type": "Multipurpose w/o Collateral",
                    "lps_remarks": "full smoke submit",
                    "needs_ci": "1",
                }
                r, elapsed_ms = timed_post(client, "/loan/submit", submit_data)
                label = "loan POST /loan/submit"
                if r.status_code >= 500:
                    failures.append((label, r.status_code, elapsed_ms))
                    print(f"FAIL {label} status={r.status_code} time_ms={elapsed_ms:.1f}")
                else:
                    print(f"OK   {label} status={r.status_code} time_ms={elapsed_ms:.1f}")
                    if elapsed_ms > 1500:
                        slow.append((label, elapsed_ms))

            if role == "admin":
                checklist_id = find_any_ci_checklist_id()
                if checklist_id:
                    path = f"/view/checklist/{checklist_id}"
                    r, elapsed_ms = timed_get(client, path)
                    label = f"admin GET {path}"
                    if r.status_code >= 500:
                        failures.append((label, r.status_code, elapsed_ms))
                        print(f"FAIL {label} status={r.status_code} time_ms={elapsed_ms:.1f}")
                    else:
                        print(f"OK   {label} status={r.status_code} time_ms={elapsed_ms:.1f}")
                        if elapsed_ms > 1200:
                            slow.append((label, elapsed_ms))

            client.get("/logout", follow_redirects=True)

    print("\n=== SUMMARY ===")
    if failures:
        print("FAILURES:")
        for item in failures:
            print(item)
    else:
        print("No 5xx failures.")

    if slow:
        print("\nSLOW ENDPOINTS (>1.2s):")
        for item in sorted(slow, key=lambda x: x[1], reverse=True):
            print(item)
    else:
        print("No slow endpoints above threshold.")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
