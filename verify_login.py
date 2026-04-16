import sqlite3
from werkzeug.security import check_password_hash

print("\n" + "="*60)
print("SUPER ADMIN LOGIN VERIFICATION")
print("="*60)

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Test credentials
test_email = 'superadmin@dccco.test'
test_password = 'admin@2024'

print(f"\nTesting login with:")
print(f"  Email: {test_email}")
print(f"  Password: {test_password}")

# Get user from database
user = cursor.execute('SELECT * FROM users WHERE email = ?', (test_email,)).fetchone()

if not user:
    print("\n❌ User not found in database!")
else:
    # Get column names
    columns = [description[0] for description in cursor.description]
    user_dict = dict(zip(columns, user))
    
    print(f"\n✓ User found in database")
    print(f"  ID: {user_dict['id']}")
    print(f"  Name: {user_dict['name']}")
    print(f"  Email: {user_dict['email']}")
    print(f"  Role: {user_dict['role']}")
    print(f"  Is Approved: {user_dict['is_approved']}")
    
    # Check password
    password_valid = check_password_hash(user_dict['password_hash'], test_password)
    
    if password_valid:
        print(f"\n✓ Password is CORRECT")
        
        if user_dict['is_approved'] == 1:
            print(f"✓ Account is APPROVED")
            print("\n" + "="*60)
            print("LOGIN SHOULD WORK!")
            print("="*60)
            print("\nCredentials to use:")
            print(f"  Email: {test_email}")
            print(f"  Password: {test_password}")
        else:
            print(f"\n❌ Account is NOT approved")
    else:
        print(f"\n❌ Password is INCORRECT")

conn.close()
