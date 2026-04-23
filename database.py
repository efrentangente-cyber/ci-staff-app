"""
Database Connection Manager
Supports both SQLite (local) and PostgreSQL (Render production)
Automatically detects which to use based on DATABASE_URL environment variable
Updated: 2026-04-23 - Fixed PostgreSQL compatibility
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

class DatabaseConnection:
    """Wrapper for database connection that handles SQL placeholder conversion"""
    
    def __init__(self, conn, db_type):
        self._conn = conn
        self._db_type = db_type
    
    def cursor(self):
        """Get cursor from underlying connection"""
        return self._conn.cursor()
    
    def _adapt_query_for_postgresql(self, query):
        """
        Adapt SQLite-style SQL for psycopg2:
        - Convert positional placeholders from ? to %s
        - Escape literal % so psycopg2 doesn't treat LIKE patterns as placeholders
        """
        # First, escape literal % while preserving psycopg2 placeholders.
        escaped_query_parts = []
        i = 0
        while i < len(query):
            ch = query[i]
            if ch == '%':
                next_char = query[i + 1] if i + 1 < len(query) else ''
                if next_char == '%':
                    escaped_query_parts.append('%%')
                    i += 2
                    continue
                if next_char in ('s', '('):
                    escaped_query_parts.append('%')
                else:
                    escaped_query_parts.append('%%')
            else:
                escaped_query_parts.append(ch)
            i += 1
        escaped_query = ''.join(escaped_query_parts)

        # Then convert ? placeholders only when outside quoted strings.
        adapted_parts = []
        in_single_quote = False
        in_double_quote = False

        for ch in escaped_query:
            if ch == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                adapted_parts.append(ch)
                continue
            if ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                adapted_parts.append(ch)
                continue
            if ch == '?' and not in_single_quote and not in_double_quote:
                adapted_parts.append('%s')
            else:
                adapted_parts.append(ch)

        return ''.join(adapted_parts)

    def execute(self, query, params=None):
        """Execute query with automatic placeholder conversion"""
        if self._db_type == 'postgresql':
            query = self._adapt_query_for_postgresql(query)
        
        cursor = self._conn.cursor()
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        return cursor
    
    def executescript(self, script):
        """Execute SQL script (SQLite only)"""
        if self._db_type == 'sqlite':
            return self._conn.executescript(script)
        else:
            # For PostgreSQL, execute statements one by one
            cursor = self._conn.cursor()
            cursor.execute(script)
            return cursor
    
    def commit(self):
        """Commit transaction"""
        return self._conn.commit()
    
    def rollback(self):
        """Rollback transaction"""
        return self._conn.rollback()
    
    def close(self):
        """Close connection"""
        return self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        self.close()

def get_db():
    """
    Get database connection - automatically uses PostgreSQL or SQLite
    
    Returns:
        DatabaseConnection wrapper object
        
    Usage:
        conn = get_db()
        cursor = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
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
            return DatabaseConnection(conn, 'postgresql')
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            print(f"   DATABASE_URL: {database_url[:50]}...")
            raise
    
    # Use SQLite for local development (default)
    else:
        database_file = os.getenv('SQLITE_DATABASE', 'app.db')
        conn = sqlite3.connect(database_file, timeout=10)
        conn.row_factory = sqlite3.Row
        return DatabaseConnection(conn, 'sqlite')

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
