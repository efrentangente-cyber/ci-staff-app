import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

print("\n" + "="*70)
print("SETTING UP ALL 4 USER ACCOUNTS")
print("="*70)

# Check existing users
print("\nCurrent users in database:")
users = cursor.execute('SELECT id, email, name, role FROM users').fetchall()
for user_id, email, name, role in users:
    print(f"  {user_id}. {email} ({name}) - {role}")

# Define the 4 required users
required_users = [
    {
        'email': 'superadmin@dccco.test',
        'password': 'admin@2024',
        'name': 'Super Admin',
        'role': 'admin'
    },
    {
        'email': 'admin@dccco.test',
        'password': 'admin123',
        'name': 'Loan Officer',
        'role': 'loan_officer'
    },
    {
        'email': 'ci@dccco.test',
        'password': 'ci123',
        'name': 'CI Staff',
        'role': 'ci_staff'
    },
    {
        'email': 'loan@dccco.test',
        'password': 'loan123',
        'name': 'Loan Staff',
        'role': 'loan_staff'
    }
]

print("\n" + "="*70)
print("UPDATING/CREATING USERS")
print("="*70)

for user_data in required_users:
    # Check if user exists
    existing = cursor.execute('SELECT id, role, name FROM users WHERE email = ?', (user_data['email'],)).fetchone()
    
    if existing:
        user_id, current_role, current_name = existing
        # Update if role or name is different
        if current_role != user_data['role'] or current_name != user_data['name']:
            print(f"\n✓ Updating {user_data['email']}:")
            print(f"  Name: {current_name} → {user_data['name']}")
            print(f"  Role: {current_role} → {user_data['role']}")
            cursor.execute('UPDATE users SET name = ?, role = ? WHERE email = ?', 
                         (user_data['name'], user_data['role'], user_data['email']))
        else:
            print(f"\n✓ {user_data['email']} already correct")
    else:
        # Create new user
        print(f"\n✓ Creating {user_data['email']}:")
        print(f"  Name: {user_data['name']}")
        print(f"  Role: {user_data['role']}")
        password_hash = generate_password_hash(user_data['password'])
        cursor.execute('''
            INSERT INTO users (email, password_hash, name, role, is_approved)
            VALUES (?, ?, ?, ?, 1)
        ''', (user_data['email'], password_hash, user_data['name'], user_data['role']))

conn.commit()

print("\n" + "="*70)
print("FINAL USER LIST")
print("="*70)

users = cursor.execute('SELECT id, email, name, role FROM users ORDER BY id').fetchall()
for user_id, email, name, role in users:
    print(f"\n{user_id}. {name}")
    print(f"   Email: {email}")
    print(f"   Role: {role}")
    
    # Show password
    if email == 'superadmin@dccco.test':
        print(f"   Password: admin@2024")
    elif email == 'admin@dccco.test':
        print(f"   Password: admin123")
    elif email == 'ci@dccco.test':
        print(f"   Password: ci123")
    elif email == 'loan@dccco.test':
        print(f"   Password: loan123")

print("\n" + "="*70)
print("ALL 4 USERS ARE READY!")
print("="*70)

conn.close()
