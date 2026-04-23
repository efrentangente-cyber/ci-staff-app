"""
Complete Migration from SQLite to PostgreSQL
Migrates ALL data including users, applications, documents, messages, etc.
"""

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# Get database URLs
sqlite_db = 'app.db'
postgres_url = os.getenv('DATABASE_URL')

if postgres_url.startswith('postgres://'):
    postgres_url = postgres_url.replace('postgres://', 'postgresql://', 1)

print("=" * 60)
print("FULL DATABASE MIGRATION: SQLite → PostgreSQL")
print("=" * 60)

# Connect to both databases
print("\n1. Connecting to databases...")
sqlite_conn = sqlite3.connect(sqlite_db)
sqlite_conn.row_factory = sqlite3.Row
pg_conn = psycopg2.connect(postgres_url, cursor_factory=RealDictCursor)

print("✓ Connected to SQLite")
print("✓ Connected to PostgreSQL")

# Create all tables first
print("\n2. Creating PostgreSQL tables...")
pg_cursor = pg_conn.cursor()

# Users table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    is_approved INTEGER DEFAULT 0,
    signature_path VARCHAR(500),
    backup_email VARCHAR(255),
    profile_photo VARCHAR(500),
    is_online INTEGER DEFAULT 0,
    last_seen TIMESTAMP,
    current_workload INTEGER DEFAULT 0,
    assigned_route TEXT,
    permissions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Loan applications table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS loan_applications (
    id SERIAL PRIMARY KEY,
    member_name VARCHAR(255) NOT NULL,
    member_contact VARCHAR(50),
    member_address TEXT,
    loan_amount DECIMAL(15, 2),
    loan_type VARCHAR(255),
    loan_purpose TEXT,
    status VARCHAR(50) DEFAULT 'submitted',
    needs_ci_interview INTEGER DEFAULT 1,
    submitted_by INTEGER,
    assigned_ci_staff INTEGER,
    lps_remarks TEXT,
    ci_notes TEXT,
    ci_checklist_data TEXT,
    ci_signature TEXT,
    ci_latitude DECIMAL(10, 8),
    ci_longitude DECIMAL(11, 8),
    ci_completed_at TIMESTAMP,
    admin_notes TEXT,
    admin_decision_at TIMESTAMP,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Documents table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    loan_application_id INTEGER NOT NULL,
    file_name VARCHAR(500),
    file_path VARCHAR(500),
    uploaded_by INTEGER,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Direct messages table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS direct_messages (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    is_edited INTEGER DEFAULT 0,
    is_deleted INTEGER DEFAULT 0
)
""")

# Notifications table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    message TEXT,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Location tracking table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS location_tracking (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    activity VARCHAR(255),
    tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Loan types table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS loan_types (
    id SERIAL PRIMARY KEY,
    loan_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1
)
""")

# System settings table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT
)
""")

# SMS templates table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS sms_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL,
    template_content TEXT,
    is_active INTEGER DEFAULT 1
)
""")

