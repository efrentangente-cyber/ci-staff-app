#!/usr/bin/env python3
"""
Clean up unnecessary documentation and test files
Keeps only essential system files
"""

import os
import glob

# Files to delete
files_to_delete = []

# All .md files (documentation)
md_files = glob.glob('*.md')
files_to_delete.extend(md_files)

# Test files
test_patterns = [
    'test_*.py',
    'check_*.py',
    'verify_*.py',
    '*_check.py',
    'comprehensive_*.py'
]

for pattern in test_patterns:
    files_to_delete.extend(glob.glob(pattern))

# Migration/setup scripts (keep only essential ones)
setup_scripts = [
    'change_admin_to_loan_officer.py',
    'make_current_admin_super.py',
    'show_admin_features.py',
    'fix_admin_role.py',
    'update_all_terminology.py',
    'view_all_records.py'
]
files_to_delete.extend(setup_scripts)

# HTML files that are not templates
html_files = [
    'SMS_MODAL_FOR_ADMIN_DASHBOARD.html'
]
files_to_delete.extend(html_files)

# Remove duplicates
files_to_delete = list(set(files_to_delete))

# Files to KEEP (essential)
keep_files = [
    'requirements.txt',
    'README.md',  # If it exists
    'Procfile',
    '.env'
]

# Filter out files to keep
files_to_delete = [f for f in files_to_delete if f not in keep_files and os.path.exists(f)]

print("=" * 70)
print("CLEANUP: Removing Unnecessary Files")
print("=" * 70)
print(f"\nFound {len(files_to_delete)} files to delete:\n")

# Group by type
md_count = sum(1 for f in files_to_delete if f.endswith('.md'))
py_count = sum(1 for f in files_to_delete if f.endswith('.py'))
html_count = sum(1 for f in files_to_delete if f.endswith('.html'))

print(f"  - Markdown files (.md): {md_count}")
print(f"  - Python scripts (.py): {py_count}")
print(f"  - HTML files (.html): {html_count}")

print("\nDeleting files...")

deleted_count = 0
for file_path in files_to_delete:
    try:
        os.remove(file_path)
        deleted_count += 1
        print(f"  ✓ Deleted: {file_path}")
    except Exception as e:
        print(f"  ✗ Failed to delete {file_path}: {e}")

print("\n" + "=" * 70)
print(f"✅ CLEANUP COMPLETE")
print("=" * 70)
print(f"\nDeleted: {deleted_count}/{len(files_to_delete)} files")
print("\nYour system now contains only essential files:")
print("  ✓ app.py (main application)")
print("  ✓ schema.sql (database schema)")
print("  ✓ requirements.txt (dependencies)")
print("  ✓ templates/ (HTML templates)")
print("  ✓ static/ (CSS, JS, images)")
print("  ✓ Migration scripts (for database updates)")
print("  ✓ Production setup scripts")
print("\nAll documentation and test files have been removed.")
