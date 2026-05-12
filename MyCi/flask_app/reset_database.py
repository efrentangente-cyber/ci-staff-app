#!/usr/bin/env python3
"""
Reset database script - deletes old database and recreates with new schema
Run this once on Render to fix the database schema issue
"""
import os
import sqlite3

DATABASE = 'app.db'

# Delete old database if it exists
if os.path.exists(DATABASE):
    print(f"Deleting old database: {DATABASE}")
    os.remove(DATABASE)
    print("Old database deleted!")

# Create new database with correct schema
print("Creating new database with correct schema...")
conn = sqlite3.connect(DATABASE)

with open('schema.sql', 'r') as f:
    conn.executescript(f.read())

# Create demo users (all approved)
from werkzeug.security import generate_password_hash

admin_hash = generate_password_hash('admin123')
loan_hash = generate_password_hash('loan123')
ci_hash = generate_password_hash('ci123')

conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
             ('admin@dccco.test', admin_hash, 'Admin User', 'admin', 1))
conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
             ('loan@dccco.test', loan_hash, 'Loan Staff', 'loan_staff', 1))
conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
             ('ci@dccco.test', ci_hash, 'CI Staff', 'ci_staff', 1))

conn.commit()
conn.close()

print("✅ Database reset complete!")
print("\nDemo users created:")
print("  Admin: admin@dccco.test / admin123")
print("  Loan Staff: loan@dccco.test / loan123")
print("  CI Staff: ci@dccco.test / ci123")
