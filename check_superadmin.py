import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

user = cursor.execute('SELECT email, role, is_approved FROM users WHERE email = ?', ('superadmin@dccco.test',)).fetchone()

if user:
    email, role, is_approved = user
    print(f"\nSuper Admin Account:")
    print(f"  Email: {email}")
    print(f"  Role: {role}")
    print(f"  Is Approved: {is_approved}")
    
    if is_approved == 0:
        print("\n❌ Account is NOT approved!")
        print("Approving account...")
        cursor.execute('UPDATE users SET is_approved = 1 WHERE email = ?', ('superadmin@dccco.test',))
        conn.commit()
        print("✓ Account approved!")
    else:
        print("\n✓ Account is approved and ready to use")
else:
    print("User not found!")

conn.close()
