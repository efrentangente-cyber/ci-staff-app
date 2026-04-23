#!/usr/bin/env python3
"""
Show sample CI checklist data structure
"""

import os
os.environ['DATABASE_URL'] = 'postgresql://dccco_app:JipCepytJQE4DlYVfgJM4yxJXsNF8GSh@dpg-d7kltthj2pic73cana4g-a.oregon-postgres.render.com/dbs_txpj'

from database import get_db
import json

print("=" * 80)
print("CI CHECKLIST DATA STRUCTURE")
print("=" * 80)
print()

conn = get_db()
cursor = conn.cursor()

cursor.execute("""
    SELECT member_name, loan_type, loan_amount, ci_checklist_data 
    FROM loan_applications 
    WHERE ci_checklist_data IS NOT NULL 
    AND ci_checklist_data != ''
    ORDER BY id DESC
    LIMIT 1
""")

row = cursor.fetchone()

if row:
    print(f"Application: {row['member_name']}")
    print(f"Loan Type: {row['loan_type']}")
    print(f"Loan Amount: ₱{row['loan_amount']:,.2f}")
    print()
    print("=" * 80)
    print("CI CHECKLIST DATA (3 PAGES)")
    print("=" * 80)
    print()
    
    checklist = json.loads(row['ci_checklist_data'])
    
    print("📋 PAGE 1 - APPLICANT INFORMATION")
    print("-" * 80)
    for key, value in checklist['page1'].items():
        print(f"  • {key.replace('_', ' ').title()}: {value}")
    
    print()
    print("📋 PAGE 2 - CHARACTER & VERIFICATION")
    print("-" * 80)
    for key, value in checklist['page2'].items():
        print(f"  • {key.replace('_', ' ').title()}: {value}")
    
    print()
    print("📋 PAGE 3 - FINANCIAL ANALYSIS")
    print("-" * 80)
    for key, value in checklist['page3'].items():
        print(f"  • {key.replace('_', ' ').title()}: {value}")
    
    print()
    print("📋 RECOMMENDATION")
    print("-" * 80)
    print(f"  • {checklist['recommendation']}")
    
    print()
    print("=" * 80)
    print("✅ YES! All 3 pages of CI checklist are included!")
    print("=" * 80)
else:
    print("No applications with CI checklist data found")

conn.close()
