"""
Check PostgreSQL users and create default login accounts
"""
import os
from database import get_db
from werkzeug.security import generate_password_hash

# Use PostgreSQL
os.environ['DATABASE_URL'] = 'postgresql://dccco_app:JipCepytJQE4DlYVfgJM4yxJXsNF8GSh@dpg-d7kltthj2pic73cana4g-a.oregon-postgres.render.com/dbs_txpj'

print("🔍 Checking PostgreSQL users...")

conn = get_db()

# Check existing users
cursor = conn.execute("SELECT id, email, name, role, is_approved FROM users ORDER BY id")
users = cursor.fetchall()

print(f"\n📊 Found {len(users)} users in PostgreSQL:")
for user in users:
    print(f"  ID: {user['id']}, Email: {user['email']}, Name: {user['name']}, Role: {user['role']}, Approved: {user['is_approved']}")

# Create/update default users with known passwords
print("\n🔧 Creating/updating default users...")

default_users = [
    ('admin@dccco.test', 'admin123', 'Admin User', 'loan_officer'),
    ('superadmin@dccco.test', 'admin@2024', 'Super Admin', 'admin'),
    ('loan@dccco.test', 'loan123', 'Loan Staff', 'loan_staff'),
    ('ci@dccco.test', 'ci123', 'CI Staff', 'ci_staff'),
]

for email, password, name, role in default_users:
    # Check if user exists
    existing = conn.execute("SELECT id FROM users WHERE email = %s", (email,)).fetchone()
    
    password_hash = generate_password_hash(password)
    
    if existing:
        # Update password and ensure approved
        conn.execute("""
            UPDATE users 
            SET password_hash = %s, name = %s, role = %s, is_approved = 1 
            WHERE email = %s
        """, (password_hash, name, role, email))
        print(f"  ✓ Updated: {email} (password reset)")
    else:
        # Create new user
        conn.execute("""
            INSERT INTO users (email, password_hash, name, role, is_approved)
            VALUES (%s, %s, %s, %s, 1)
        """, (email, password_hash, name, role))
        print(f"  ✓ Created: {email}")

conn.commit()

# Show final user list
print("\n✅ Final user list:")
cursor = conn.execute("SELECT id, email, name, role, is_approved FROM users ORDER BY id")
users = cursor.fetchall()
for user in users:
    print(f"  ID: {user['id']}, Email: {user['email']}, Role: {user['role']}, Approved: {user['is_approved']}")

# Check applications
cursor = conn.execute("SELECT COUNT(*) as count FROM loan_applications")
app_count = cursor.fetchone()['count']
print(f"\n📝 Total applications: {app_count}")

conn.close()

print("\n🎉 Done! You can now login with:")
print("   Email: admin@dccco.test")
print("   Password: admin123")
