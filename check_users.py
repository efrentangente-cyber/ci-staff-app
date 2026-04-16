import sqlite3

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

users = cursor.execute('SELECT email, role FROM users WHERE email LIKE "%admin%"').fetchall()
print("\nAdmin accounts in database:")
for email, role in users:
    print(f"  {email} - {role}")

conn.close()
