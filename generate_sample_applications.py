#!/usr/bin/env python3
"""
Generate 50 realistic loan applications with complete workflow data
LPS → CI/BI → Loan Officer (approved/disapproved/deferred)
"""

import random
from datetime import datetime, timedelta
from database import get_db
import json

# Philippine names database
FIRST_NAMES = [
    'Maria', 'Jose', 'Juan', 'Ana', 'Pedro', 'Rosa', 'Antonio', 'Carmen', 'Francisco', 'Teresa',
    'Manuel', 'Luz', 'Ricardo', 'Elena', 'Roberto', 'Sofia', 'Miguel', 'Isabel', 'Carlos', 'Patricia',
    'Fernando', 'Gloria', 'Rafael', 'Angelica', 'Eduardo', 'Cristina', 'Ramon', 'Beatriz', 'Luis', 'Margarita',
    'Jorge', 'Rosario', 'Alfredo', 'Dolores', 'Ernesto', 'Pilar', 'Raul', 'Mercedes', 'Sergio', 'Concepcion',
    'Alberto', 'Remedios', 'Enrique', 'Esperanza', 'Arturo', 'Felicidad', 'Rodrigo', 'Milagros', 'Domingo', 'Victoria'
]

LAST_NAMES = [
    'Santos', 'Reyes', 'Cruz', 'Bautista', 'Ocampo', 'Garcia', 'Mendoza', 'Torres', 'Gonzales', 'Lopez',
    'Ramos', 'Flores', 'Rivera', 'Gomez', 'Fernandez', 'Dela Cruz', 'Villanueva', 'Castillo', 'Aquino', 'Morales',
    'Valdez', 'Santiago', 'Pascual', 'Mercado', 'Aguilar', 'Navarro', 'Diaz', 'Salazar', 'Hernandez', 'Castro',
    'Jimenez', 'Rojas', 'Alvarez', 'Romero', 'Gutierrez', 'Alonso', 'Vargas', 'Chavez', 'Perez', 'Sanchez',
    'Ramirez', 'Herrera', 'Medina', 'Ortiz', 'Ruiz', 'Molina', 'Delgado', 'Moreno', 'Suarez', 'Ortega'
]

BARANGAYS = [
    'Poblacion', 'San Isidro', 'San Jose', 'Santa Cruz', 'San Antonio', 'San Pedro', 'San Miguel',
    'Santo Niño', 'San Vicente', 'San Rafael', 'San Roque', 'Santa Maria', 'San Juan', 'San Pablo',
    'San Francisco', 'Santa Rosa', 'San Nicolas', 'San Agustin', 'San Luis', 'Santa Ana'
]

MUNICIPALITIES = [
    'Dumaguete City', 'Bais City', 'Canlaon City', 'Tanjay City', 'Guihulngan City',
    'Sibulan', 'Valencia', 'Bacong', 'Dauin', 'Zamboanguita', 'Sta. Catalina', 'Tayasan',
    'Jimalalud', 'La Libertad', 'Manjuyod', 'Bindoy', 'Ayungon', 'Basay', 'Bayawan'
]

LOAN_TYPES = [
    'Agricultural w/o Collateral', 'Agricultural with Chattel', 'Agricultural with REM',
    'Business w/o Collateral', 'Business with Chattel', 'Business with REM',
    'Multipurpose w/o Collateral', 'Multipurpose with Chattel', 'Multipurpose with REM',
    'Salary ATM - Dim', 'Salary MOA - Dim', 'Car Loan - Dim (surplus)', 'Car Loan (Brand New) - Dim',
    'Back-to-back Loan', 'Pension Loan', 'Hospitalization Loan', 'Petty Cash Loan', 'Incentive Loan'
]

OCCUPATIONS = [
    'Farmer', 'Fisherman', 'Teacher', 'Government Employee', 'Business Owner', 'Vendor',
    'Driver', 'Construction Worker', 'Nurse', 'Security Guard', 'Sales Agent', 'Mechanic',
    'Electrician', 'Carpenter', 'Tailor', 'Baker', 'Cook', 'Waiter', 'Cashier', 'Clerk'
]

LOAN_PURPOSES = {
    'Agricultural': ['Farm expansion', 'Purchase of farm equipment', 'Livestock purchase', 'Fertilizer and seeds', 'Irrigation system'],
    'Business': ['Business capital', 'Inventory purchase', 'Equipment upgrade', 'Store renovation', 'Franchise fee'],
    'Multipurpose': ['Home improvement', 'Medical expenses', 'Education', 'Debt consolidation', 'Emergency expenses'],
    'Salary': ['Personal expenses', 'Bills payment', 'Home appliances', 'Gadgets', 'Vacation'],
    'Car': ['Vehicle purchase', 'Down payment for car', 'Car repair', 'Vehicle upgrade'],
    'Other': ['Medical emergency', 'Tuition fee', 'House repair', 'Wedding expenses', 'Funeral expenses']
}

