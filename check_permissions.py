#!/usr/bin/env python3
"""Check permissions setup"""

import sqlite3

conn = sqlite3.connect('app.db')
conn.row_factory = sqlite3.Row

print("=" * 80)
print("CURRENT USERS WITH PERMISSIONS")
print("=" * 80)

users = conn.execute('''
    SELECT id, name, email, role, permissions 
    FROM users 
    WHERE role IN ('admin', 'loan_officer')
    ORDER BY role, name
''').fetchall()

for user in users:
    perms = user['permissions'] or 'None'
    print(f"{user['name']:25} | {user['email']:30} | {user['role']:15} | {perms}")

conn.close()

print("=" * 80)
print("✅ PERMISSIONS CHECK COMPLETE")
print("=" * 80)
