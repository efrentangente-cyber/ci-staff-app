import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('app.db')
conn.row_factory = sqlite3.Row

user = conn.execute('SELECT * FROM users WHERE email="loan@dccco.test"').fetchone()

if user:
    print(f'User found: {user["email"]}')
    print(f'Name: {user["name"]}')
    print(f'Role: {user["role"]}')
    print(f'Approved: {user["is_approved"]}')
    
    # Test password
    password_correct = check_password_hash(user['password_hash'], 'loan123')
    print(f'Password "loan123" is correct: {password_correct}')
else:
    print('User not found')

conn.close()