CI_FINDINGS = [
    'Applicant has stable income source. Property verified and in good condition.',
    'Business is operational with good customer base. Financial capacity confirmed.',
    'Applicant has good credit history. Collateral value matches loan amount.',
    'Income documents verified. Character references are positive.',
    'Property inspection completed. Market value assessed at appropriate level.',
    'Business location is strategic. Daily sales records show consistent income.',
    'Applicant is cooperative and transparent. All documents are authentic.',
    'Neighbors confirm good reputation. No adverse findings during investigation.',
    'Employment verified with employer. Salary sufficient for loan repayment.',
    'Collateral is free from liens. Title is clean and authentic.'
]

ADMIN_NOTES_APPROVED = [
    'Application approved. All requirements complete and verified.',
    'Loan granted. Applicant meets all criteria for approval.',
    'Approved based on CI recommendation and complete documentation.',
    'Application approved. Good credit standing and sufficient collateral.',
    'Loan approved. Applicant has proven capacity to pay.',
]

ADMIN_NOTES_DISAPPROVED = [
    'Insufficient collateral value. Application disapproved.',
    'Incomplete requirements. Unable to verify income source.',
    'Credit history shows delinquency. Application denied.',
    'Property has existing liens. Cannot approve at this time.',
    'Income insufficient for requested loan amount. Disapproved.',
]

ADMIN_NOTES_DEFERRED = [
    'Pending additional documents. Application deferred.',
    'Awaiting property title verification. Decision deferred.',
    'Need updated income documents. Application on hold.',
    'Collateral appraisal pending. Decision deferred.',
    'Awaiting co-maker documents. Application deferred.',
]

def generate_phone():
    """Generate Philippine mobile number"""
    return f"09{random.randint(100000000, 999999999)}"

def generate_address():
    """Generate Philippine address"""
    barangay = random.choice(BARANGAYS)
    municipality = random.choice(MUNICIPALITIES)
    return f"Brgy. {barangay}, {municipality}, Negros Oriental"

def generate_name():
    """Generate Filipino name"""
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"

def generate_ci_checklist():
    """Generate realistic CI checklist data"""
    checklist = {
        'page1': {
            'applicant_name': '',
            'loan_amount': '',
            'purpose': '',
            'residence_type': random.choice(['Owned', 'Rented', 'Living with relatives']),
            'years_residing': str(random.randint(1, 30)),
            'household_members': str(random.randint(2, 8)),
            'occupation': random.choice(OCCUPATIONS),
            'monthly_income': str(random.randint(8000, 50000)),
            'other_income': str(random.randint(0, 15000)),
        },
        'page2': {
            'character_rating': random.choice(['Excellent', 'Good', 'Fair']),
            'payment_history': random.choice(['No previous loans', 'Good payment record', 'Has existing loan']),
            'neighbors_feedback': random.choice(['Positive', 'Very positive', 'Neutral']),
            'business_verification': random.choice(['Verified operational', 'Confirmed active', 'N/A']),
        },
        'page3': {
            'total_assets': str(random.randint(100000, 2000000)),
            'total_liabilities': str(random.randint(0, 500000)),
            'net_worth': str(random.randint(50000, 1500000)),
            'monthly_expenses': str(random.randint(5000, 30000)),
            'debt_to_income_ratio': f"{random.randint(20, 60)}%",
        },
        'recommendation': random.choice(['Highly recommended for approval', 'Recommended for approval', 'Approved with conditions'])
    }
    return json.dumps(checklist)

def generate_lps_remarks():
    """Generate LPS remarks"""
    remarks = [
        'Applicant is a regular member in good standing. All documents submitted are complete.',
        'Member has been with the cooperative for several years. No adverse records.',
        'Application documents verified and found to be in order. Member is cooperative.',
        'All required documents submitted. Member expressed willingness to comply with terms.',
        'Member has good relationship with the cooperative. Documents are authentic.',
        'Applicant provided all necessary information. Very cooperative during interview.',
        'Member is known in the community. Has good reputation and character.',
        'Documents submitted are complete and properly filled out. Member is reliable.',
    ]
    return random.choice(remarks)

