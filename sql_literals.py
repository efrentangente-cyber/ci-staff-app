"""SQL strings shared across app entrypoints (avoids copy-paste drift between app.py copies)."""


# CI checklist wizard GET: only columns needed for auth + prefill + saved draft JSON.
SQL_CI_CHECKLIST_WIZARD_BY_ID = """
        SELECT la.id, la.assigned_ci_staff, la.member_name, la.member_address, la.member_contact,
               la.loan_amount, la.loan_type, la.ci_checklist_data
        FROM loan_applications la
        WHERE la.id=?
        """

# Notifications page: template uses id, message, link, is_read, created_at only.
SQL_NOTIFICATIONS_INBOX = """
            SELECT id, message, link, is_read, created_at
            FROM notifications
            WHERE user_id=?
            ORDER BY created_at DESC
            LIMIT 50
        """
