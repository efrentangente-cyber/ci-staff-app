#!/usr/bin/env python3
"""
View PostgreSQL Database - No psql installation needed!
"""

import os
os.environ['DATABASE_URL'] = 'postgresql://dccco_app:JipCepytJQE4DlYVfgJM4yxJXsNF8GSh@dpg-d7kltthj2pic73cana4g-a.oregon-postgres.render.com/dbs_txpj'

from database import get_db
import sys

def print_separator():
    print("=" * 100)

def view_users():
    print_separator()
    print("👥 USERS")
    print_separator()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, role, is_approved FROM users ORDER BY id")
    
    print(f"{'ID':<5} {'Email':<35} {'Name':<25} {'Role':<15} {'Approved'}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        approved = "✓" if row['is_approved'] else "✗"
        print(f"{row['id']:<5} {row['email']:<35} {row['name']:<25} {row['role']:<15} {approved}")
    
    conn.close()
    print()

def view_applications_summary():
    print_separator()
    print("📊 LOAN APPLICATIONS SUMMARY")
    print_separator()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Total count
    cursor.execute("SELECT COUNT(*) as count FROM loan_applications")
    total = cursor.fetchone()['count']
    print(f"\n📝 Total Applications: {total}")
    
    # By status
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM loan_applications 
        GROUP BY status 
        ORDER BY count DESC
    """)
    
    print("\n📈 By Status:")
    status_emoji = {
        'approved': '✅',
        'disapproved': '❌',
        'deferred': '⏸️',
        'ci_completed': '📋',
        'assigned_to_ci': '🔍',
        'submitted': '📝'
    }
    
    for row in cursor.fetchall():
        emoji = status_emoji.get(row['status'], '•')
        print(f"  {emoji} {row['status'].upper():<20} {row['count']:>5} applications")
    
    # By loan type
    cursor.execute("""
        SELECT loan_type, COUNT(*) as count 
        FROM loan_applications 
        WHERE loan_type IS NOT NULL
        GROUP BY loan_type 
        ORDER BY count DESC 
        LIMIT 10
    """)
    
    print("\n💰 Top 10 Loan Types:")
    for row in cursor.fetchall():
        loan_type = row['loan_type'] or 'Not specified'
        print(f"  • {loan_type:<40} {row['count']:>3} applications")
    
    conn.close()
    print()

def view_recent_applications(limit=10):
    print_separator()
    print(f"📋 RECENT {limit} APPLICATIONS")
    print_separator()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT id, member_name, loan_type, loan_amount, status, submitted_at
        FROM loan_applications 
        ORDER BY id DESC 
        LIMIT {limit}
    """)
    
    print(f"{'ID':<5} {'Name':<25} {'Loan Type':<30} {'Amount':<15} {'Status':<15} {'Date'}")
    print("-" * 100)
    
    for row in cursor.fetchall():
        amount = f"₱{row['loan_amount']:,.0f}"
        date = str(row['submitted_at'])[:10] if row['submitted_at'] else 'N/A'
        print(f"{row['id']:<5} {row['member_name']:<25} {row['loan_type']:<30} {amount:<15} {row['status']:<15} {date}")
    
    conn.close()
    print()

