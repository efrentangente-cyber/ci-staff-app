import sqlite3

conn = sqlite3.connect('app.db')

print("=== ALL APPLICATIONS ===")
apps = conn.execute('SELECT id, member_name, status FROM loan_applications ORDER BY id').fetchall()
for app in apps:
    print(f"App ID: {app[0]} | Member: {app[1]} | Status: {app[2]}")
    docs = conn.execute('SELECT id, file_name FROM documents WHERE loan_application_id=?', (app[0],)).fetchall()
    if docs:
        for doc in docs:
            print(f"  - Doc ID: {doc[0]} | File: {doc[1]}")
    else:
        print("  - No documents")
    print()

conn.close()
