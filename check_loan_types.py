import sqlite3

conn = sqlite3.connect('app.db')
conn.row_factory = sqlite3.Row
rows = conn.execute('SELECT id, name FROM loan_types WHERE is_active=1 ORDER BY name ASC').fetchall()
conn.close()

print(f'Found {len(rows)} active loan types:')
for r in rows:
    print(f'  {r["id"]}: {r["name"]}')
