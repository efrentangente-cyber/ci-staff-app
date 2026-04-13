import sqlite3

conn = sqlite3.connect('app.db')
conn.row_factory = sqlite3.Row

users = conn.execute('SELECT id, email, name, role, is_approved FROM users WHERE role="loan_staff"').fetchall()

print('Loan Staff Accounts:')
for u in users:
    print(f'ID: {u["id"]}, Email: {u["email"]}, Name: {u["name"]}, Approved: {u["is_approved"]}')

conn.close()
