import sqlite3

# Add profile_photo column to existing database
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
    conn.commit()
    print("✓ Added profile_photo column to users table")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower():
        print("✓ profile_photo column already exists")
    else:
        print(f"✗ Error: {e}")

conn.close()
