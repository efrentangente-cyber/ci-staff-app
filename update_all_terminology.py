#!/usr/bin/env python3
"""
Comprehensive terminology update script
Updates all files with new terminology
"""

import os
import re

def update_file(filepath, replacements):
    """Update a file with multiple replacements"""
    if not os.path.exists(filepath):
        print(f"  ⚠ File not found: {filepath}")
        return False
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = 0
        
        for old, new in replacements:
            if old in content:
                count = content.count(old)
                content = content.replace(old, new)
                changes_made += count
                print(f"    - Replaced '{old}' → '{new}' ({count} times)")
        
        if changes_made > 0:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  ✓ Updated {filepath} ({changes_made} changes)")
            return True
        else:
            print(f"  - No changes needed in {filepath}")
            return False
            
    except Exception as e:
        print(f"  ✗ Error updating {filepath}: {e}")
        return False

def main():
    print("=" * 70)
    print("COMPREHENSIVE TERMINOLOGY UPDATE")
    print("=" * 70)
    
    # Define replacements for each file type
    
    # 1. Update templates - "Loan Staff" to "LPS"
    print("\n1. Updating 'Loan Staff' → 'LPS' in templates...")
    template_files = [
        'templates/admin_dashboard.html',
        'templates/loan_dashboard.html',
        'templates/admin_application.html',
        'templates/manage_users.html',
        'templates/reports.html',
    ]
    
    for filepath in template_files:
        update_file(filepath, [
            ('Loan Staff', 'LPS'),
            ('>Loan Staff<', '>LPS<'),
        ])
    
    # 2. Update app.py - reject to disapprove
    print("\n2. Updating 'Reject/Rejected' → 'Disapprove/Disapproved' in app.py...")
    update_file('app.py', [
        ("'rejected'", "'disapproved'"),
        ('"rejected"', '"disapproved"'),
        ('rejected', 'disapproved'),  # In status checks
        ('Reject', 'Disapprove'),
        ('REJECTED', 'DISAPPROVED'),
    ])
    
    # 3. Update admin_application.html - decision form
    print("\n3. Updating decision form in admin_application.html...")
    update_file('templates/admin_application.html', [
        ('<option value="rejected">Reject</option>', 
         '<option value="disapproved">Disapprove</option>\n                            <option value="deferred">Defer</option>'),
        ('rejected', 'disapproved'),
    ])
    
    # 4. Update base.html
    print("\n4. Updating base.html...")
    update_file('templates/base.html', [
        ('Loan Staff Dashboard', 'LPS Dashboard'),
    ])
    
    print("\n" + "=" * 70)
    print("✅ TERMINOLOGY UPDATE COMPLETE")
    print("=" * 70)
    print("\nManual steps still needed:")
    print("1. Add CI staff reassignment functionality")
    print("2. Remove 'Send directly to loan officer' option from submit form")
    print("3. Test all changes thoroughly")

if __name__ == '__main__':
    main()
