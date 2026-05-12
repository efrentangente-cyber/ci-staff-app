import sqlite3

# Connect to database
conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Delete all applications, documents, messages, notifications
cursor.execute('DELETE FROM loan_applications')
cursor.execute('DELETE FROM documents')
cursor.execute('DELETE FROM messages')
cursor.execute('DELETE FROM notifications')

# Reset auto-increment counters
cursor.execute('DELETE FROM sqlite_sequence WHERE name="loan_applications"')
cursor.execute('DELETE FROM sqlite_sequence WHERE name="documents"')
cursor.execute('DELETE FROM sqlite_sequence WHERE name="messages"')
cursor.execute('DELETE FROM sqlite_sequence WHERE name="notifications"')

# Keep users but reset their workload
cursor.execute('UPDATE users SET current_workload = 0')

conn.commit()
conn.close()

print("✓ Database cleaned successfully!")
print("✓ All applications, documents, messages, and notifications deleted")
print("✓ User accounts preserved")
