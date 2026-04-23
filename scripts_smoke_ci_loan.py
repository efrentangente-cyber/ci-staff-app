from app import app


def login(client, email, password):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def main():
    app.config["TESTING"] = True

    with app.test_client() as client:
        # CI account smoke
        ci = login(client, "ci@dccco.test", "ci123")
        print("CI_LOGIN", ci.status_code)
        for path in ["/", "/ci/dashboard", "/messages", "/notifications/count"]:
            r = client.get(path, follow_redirects=True)
            print("CI_PATH", path, r.status_code)

        # logout
        client.get("/logout", follow_redirects=True)

        # LPS account smoke
        lps = login(client, "loan@dccco.test", "loan123")
        print("LPS_LOGIN", lps.status_code)
        for path in ["/", "/loan/dashboard", "/loan/submit", "/api/loan-types"]:
            r = client.get(path, follow_redirects=True)
            print("LPS_PATH", path, r.status_code)

        # simulate submit loan application
        submit_resp = client.post(
            "/loan/submit",
            data={
                "member_name": "Smoke Test Member",
                "member_contact": "09123456789",
                "member_address": "Poblacion, Bayawan, Negros Oriental",
                "loan_amount": "15000",
                "loan_type": "Multipurpose w/o Collateral",
                "lps_remarks": "smoke",
                "needs_ci": "1",
            },
            follow_redirects=True,
        )
        print("LPS_SUBMIT", submit_resp.status_code)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

