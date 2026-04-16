import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

print("\n" + "="*60)
print("CHANGING CURRENT ADMIN TO SUPER ADMIN")
print("="*60)

# Change admin@dccco.test to admin role (super admin)
print("\nChanging admin@dccco.test from loan_officer to admin...")
cursor.execute('UPDATE users SET role = ? WHERE email = ?', ('admin', 'admin@dccco.test'))
conn.commit()

# Verify the change
user = cursor.execute('SELECT email, name, role FROM users WHERE email = ?', ('admin@dccco.test',)).fetchone()

print(f"\n✓ Updated successfully!")
print(f"  Email: {user[0]}")
print(f"  Name: {user[1]}")
print(f"  Role: {user[2]}")

print("\n" + "="*60)
print("DONE! Logout and login again to see admin features")
print("="*60)
print("\nYou can now login with:")
print("  Email: admin@dccco.test")
print("  Password: admin123")
print("\nYou'll now see:")
print("  • System Settings (admin-only)")
print("  • Loan Types (admin-only)")
print("  • Route Assignment (admin-only)")

conn.close()
