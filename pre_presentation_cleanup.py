#!/usr/bin/env python3
"""
Pre-Presentation Cleanup Script
Removes unnecessary files and ensures system is ready for presentation
"""

import os
import shutil

# Files to remove (unnecessary migration scripts and temp files)
FILES_TO_REMOVE = [
    'migrate_add_deferred_status.py',
    'migrate_add_loan_type.py',
    'migrate_add_route.py',
    'migrate_add_sms_templates.py',
    'migrate_allow_null_role.py',
    'migrate_direct_messages_media.py',
    'migrate_role_restructure.py',
    'migrate_status_constraint.py',
    'add_loan_officer_permissions.py',
    'apply_terminology_changes.py',
    'clean_database.py',
    'cleanup_unnecessary_files.py',
    'reset_database.py',
    'secure_routes.py',
    'setup_all_users.py',
    'setup_production.py',
    '~$app.db',  # Temp file
]

# Directories to remove (if they exist and are empty or unnecessary)
DIRS_TO_CLEAN = [
    '__pycache__',
    '.idea',
    '.vscode',
]

def cleanup():
    """Remove unnecessary files and directories"""
    removed_files = []
    removed_dirs = []
    
    # Remove files
    for filename in FILES_TO_REMOVE:
        if os.path.exists(filename):
            try:
                os.remove(filename)
                removed_files.append(filename)
                print(f"✓ Removed: {filename}")
            except Exception as e:
                print(f"✗ Could not remove {filename}: {e}")
    
    # Remove directories
    for dirname in DIRS_TO_CLEAN:
        if os.path.exists(dirname):
            try:
                shutil.rmtree(dirname)
                removed_dirs.append(dirname)
                print(f"✓ Removed directory: {dirname}")
            except Exception as e:
                print(f"✗ Could not remove {dirname}: {e}")
    
    print(f"\n✓ Cleanup complete!")
    print(f"  - Removed {len(removed_files)} files")
    print(f"  - Removed {len(removed_dirs)} directories")
    
    # Check critical files
    print("\n✓ Checking critical files...")
    critical_files = ['app.py', 'app.db', 'requirements.txt', 'schema.sql']
    for f in critical_files:
        if os.path.exists(f):
            print(f"  ✓ {f} exists")
        else:
            print(f"  ✗ WARNING: {f} is missing!")

if __name__ == '__main__':
    print("=" * 60)
    print("PRE-PRESENTATION CLEANUP")
    print("=" * 60)
    print("\nThis will remove unnecessary migration and setup files.")
    response = input("Continue? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        cleanup()
    else:
        print("Cleanup cancelled.")
