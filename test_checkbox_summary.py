#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for CI Checkbox Summary feature
Verifies all components are in place and working
"""

import os
import sys

def test_files_exist():
    """Test that all required files exist"""
    print("=" * 60)
    print("TEST 1: Checking if all files exist...")
    print("=" * 60)
    
    required_files = [
        'templates/ci_checklist_summary.html',
        'templates/ci_review_application.html',
        'static/ci-checklist-wizard.js',
        'app.py'
    ]
    
    all_exist = True
    for file_path in required_files:
        exists = os.path.exists(file_path)
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"{status}: {file_path}")
        if not exists:
            all_exist = False
    
    print()
    return all_exist


def test_route_exists():
    """Test that the checkbox summary route exists in app.py"""
    print("=" * 60)
    print("TEST 2: Checking if route exists in app.py...")
    print("=" * 60)
    
    try:
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = [
            ("Route definition", "@app.route('/ci/checklist/summary/<int:id>')"),
            ("Function definition", "def ci_checklist_summary(id):"),
            ("Template render", "return render_template('ci_checklist_summary.html'")
        ]
        
        all_found = True
        for check_name, check_string in checks:
            found = check_string in content
            status = "✅ FOUND" if found else "❌ NOT FOUND"
            print(f"{status}: {check_name}")
            if not found:
                all_found = False
        
        print()
        return all_found
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print()
        return False


def test_javascript_function():
    """Test that loadCheckboxData function exists in JavaScript"""
    print("=" * 60)
    print("TEST 3: Checking JavaScript functions...")
    print("=" * 60)
    
    try:
        with open('static/ci-checklist-wizard.js', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = [
            ("loadCheckboxData function", "function loadCheckboxData()"),
            ("Session storage get", "sessionStorage.getItem('ci_checkbox_data')"),
            ("Checkbox notification", "function showCheckboxNotification()"),
            ("Function call in DOMContentLoaded", "loadCheckboxData();")
        ]
        
        all_found = True
        for check_name, check_string in checks:
            found = check_string in content
            status = "✅ FOUND" if found else "❌ NOT FOUND"
            print(f"{status}: {check_name}")
            if not found:
                all_found = False
        
        print()
        return all_found
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print()
        return False


def test_template_structure():
    """Test that checkbox summary template has required elements"""
    print("=" * 60)
    print("TEST 4: Checking template structure...")
    print("=" * 60)
    
    try:
        with open('templates/ci_checklist_summary.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = [
            ("Extends base template", "{% extends \"base.html\" %}"),
            ("Progress indicator", "id=\"progressBar\""),
            ("Form element", "<form id=\"checklistSummaryForm\">"),
            ("Residence status section", "Residence Status"),
            ("Type of house section", "Type of House"),
            ("Court checking section", "Court and Government Agency Checking"),
            ("Employment section", "Employment Status"),
            ("Business nature section", "Business Nature"),
            ("Credit checking section", "Credit Checking"),
            ("Membership section", "Membership Status"),
            ("Capacity section", "Capacity Assessment"),
            ("Character section", "Character Assessment"),
            ("Collateral section", "Collateral"),
            ("Health section", "Condition - Health"),
            ("Business condition section", "Condition - Business"),
            ("Recommendations section", "Recommendations"),
            ("Proceed button", "Proceed to 5-Page Form"),
            ("JavaScript function", "function proceedToWizard()"),
            ("Session storage set", "sessionStorage.setItem('ci_checkbox_data'")
        ]
        
        all_found = True
        for check_name, check_string in checks:
            found = check_string in content
            status = "✅ FOUND" if found else "❌ NOT FOUND"
            print(f"{status}: {check_name}")
            if not found:
                all_found = False
        
        print()
        return all_found
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print()
        return False


def test_review_page_link():
    """Test that review page has link to checkbox summary"""
    print("=" * 60)
    print("TEST 5: Checking review page link...")
    print("=" * 60)
    
    try:
        with open('templates/ci_review_application.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = [
            ("Link to checkbox summary", "url_for('ci_checklist_summary', id=application.id)"),
            ("Button text", "Fill Interview Checklist")
        ]
        
        all_found = True
        for check_name, check_string in checks:
            found = check_string in content
            status = "✅ FOUND" if found else "❌ NOT FOUND"
            print(f"{status}: {check_name}")
            if not found:
                all_found = False
        
        print()
        return all_found
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print()
        return False


def count_checkboxes():
    """Count total checkboxes in summary template"""
    print("=" * 60)
    print("TEST 6: Counting checkboxes...")
    print("=" * 60)
    
    try:
        with open('templates/ci_checklist_summary.html', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Count checkbox inputs
        checkbox_count = content.count('type="checkbox"')
        
        print(f"Total checkboxes found: {checkbox_count}")
        
        if checkbox_count >= 100:
            print(f"✅ PASS: Found {checkbox_count} checkboxes (expected 100+)")
            print()
            return True
        else:
            print(f"❌ FAIL: Only found {checkbox_count} checkboxes (expected 100+)")
            print()
            return False
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "CI CHECKBOX SUMMARY - TEST SUITE" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    tests = [
        ("Files Exist", test_files_exist),
        ("Route Exists", test_route_exists),
        ("JavaScript Functions", test_javascript_function),
        ("Template Structure", test_template_structure),
        ("Review Page Link", test_review_page_link),
        ("Checkbox Count", count_checkboxes)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ ERROR in {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Print summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 10 + "🎉 ALL TESTS PASSED! 🎉" + " " * 22 + "║")
        print("║" + " " * 10 + "Ready for deployment!" + " " * 24 + "║")
        print("╚" + "=" * 58 + "╝")
        print()
        return 0
    else:
        print()
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 10 + "⚠️  SOME TESTS FAILED ⚠️" + " " * 21 + "║")
        print("║" + " " * 10 + "Please fix issues before deploying" + " " * 11 + "║")
        print("╚" + "=" * 58 + "╝")
        print()
        return 1


if __name__ == '__main__':
    sys.exit(main())
