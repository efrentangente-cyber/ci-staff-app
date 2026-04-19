#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test template rendering for ci_checklist_summary.html
"""

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
import os

def test_template():
    """Test if the template can be loaded and rendered"""
    try:
        # Create Jinja2 environment
        env = Environment(loader=FileSystemLoader('templates'))
        
        # Try to load the template
        print("Loading template...")
        template = env.get_template('ci_checklist_summary.html')
        print("✅ Template loaded successfully")
        
        # Try to render with dummy data
        print("\nRendering template with dummy data...")
        dummy_data = {
            'application': {
                'id': 1,
                'member_name': 'Test User',
                'loan_type': 'Personal Loan',
                'loan_amount': 10000
            },
            'unread_count': 0
        }
        
        html = template.render(**dummy_data)
        print("✅ Template rendered successfully")
        print(f"   Output length: {len(html)} characters")
        
        return True
        
    except TemplateSyntaxError as e:
        print(f"❌ Template Syntax Error:")
        print(f"   Line {e.lineno}: {e.message}")
        print(f"   File: {e.filename}")
        return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("Testing ci_checklist_summary.html")
    print("=" * 60)
    
    if test_template():
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
