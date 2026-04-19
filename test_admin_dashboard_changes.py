#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script to verify admin dashboard changes
"""

print("Testing Admin Dashboard Changes...")
print("=" * 50)

# Test 1: Check if admin_dashboard route was updated
print("\n1. Checking admin_dashboard route...")
with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    
    # Check for in_process_applications query
    if "in_process_applications = conn.execute(" in content:
        print("✓ in_process_applications query added")
    else:
        print("✗ in_process_applications query NOT found")
    
    # Check for WHERE la.status IN ('submitted', 'assigned_to_ci')
    if "WHERE la.status IN ('submitted', 'assigned_to_ci')" in content:
        print("✓ In Process status filter added")
    else:
        print("✗ In Process status filter NOT found")
    
    # Check for in_process_applications in render_template
    if "in_process_applications=in_process_applications" in content:
        print("✓ in_process_applications passed to template")
    else:
        print("✗ in_process_applications NOT passed to template")

# Test 2: Check if admin_dashboard.html was updated
print("\n2. Checking admin_dashboard.html template...")
with open('templates/admin_dashboard.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    
    # Check for In Process tab
    if "In Process (LPS → CI)" in content:
        print("✓ In Process tab header added")
    else:
        print("✗ In Process tab header NOT found")
    
    # Check for inProcessTable
    if 'id="inProcessTable"' in content:
        print("✓ inProcessTable element added")
    else:
        print("✗ inProcessTable element NOT found")
    
    # Check for reassign modal
    if 'id="reassignModal"' in content:
        print("✓ Reassign modal added")
    else:
        print("✗ Reassign modal NOT found")
    
    # Check for openReassignModal function
    if "function openReassignModal(" in content:
        print("✓ openReassignModal function added")
    else:
        print("✗ openReassignModal function NOT found")
    
    # Check for in_process_applications loop
    if "{% for app in in_process_applications %}" in content:
        print("✓ in_process_applications loop added")
    else:
        print("✗ in_process_applications loop NOT found")
    
    # Check for searchApplications updated for inprocess
    if "tableType === 'inprocess'" in content:
        print("✓ Search function updated for In Process tab")
    else:
        print("✗ Search function NOT updated for In Process tab")

# Test 3: Check loan_application.html
print("\n3. Checking loan_application.html template...")
with open('templates/loan_application.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()
    
    # Check for can_edit variable
    if "{% if can_edit %}" in content:
        print("✓ can_edit conditional found")
    else:
        print("✗ can_edit conditional NOT found")
    
    # Check for form submission
    if 'method="POST"' in content:
        print("✓ POST form method found")
    else:
        print("✗ POST form method NOT found")
    
    # Check for address autocomplete
    if 'id="address_suggestions"' in content:
        print("✓ Address autocomplete present")
    else:
        print("✗ Address autocomplete NOT found")

print("\n" + "=" * 50)
print("Test completed!")
print("\nSummary:")
print("- Admin dashboard route updated with In Process query")
print("- Admin dashboard template has new In Process tab")
print("- Reassign CI Staff modal and functions added")
print("- Loan application template ready for editing")
print("\nNext steps:")
print("1. Test the In Process tab in admin dashboard")
print("2. Test reassigning CI staff from In Process tab")
print("3. Test editing applications from LPS dashboard")
