import traceback

from app import app


ADMIN_CREDENTIALS = [
    ("superadmin@dccco.test", "admin@2024"),
    ("admin@dccco.test", "admin123"),
]

ADMIN_PATHS = [
    "/admin/dashboard",
    "/manage_users",
    "/manage_permissions",
    "/reports",
    "/system_settings",
    "/admin/loan-types",
    "/manage_sms_templates",
    "/notifications",
    "/messages",
    "/ci-tracking",
    "/notifications/count",
    "/api/online_users",
    "/api/unread_messages_count",
    "/api/loan-types",
]


def try_login(client):
    for email, password in ADMIN_CREDENTIALS:
        resp = client.post(
            "/login",
            data={"email": email, "password": password},
            follow_redirects=True,
        )
        if resp.status_code == 200 and b"Logged in successfully" in resp.data:
            return email
    return None


def main():
    app.config["TESTING"] = True
    failures = []

    with app.test_client() as client:
        logged_in_email = try_login(client)
        if not logged_in_email:
            print("LOGIN_FAILED: could not login using default admin credentials")
            return 2

        print(f"LOGIN_OK: {logged_in_email}")

        for path in ADMIN_PATHS:
            try:
                resp = client.get(path, follow_redirects=True)
                code = resp.status_code
                if code >= 500:
                    failures.append((path, code))
                    print(f"FAIL {code} {path}")
                else:
                    print(f"OK   {code} {path}")
            except Exception:
                failures.append((path, "EXCEPTION"))
                print(f"EXCEPTION {path}")
                traceback.print_exc()

    if failures:
        print("\nSUMMARY: FAILURES")
        for item in failures:
            print(item)
        return 1

    print("\nSUMMARY: all admin smoke paths passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

