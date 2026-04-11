#!/usr/bin/env python3
"""
View and Print All Records from Database
This script displays all data from your loan management system
"""

import sqlite3
from datetime import datetime

def print_separator(title=""):
    print("\n" + "=" * 80)
    if title:
        print(f" {title} ".center(80, "="))
        print("=" * 80)

def view_all_records():
    try:
        conn = sqlite3.connect('app.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        print_separator("DATABASE RECORDS REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. USERS
        print_separator("USERS")
        cursor.execute('SELECT * FROM users ORDER BY id')
        users = cursor.fetchall()
        print(f"Total Users: {len(users)}\n")
        
        for user in users:
            print(f"ID: {user['id']}")
            print(f"  Name: {user['name']}")
            print(f"  Email: {user['email']}")
            print(f"  Role: {user['role']}")
            print(f"  Approved: {'Yes' if user['is_approved'] else 'No'}")
            print(f"  Workload: {user['current_workload']}")
            if user['assigned_route']:
                print(f"  Assigned Routes: {user['assigned_route']}")
            print(f"  Created: {user['created_at']}")
            print("-" * 80)
        
        # 2. LOAN APPLICATIONS
        print_separator("LOAN APPLICATIONS")
        cursor.execute('''
            SELECT la.*, 
                   u1.name as submitted_by_name,
                   u2.name as ci_staff_name
            FROM loan_applications la
            LEFT JOIN users u1 ON la.submitted_by = u1.id
            LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
            ORDER BY la.id DESC
        ''')
        applications = cursor.fetchall()
        print(f"Total Applications: {len(applications)}\n")
        
        for app in applications:
            print(f"Application ID: #{app['id']}")
            print(f"  Member Name: {app['member_name']}")
            print(f"  Contact: {app['member_contact']}")
            print(f"  Address: {app['member_address']}")
            print(f"  Loan Amount: ₱{app['loan_amount']:,.2f}" if app['loan_amount'] else "  Loan Amount: N/A")
            print(f"  Loan Type: {app['loan_type'] if app['loan_type'] else 'N/A'}")
            print(f"  Status: {app['status']}")
            print(f"  Needs CI: {'Yes' if app['needs_ci_interview'] else 'No'}")
            print(f"  Submitted By: {app['submitted_by_name']}")
            print(f"  Assigned CI: {app['ci_staff_name'] if app['ci_staff_name'] else 'Not assigned'}")
            print(f"  Submitted At: {app['submitted_at']}")
            if app['ci_completed_at']:
                print(f"  CI Completed: {app['ci_completed_at']}")
            if app['admin_decision_at']:
                print(f"  Admin Decision: {app['admin_decision_at']}")
            if app['ci_notes']:
                print(f"  CI Notes: {app['ci_notes'][:100]}..." if len(app['ci_notes']) > 100 else f"  CI Notes: {app['ci_notes']}")
            print("-" * 80)
        
        # 3. DOCUMENTS
        print_separator("UPLOADED DOCUMENTS")
        cursor.execute('''
            SELECT d.*, la.member_name, u.name as uploaded_by_name
            FROM documents d
            LEFT JOIN loan_applications la ON d.loan_application_id = la.id
            LEFT JOIN users u ON d.uploaded_by = u.id
            ORDER BY d.uploaded_at DESC
        ''')
        documents = cursor.fetchall()
        print(f"Total Documents: {len(documents)}\n")
        
        for doc in documents:
            print(f"Document ID: {doc['id']}")
            print(f"  Application: #{doc['loan_application_id']} - {doc['member_name']}")
            print(f"  File Name: {doc['file_name']}")
            print(f"  File Path: {doc['file_path']}")
            print(f"  Uploaded By: {doc['uploaded_by_name']}")
            print(f"  Uploaded At: {doc['uploaded_at']}")
            print("-" * 80)
        
        # 4. MESSAGES
        print_separator("MESSAGES")
        cursor.execute('''
            SELECT m.*, u.name as sender_name, la.member_name
            FROM messages m
            LEFT JOIN users u ON m.sender_id = u.id
            LEFT JOIN loan_applications la ON m.loan_application_id = la.id
            ORDER BY m.sent_at DESC
            LIMIT 50
        ''')
        messages = cursor.fetchall()
        print(f"Total Messages (showing last 50): {len(messages)}\n")
        
        for msg in messages:
            print(f"Message ID: {msg['id']}")
            print(f"  Application: #{msg['loan_application_id']} - {msg['member_name']}")
            print(f"  Sender: {msg['sender_name']}")
            print(f"  Type: {msg['message_type']}")
            if msg['message']:
                print(f"  Message: {msg['message'][:100]}..." if len(msg['message']) > 100 else f"  Message: {msg['message']}")
            print(f"  Sent At: {msg['sent_at']}")
            print("-" * 80)
        
        # 5. NOTIFICATIONS
        print_separator("NOTIFICATIONS")
        cursor.execute('''
            SELECT n.*, u.name as user_name
            FROM notifications n
            LEFT JOIN users u ON n.user_id = u.id
            ORDER BY n.created_at DESC
            LIMIT 50
        ''')
        notifications = cursor.fetchall()
        print(f"Total Notifications (showing last 50): {len(notifications)}\n")
        
        for notif in notifications:
            print(f"Notification ID: {notif['id']}")
            print(f"  User: {notif['user_name']}")
            print(f"  Message: {notif['message']}")
            print(f"  Link: {notif['link'] if notif['link'] else 'N/A'}")
            print(f"  Read: {'Yes' if notif['is_read'] else 'No'}")
            print(f"  Created: {notif['created_at']}")
            print("-" * 80)
        
        # 6. STATISTICS
        print_separator("STATISTICS SUMMARY")
        
        # Count by status
        cursor.execute('SELECT status, COUNT(*) as count FROM loan_applications GROUP BY status')
        status_counts = cursor.fetchall()
        print("\nApplications by Status:")
        for row in status_counts:
            print(f"  {row['status']}: {row['count']}")
        
        # Count by role
        cursor.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role')
        role_counts = cursor.fetchall()
        print("\nUsers by Role:")
        for row in role_counts:
            print(f"  {row['role']}: {row['count']}")
        
        # Count by loan type
        cursor.execute('SELECT loan_type, COUNT(*) as count FROM loan_applications WHERE loan_type IS NOT NULL GROUP BY loan_type')
        type_counts = cursor.fetchall()
        if type_counts:
            print("\nApplications by Loan Type:")
            for row in type_counts:
                print(f"  {row['loan_type']}: {row['count']}")
        
        print_separator("END OF REPORT")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    view_all_records()
