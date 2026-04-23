from database import get_db

conn = get_db()
cursor = conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
tables = [row['table_name'] for row in cursor.fetchall()]
print('Tables in PostgreSQL:')
for table in sorted(tables):
    print(f'  - {table}')
conn.close()
