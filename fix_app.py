with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix broken SQL string - single quotes inside single-quoted string
old = "conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE 'New message from%''"
new = 'conn.execute(\'\'\'SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"\'\'\''

content = content.replace(old, new)
print('Replacements done. New message from occurrences:', content.count('New message from'))

with open('app.py', 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print('Done, lines:', len(content.splitlines()))
