import sqlite3
from werkzeug.security import check_password_hash

conn = sqlite3.connect('app.db')
cursor = conn.cursor()

# Get superadmin user
user = cursor.execute('SELECT email, password_hash FROM users WHERE email = ?', ('superadmin@dccco.test',)).fetchone()

if user:
    email, password_hash = user
    print(f"\nUser found: {email}")
    
    # Test password
    test_password = 'admin@2024'
    is_valid = check_password_hash(password_hash, test_password)
    
    print(f"Password '{test_password}' is valid: {is_valid}")
    
    if not is_valid:
        print("\nPassword hash in database doesn't match 'admin@2024'")
        print("Regenerating password hash...")
        
        from werkzeug.security import generate_password_hash
        new_hash = generate_password_hash('admin@2024')
        cursor.execute('UPDATE users SET password_hash = ? WHERE email = ?', (new_hash, 'superadmin@dccco.test'))
        conn.commit()
        print("✓ Password updated successfully!")
        print("You can now login with: superadmin@dccco.test / admin@2024")
else:
    print("User not found!")

conn.close()