def view_application_details(app_id):
    print_separator()
    print(f"📄 APPLICATION DETAILS - ID: {app_id}")
    print_separator()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM loan_applications WHERE id = %s
    """, (app_id,))
    
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ Application ID {app_id} not found")
        conn.close()
        return
    
    print(f"\n👤 APPLICANT INFORMATION")
    print(f"  Name: {row['member_name']}")
    print(f"  Contact: {row['member_contact']}")
    print(f"  Address: {row['member_address']}")
    
    print(f"\n💰 LOAN DETAILS")
    print(f"  Type: {row['loan_type']}")
    print(f"  Amount: ₱{row['loan_amount']:,.2f}")
    print(f"  Status: {row['status'].upper()}")
    print(f"  Submitted: {row['submitted_at']}")
    
    if row['lps_remarks']:
        print(f"\n📝 LPS REMARKS")
        print(f"  {row['lps_remarks']}")
    
    if row['ci_notes']:
        print(f"\n🔍 CI INVESTIGATION NOTES")
        print(f"  {row['ci_notes']}")
        print(f"  Completed: {row['ci_completed_at']}")
        if row['ci_latitude'] and row['ci_longitude']:
            print(f"  Location: {row['ci_latitude']}, {row['ci_longitude']}")
    
    if row['admin_notes']:
        print(f"\n👨‍💼 ADMIN DECISION")
        print(f"  {row['admin_notes']}")
        print(f"  Date: {row['admin_decision_at']}")
    
    conn.close()
    print()

def search_applications(search_term):
    print_separator()
    print(f"🔍 SEARCH RESULTS: '{search_term}'")
    print_separator()
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, member_name, loan_type, loan_amount, status
        FROM loan_applications 
        WHERE member_name ILIKE %s 
           OR loan_type ILIKE %s
           OR member_contact ILIKE %s
        ORDER BY id DESC
        LIMIT 20
    """, (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
    
    results = cursor.fetchall()
    
    if not results:
        print(f"❌ No applications found matching '{search_term}'")
    else:
        print(f"\n✓ Found {len(results)} applications:\n")
        print(f"{'ID':<5} {'Name':<30} {'Loan Type':<30} {'Amount':<15} {'Status'}")
        print("-" * 100)
        
        for row in results:
            amount = f"₱{row['loan_amount']:,.0f}"
            print(f"{row['id']:<5} {row['member_name']:<30} {row['loan_type']:<30} {amount:<15} {row['status']}")
    
    conn.close()
    print()

def interactive_menu():
    while True:
        print_separator()
        print("🗄️  DATABASE VIEWER - INTERACTIVE MENU")
        print_separator()
        print("\n1. View Users")
        print("2. View Applications Summary")
        print("3. View Recent Applications")
        print("4. View Application Details (by ID)")
        print("5. Search Applications")
        print("6. Exit")
        print()
        
        choice = input("Enter your choice (1-6): ").strip()
        print()
        
        if choice == '1':
            view_users()
        elif choice == '2':
            view_applications_summary()
        elif choice == '3':
            limit = input("How many recent applications? (default 10): ").strip()
            limit = int(limit) if limit.isdigit() else 10
            view_recent_applications(limit)
        elif choice == '4':
            app_id = input("Enter application ID: ").strip()
            if app_id.isdigit():
                view_application_details(int(app_id))
            else:
                print("❌ Invalid ID")
        elif choice == '5':
            search_term = input("Enter search term (name, loan type, or phone): ").strip()
            if search_term:
                search_applications(search_term)
            else:
                print("❌ Please enter a search term")
        elif choice == '6':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-6.")
        
        input("\nPress Enter to continue...")
        print("\n" * 2)

if __name__ == '__main__':
    print("\n")
    print("=" * 100)
    print("🗄️  DCCCO LOAN MANAGEMENT SYSTEM - DATABASE VIEWER")
    print("=" * 100)
    print()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'users':
            view_users()
        elif command == 'summary':
            view_applications_summary()
        elif command == 'recent':
            limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            view_recent_applications(limit)
        elif command == 'view' and len(sys.argv) > 2:
            view_application_details(int(sys.argv[2]))
        elif command == 'search' and len(sys.argv) > 2:
            search_applications(sys.argv[2])
        else:
            print("Usage:")
            print("  python view_database.py              - Interactive menu")
            print("  python view_database.py users        - View all users")
            print("  python view_database.py summary      - View summary")
            print("  python view_database.py recent [N]   - View N recent applications")
            print("  python view_database.py view <ID>    - View application details")
            print("  python view_database.py search <term> - Search applications")
    else:
        interactive_menu()
