import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

print("\n" + "="*70)
print("CHECKING CURRENT SYSTEM STATE")
print("="*70)

# Get all users
print("\nALL USERS IN DATABASE:")
users = cursor.execute('SELECT id, email, name, role, is_approved FROM users ORDER BY id').fetchall()

for user_id, email, name, role, is_approved in users:
    print(f"\n{user_id}. {name}")
    print(f"   Email: {email}")
    print(f"   Role: {role}")
    print(f"   Approved: {'Yes' if is_approved else 'No'}")

print("\n" + "="*70)
print("CHECKING WHAT YOU SHOULD SEE IN MANAGE USERS PAGE")
print("="*70)

# Active users (what shows in the table)
print("\nACTIVE USERS (is_approved = 1):")
active = cursor.execute('SELECT id, email, name, role FROM users WHERE is_approved = 1 ORDER BY id').fetchall()

if not active:
    print("  No active users found!")
else:
    for user_id, email, name, role in active:
        print(f"\n  • {name}")
        print(f"    Email: {email}")
        print(f"    Role: {role}")

print("\n" + "="*70)
print("EXPECTED 4 MAIN USERS")
print("="*70)

expected = [
    ('superadmin@dccco.test', 'Super Admin', 'admin'),
    ('admin@dccco.test', 'Loan Officer', 'loan_officer'),
    ('ci@dccco.test', 'CI Staff', 'ci_staff'),
    ('loan@dccco.test', 'Loan Staff', 'loan_staff')
]

print("\nChecking if expected users exist:")
for email, expected_name, expected_role in expected:
    user = cursor.execute('SELECT name, role, is_approved FROM users WHERE email = ?', (email,)).fetchone()
    if user:
        name, role, is_approved = user
        status = "✓" if (name == expected_name and role == expected_role and is_approved == 1) else "✗"
        print(f"\n{status} {email}")
        print(f"   Expected: {expected_name} ({expected_role})")
        print(f"   Actual: {name} ({role}) - Approved: {is_approved}")
        
        if name != expected_name or role != expected_role:
            print(f"   ⚠ MISMATCH FOUND!")
    else:
        print(f"\n✗ {email} - NOT FOUND!")

conn.close()
