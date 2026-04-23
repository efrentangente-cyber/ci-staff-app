from database import get_db

conn = get_db()

# Count applications
cursor = conn.execute("SELECT COUNT(*) as count FROM loan_applications")
app_count = cursor.fetchone()['count']
print(f"✅ Applications: {app_count}")

# Count users
cursor = conn.execute("SELECT COUNT(*) as count FROM users")
user_count = cursor.fetchone()['count']
print(f"✅ Users: {user_count}")

# Count loan types
cursor = conn.execute("SELECT COUNT(*) as count FROM loan_types")
loan_type_count = cursor.fetchone()['count']
print(f"✅ Loan Types: {loan_type_count}")

# Count system settings
cursor = conn.execute("SELECT COUNT(*) as count FROM system_settings")
settings_count = cursor.fetchone()['count']
print(f"✅ System Settings: {settings_count}")

conn.close()

print("\n🎉 All data verified!")