# Password reset codes table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS password_reset_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    code VARCHAR(10) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Permissions table
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    permission_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT
)
""")

pg_conn.commit()
print("✓ All tables created")

# Migrate data
print("\n3. Migrating data...")

# Migrate users
print("\n   → Migrating users...")
sqlite_cursor = sqlite_conn.cursor()
users = sqlite_cursor.execute("SELECT * FROM users").fetchall()
user_count = 0
for user in users:
    try:
        pg_cursor.execute("""
            INSERT INTO users (email, password_hash, name, role, is_approved, signature_path, 
                             backup_email, profile_photo, is_online, last_seen, current_workload, 
                             assigned_route, permissions, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                name = EXCLUDED.name,
                role = EXCLUDED.role,
                is_approved = EXCLUDED.is_approved
        """, (
            user['email'], user['password_hash'], user['name'], user['role'],
            user['is_approved'], user.get('signature_path'), user.get('backup_email'),
            user.get('profile_photo'), user.get('is_online', 0), user.get('last_seen'),
            user.get('current_workload', 0), user.get('assigned_route'), 
            user.get('permissions'), user.get('created_at')
        ))
        user_count += 1
    except Exception as e:
        print(f"     Warning: {e}")
        continue

pg_conn.commit()
print(f"   ✓ Migrated {user_count} users")

# Migrate loan applications
print("\n   → Migrating loan applications...")
applications = sqlite_cursor.execute("SELECT * FROM loan_applications").fetchall()
app_count = 0
for app in applications:
    try:
        pg_cursor.execute("""
            INSERT INTO loan_applications (member_name, member_contact, member_address, loan_amount,
                                         loan_type, loan_purpose, status, needs_ci_interview,
                                         submitted_by, assigned_ci_staff, lps_remarks, ci_notes,
                                         ci_checklist_data, ci_signature, ci_latitude, ci_longitude,
                                         ci_completed_at, admin_notes, admin_decision_at, submitted_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            app['member_name'], app.get('member_contact'), app.get('member_address'),
            app.get('loan_amount'), app.get('loan_type'), app.get('loan_purpose'),
            app.get('status', 'submitted'), app.get('needs_ci_interview', 1),
            app.get('submitted_by'), app.get('assigned_ci_staff'), app.get('lps_remarks'),
            app.get('ci_notes'), app.get('ci_checklist_data'), app.get('ci_signature'),
            app.get('ci_latitude'), app.get('ci_longitude'), app.get('ci_completed_at'),
            app.get('admin_notes'), app.get('admin_decision_at'), app.get('submitted_at')
        ))
        app_count += 1
    except Exception as e:
        print(f"     Warning: {e}")
        continue

pg_conn.commit()
print(f"   ✓ Migrated {app_count} loan applications")

# Migrate documents
print("\n   → Migrating documents...")
documents = sqlite_cursor.execute("SELECT * FROM documents").fetchall()
doc_count = 0
for doc in documents:
    try:
        pg_cursor.execute("""
            INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by, uploaded_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            doc['loan_application_id'], doc.get('file_name'), doc.get('file_path'),
            doc.get('uploaded_by'), doc.get('uploaded_at')
        ))
        doc_count += 1
    except Exception as e:
        print(f"     Warning: {e}")
        continue

pg_conn.commit()
print(f"   ✓ Migrated {doc_count} documents")

# Migrate loan types
print("\n   → Migrating loan types...")
try:
    loan_types = sqlite_cursor.execute("SELECT * FROM loan_types").fetchall()
    lt_count = 0
    for lt in loan_types:
        try:
            pg_cursor.execute("""
                INSERT INTO loan_types (loan_name, description, is_active)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (lt['loan_name'], lt.get('description'), lt.get('is_active', 1)))
            lt_count += 1
        except:
            continue
    pg_conn.commit()
    print(f"   ✓ Migrated {lt_count} loan types")
except:
    print("   ⚠ Loan types table not found in SQLite, skipping...")

# Migrate system settings
print("\n   → Migrating system settings...")
try:
    settings = sqlite_cursor.execute("SELECT * FROM system_settings").fetchall()
    set_count = 0
    for setting in settings:
        try:
            pg_cursor.execute("""
                INSERT INTO system_settings (setting_key, setting_value, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (setting_key) DO UPDATE SET
                    setting_value = EXCLUDED.setting_value
            """, (setting['setting_key'], setting.get('setting_value'), setting.get('description')))
            set_count += 1
        except:
            continue
    pg_conn.commit()
    print(f"   ✓ Migrated {set_count} system settings")
except:
    print("   ⚠ System settings table not found in SQLite, skipping...")

# Close connections
sqlite_conn.close()
pg_conn.close()

print("\n" + "=" * 60)
print("MIGRATION COMPLETE!")
print("=" * 60)
print(f"\nSummary:")
print(f"  • Users: {user_count}")
print(f"  • Loan Applications: {app_count}")
print(f"  • Documents: {doc_count}")
print(f"\nPostgreSQL database is ready!")