def generate_applications():
    print("=" * 80)
    print("GENERATING 50 SAMPLE LOAN APPLICATIONS")
    print("=" * 80)
    print()
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get user IDs
    cursor.execute("SELECT id FROM users WHERE role = 'loan_staff' LIMIT 1")
    lps_user = cursor.fetchone()
    lps_id = lps_user['id'] if hasattr(lps_user, 'keys') else lps_user[0]
    
    cursor.execute("SELECT id FROM users WHERE role = 'ci_staff' LIMIT 1")
    ci_user = cursor.fetchone()
    ci_id = ci_user['id'] if hasattr(ci_user, 'keys') else ci_user[0]
    
    print(f"✓ LPS User ID: {lps_id}")
    print(f"✓ CI User ID: {ci_id}")
    print()
    
    # Generate applications with different statuses
    statuses = (
        ['approved'] * 25 +  # 25 approved
        ['disapproved'] * 10 +  # 10 disapproved
        ['deferred'] * 8 +  # 8 deferred
        ['ci_completed'] * 5 +  # 5 pending admin review
        ['assigned_to_ci'] * 2  # 2 pending CI
    )
    
    random.shuffle(statuses)
    
    created_count = 0
    
    for i, status in enumerate(statuses, 1):
        try:
            # Generate application data
            name = generate_name()
            phone = generate_phone()
            address = generate_address()
            loan_type = random.choice(LOAN_TYPES)
            
            # Determine loan amount based on type
            if 'Petty Cash' in loan_type:
                loan_amount = random.randint(5000, 20000)
            elif 'Salary' in loan_type or 'Hospitalization' in loan_type:
                loan_amount = random.randint(10000, 50000)
            elif 'Car Loan' in loan_type:
                loan_amount = random.randint(200000, 800000)
            elif 'REM' in loan_type:
                loan_amount = random.randint(100000, 500000)
            else:
                loan_amount = random.randint(20000, 300000)
            
            # Generate timestamps
            days_ago = random.randint(1, 90)
            submitted_at = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            
            # Base application data
            app_data = {
                'member_name': name,
                'member_contact': phone,
                'member_address': address,
                'loan_amount': loan_amount,
                'loan_type': loan_type,
                'status': status,
                'submitted_by': lps_id,
                'submitted_at': submitted_at,
                'lps_remarks': generate_lps_remarks()
            }
            
            # Add CI data if status is beyond assigned_to_ci
            if status in ['ci_completed', 'approved', 'disapproved', 'deferred']:
                ci_days_ago = days_ago - random.randint(1, 5)
                app_data.update({
                    'assigned_ci_staff': ci_id,
                    'ci_completed_at': (datetime.now() - timedelta(days=ci_days_ago)).strftime('%Y-%m-%d %H:%M:%S'),
                    'ci_notes': random.choice(CI_FINDINGS),
                    'ci_checklist_data': generate_ci_checklist(),
                    'ci_latitude': 9.3000 + random.uniform(-0.1, 0.1),  # Negros Oriental coordinates
                    'ci_longitude': 123.3000 + random.uniform(-0.1, 0.1),
                })
            elif status == 'assigned_to_ci':
                app_data['assigned_ci_staff'] = ci_id
            
            # Add admin decision if final status
            if status in ['approved', 'disapproved', 'deferred']:
                admin_days_ago = ci_days_ago - random.randint(1, 3)
                if status == 'approved':
                    admin_note = random.choice(ADMIN_NOTES_APPROVED)
                elif status == 'disapproved':
                    admin_note = random.choice(ADMIN_NOTES_DISAPPROVED)
                else:
                    admin_note = random.choice(ADMIN_NOTES_DEFERRED)
                
                app_data.update({
                    'admin_notes': admin_note,
                    'admin_decision_at': (datetime.now() - timedelta(days=admin_days_ago)).strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # Insert application
            columns = ', '.join(app_data.keys())
            placeholders = ', '.join(['?'] * len(app_data))  # SQLite uses ?
            query = f"INSERT INTO loan_applications ({columns}) VALUES ({placeholders})"
            
            cursor.execute(query, tuple(app_data.values()))
            conn.commit()
            
            created_count += 1
            status_emoji = {
                'approved': '✅',
                'disapproved': '❌',
                'deferred': '⏸️',
                'ci_completed': '📋',
                'assigned_to_ci': '🔍'
            }
            print(f"{status_emoji.get(status, '📝')} {i}. {name} - {loan_type} - ₱{loan_amount:,} - {status.upper()}")
            
        except Exception as e:
            print(f"❌ Error creating application {i}: {e}")
            conn.rollback()
    
    conn.close()
    
    print()
    print("=" * 80)
    print(f"✅ SUCCESSFULLY CREATED {created_count} APPLICATIONS!")
    print("=" * 80)
    print()
    print("📊 BREAKDOWN:")
    print(f"   • 25 Approved applications")
    print(f"   • 10 Disapproved applications")
    print(f"   • 8 Deferred applications")
    print(f"   • 5 Pending admin review (CI completed)")
    print(f"   • 2 Pending CI investigation")
    print()
    print("🎉 Your database now has realistic sample data!")
    print()

if __name__ == '__main__':
    generate_applications()
