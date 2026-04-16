import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Check current admin accounts
print("\nCurrent admin accounts:")
users = cursor.execute('SELECT id, email, name, role FROM users WHERE email LIKE "%admin%"').fetchall()
for user_id, email, name, role in users:
    print(f"  ID {user_id}: {email} ({name}) - Role: {role}")

# Update admin@dccco.test to loan_officer
print("\nUpdating admin@dccco.test to loan_officer role...")
cursor.execute('UPDATE users SET role = ? WHERE email = ?', ('loan_officer', 'admin@dccco.test'))
conn.commit()

print("\nUpdated accounts:")
users = cursor.execute('SELECT id, email, name, role FROM users WHERE email LIKE "%admin%"').fetchall()
for user_id, email, name, role in users:
    print(f"  ID {user_id}: {email} ({name}) - Role: {role}")

print("\n✓ Done! Please logout and login again.")
print("\nCredentials:")
print("  Super Admin: superadmin@dccco.test / admin@2024")
print("  Loan Officer: admin@dccco.test / admin123")

conn.close()
