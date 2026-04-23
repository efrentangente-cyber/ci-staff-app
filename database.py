"""
Database Connection Manager
Supports both SQLite (local) and PostgreSQL (Render production)
Automatically detects which to use based on DATABASE_URL environment variable
"""

import os
import sqlite3

# Try to import PostgreSQL driver (only needed for production)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("⚠️  psycopg2 not installed - PostgreSQL support disabled")
    print("   For local development with SQLite, this is fine.")
    print("   For Render deployment, run: pip install psycopg2-binary")

def get_db():
    """
    Get database connection - automatically uses PostgreSQL or SQLite
    
    Returns:
        Database connection object
        
    Usage:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()
    """
    database_url = os.getenv('DATABASE_URL')
    
    # Use PostgreSQL if DATABASE_URL is set (Render production)
    if database_url and database_url.startswith('postgres'):
        if not POSTGRES_AVAILABLE:
            raise Exception("PostgreSQL URL provided but psycopg2 not installed. Run: pip install psycopg2-binary")
        
        # Render provides postgres:// but psycopg2 needs postgresql://
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor, sslmode='require')
            return conn
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            print(f"   DATABASE_URL: {database_url[:50]}...")
            raise
    
    # Use SQLite for local development (default)
    else:
        database_file = os.getenv('SQLITE_DATABASE', 'app.db')
        conn = sqlite3.connect(database_file, timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

def get_database_type():
    """
    Get current database type
    
    Returns:
        'postgresql' or 'sqlite'
    """
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres'):
        return 'postgresql'
    return 'sqlite'

def is_postgresql():
    """Check if using PostgreSQL"""
    return get_database_type() == 'postgresql'

def is_sqlite():
    """Check if using SQLite"""
    return get_database_type() == 'sqlite'

# Print database info on import (helpful for debugging)
if __name__ != '__main__':
    db_type = get_database_type()
    print(f"📊 Database: {db_type.upper()}")
    if db_type == 'postgresql':
        print("   ✓ Using PostgreSQL (production mode)")
    else:
        print("   ✓ Using SQLite (development mode)")
