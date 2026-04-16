import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

print("\n" + "="*60)
print("CHANGING ADMIN USER TO LOAN OFFICER")
print("="*60)

# Get current admin user
admin = cursor.execute('SELECT id, email, name, role FROM users WHERE email = ?', ('admin@dccco.test',)).fetchone()

print(f"\nCurrent user:")
print(f"  Email: {admin[1]}")
print(f"  Name: {admin[2]}")
print(f"  Role: {admin[3]}")

# Change to loan_officer
print(f"\nChanging role from '{admin[3]}' to 'loan_officer'...")
cursor.execute('UPDATE users SET role = ? WHERE email = ?', ('loan_officer', 'admin@dccco.test'))
conn.commit()

# Verify
updated = cursor.execute('SELECT id, email, name, role FROM users WHERE email = ?', ('admin@dccco.test',)).fetchone()

print(f"\n✓ Updated successfully!")
print(f"  Email: {updated[1]}")
print(f"  Name: {updated[2]}")
print(f"  Role: {updated[3]}")

print("\n" + "="*60)
print("DONE!")
print("="*60)
print("\nLoan Officer credentials:")
print("  Email: admin@dccco.test")
print("  Password: admin123")
print("  Role: loan_officer")
print("\nThis account can now:")
print("  • Approve/reject loans")
print("  • Manage users")
print("  • Generate reports")
print("  • View CI tracking")
print("\nBut CANNOT:")
print("  • Access System Settings (admin only)")
print("  • Manage Loan Types (admin only)")
print("  • Assign routes (admin only)")

conn.close()
