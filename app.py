# IMPORTANT: eventlet monkey_patch must be called FIRST before any other imports
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, send_from_directory, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_socketio import SocketIO, emit, join_room
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, get_database_type  # Use database abstraction layer
import os
import uuid
import re
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
import resend
import requests  # For SMS API

# Load environment variables
load_dotenv()

# Always store UTC - JS will convert to local time for display
def now_ph():
    """Return current UTC time for DB storage (JS handles timezone display)"""
    return datetime.utcnow()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'replace-this-with-a-secure-random-secret')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SIGNATURE_FOLDER'] = 'signatures'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app.config['WTF_CSRF_ENABLED'] = False  # Disabled for now - enable after testing
app.config['WTF_CSRF_TIME_LIMIT'] = None  # CSRF tokens don't expire
app.config['WTF_CSRF_CHECK_DEFAULT'] = False  # Disabled for now
app.config['REMEMBER_COOKIE_DURATION'] = __import__('datetime').timedelta(days=30)
app.config['PERMANENT_SESSION_LIFETIME'] = __import__('datetime').timedelta(hours=2)  # Session expires after 2 hours of inactivity
app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes
app.config['SESSION_COOKIE_SECURE'] = True  # Only send cookie over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# Allowed file extensions for uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'webm', 'mp3', 'wav'}

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Import secure routing module
from secure_routes import SecureRouter, require_token

# Initialize Rate Limiter - 50 requests per minute
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["50 per minute"],
    storage_uri="memory://"
)

# Configure Resend
resend.api_key = os.getenv('RESEND_API_KEY')

# Add template helper function
@app.context_processor
def utility_processor():
    from flask_wtf.csrf import generate_csrf
    
    def get_user_by_id(user_id):
        if not user_id:
            return None
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
        conn.close()
        return user
    
    def secure_token(resource_type, resource_id):
        """Generate a secure token for hiding IDs in URLs"""
        return SecureRouter.generate_token(resource_type, resource_id)
    
    def csrf_token():
        """Generate CSRF token for forms"""
        return generate_csrf()

    # Inject unread message count into every template automatically
    message_unread_count = 0
    try:
        from flask_login import current_user as _cu
        if _cu.is_authenticated:
            conn = get_db()
            row = conn.execute('''
                SELECT COUNT(*) as count FROM direct_messages
                WHERE receiver_id = ? AND is_read = 0
            ''', (_cu.id,)).fetchone()
            conn.close()
            message_unread_count = row['count'] if row else 0
    except Exception:
        pass

    return dict(
        get_user_by_id=get_user_by_id, 
        message_unread_count=message_unread_count,
        secure_token=secure_token,
        csrf_token=csrf_token
    )

socketio = SocketIO(
    app,
    cors_allowed_origins="*",  # Allow all origins - authentication handles security
    async_mode='threading',   # Use threading for instant emit
    ping_timeout=60,
    ping_interval=10,  # Faster ping (was 25) for quicker detection
    logger=False,
    engineio_logger=False,
    always_connect=True,  # Maintain persistent connections
    manage_session=False  # Let Flask-Login handle sessions
)

# Track online users
online_users = {}  # {user_id: {'name': name, 'role': role, 'last_seen': timestamp}}

# Serve static files for PWA
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Serve favicon directly at /favicon.ico
@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static/images', 'logo.jpg', mimetype='image/jpeg')

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Database is now managed by database.py - supports both SQLite and PostgreSQL

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_password_strength(password):
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"

def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal"""
    filename = secure_filename(filename)
    # Remove any remaining path separators
    filename = filename.replace('/', '').replace('\\', '')
    return filename

class User(UserMixin):
    def __init__(self, id, email, name, role, signature_path=None, backup_email=None, profile_photo=None, assigned_route=None, permissions=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.signature_path = signature_path
        self.backup_email = backup_email
        self.profile_photo = profile_photo
        self.assigned_route = assigned_route
        self.permissions = permissions

def send_verification_email(to_email, code, user_name):
    """Send verification code email using Resend"""
    try:
        from_email = os.getenv('RESEND_FROM_EMAIL', 'onboarding@resend.dev')
        
        params = {
            "from": from_email,
            "to": [to_email],
            "subject": "Password Reset Verification Code - DCCCO",
            "html": f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f7fa;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <div style="text-align: center; margin-bottom: 30px;">
                            <h2 style="color: #1e3a5f; margin: 0;">DCCCO Multipurpose Cooperative</h2>
                            <p style="color: #666; margin: 5px 0;">Loan Management System</p>
                        </div>
                        
                        <h3 style="color: #1e3a5f;">Hello {user_name},</h3>
                        
                        <p style="color: #333; line-height: 1.6;">
                            You requested to reset your password. Use the verification code below to continue:
                        </p>
                        
                        <div style="background: #f8f9fa; border-left: 4px solid #1e3a5f; padding: 20px; margin: 20px 0; text-align: center;">
                            <p style="margin: 0; color: #666; font-size: 14px;">Your Verification Code</p>
                            <h1 style="margin: 10px 0; color: #1e3a5f; font-size: 36px; letter-spacing: 5px;">{code}</h1>
                            <p style="margin: 0; color: #999; font-size: 12px;">Valid for 15 minutes</p>
                        </div>
                        
                        <p style="color: #333; line-height: 1.6;">
                            If you didn't request this password reset, please ignore this email or contact support if you have concerns.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                        
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            This is an automated message, please do not reply to this email.
                        </p>
                    </div>
                </body>
            </html>
            """
        }
        
        response = resend.Emails.send(params)
        return True
    except Exception as e:
        error_msg = str(e)
        
        # Check if it's the Resend testing limitation
        if "You can only send testing emails" in error_msg:
            # Return a special error code
            return "RESEND_LIMIT"
        
        import traceback
        traceback.print_exc()
        return False

# Removed old get_db() function - now using database.py

def has_permission(user, permission):
    """Check if user has specific permission"""
    if user.role == 'admin':
        return True  # Super admin has all permissions
    if user.role == 'loan_officer':
        if hasattr(user, 'permissions') and user.permissions:
            return permission in user.permissions
    return False

def init_db():
    """Initialize database if it doesn't exist (SQLite only - PostgreSQL uses migrations)"""
    db_type = get_database_type()
    
    if db_type == 'postgresql':
        # PostgreSQL is already initialized via migration
        print("📊 Using PostgreSQL - database already initialized")
        os.makedirs('uploads', exist_ok=True)
        os.makedirs('signatures', exist_ok=True)
        return
    
    # SQLite initialization
    if not os.path.exists('app.db'):
        print("📊 Initializing SQLite database...")
        conn = get_db()
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())
        
        # Create demo users (all approved by default)
        from werkzeug.security import generate_password_hash
        admin_hash = generate_password_hash('admin123')
        loan_hash = generate_password_hash('loan123')
        ci_hash = generate_password_hash('ci123')
        
        conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
                     ('admin@dccco.test', admin_hash, 'Admin User', 'admin', 1))
        conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
                     ('loan@dccco.test', loan_hash, 'Loan Staff', 'loan_staff', 1))
        conn.execute('INSERT INTO users (email, password_hash, name, role, is_approved) VALUES (?, ?, ?, ?, ?)',
                     ('ci@dccco.test', ci_hash, 'CI Staff', 'ci_staff', 1))
        
        conn.commit()
        conn.close()
        print("✓ SQLite database initialized")
        
    # Create directories
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('signatures', exist_ok=True)

# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"⚠️  Database initialization warning: {e}")
    print("⚠️  Continuing app startup...")

# Setup production users (runs on every startup to ensure correct roles)
def setup_production_users():
    """Create or update default users"""
    try:
        conn = get_db()
        from werkzeug.security import generate_password_hash
        
        users = [
            ('superadmin@dccco.test', 'admin@2024', 'Super Admin', 'admin'),
            ('admin@dccco.test', 'admin123', 'Loan Officer', 'loan_officer'),
            ('ci@dccco.test', 'ci123', 'CI Staff', 'ci_staff'),
            ('loan@dccco.test', 'loan123', 'Loan Staff', 'loan_staff')
        ]
        
        for email, password, name, role in users:
            try:
                existing = conn.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
                
                if existing:
                    # Update existing user's name and role
                    conn.execute('UPDATE users SET name = ?, role = ?, is_approved = 1 WHERE email = ?',
                               (name, role, email))
                else:
                    # Create new user
                    password_hash = generate_password_hash(password)
                    conn.execute('''
                        INSERT INTO users (email, password_hash, name, role, is_approved)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (email, password_hash, name, role))
            except Exception as user_error:
                print(f"⚠️  User setup warning for {email}: {user_error}")
                continue
        
        conn.commit()
        print("✓ Production users setup complete")
        
        # Setup default loan types if table is empty
        try:
            count = conn.execute('SELECT COUNT(*) as count FROM loan_types').fetchone()
            if count and count['count'] == 0:
                print("Setting up default DCCCO loan types...")
                loan_types = [
                    ('Agricultural with Chattel', 'Agricultural loan with chattel mortgage', 1),
                    ('Agricultural with REM', 'Agricultural loan with real estate mortgage', 1),
                    ('Agricultural w/o Collateral', 'Agricultural loan without collateral', 1),
                    ('Business with Chattel', 'Business loan with chattel mortgage', 1),
                    ('Business with REM', 'Business loan with real estate mortgage', 1),
                    ('Business w/o Collateral', 'Business loan without collateral', 1),
                    ('Multipurpose with Chattel', 'Multipurpose loan with chattel mortgage', 1),
                    ('Multipurpose with REM', 'Multipurpose loan with real estate mortgage', 1),
                    ('Multipurpose w/o Collateral', 'Multipurpose loan without collateral', 1),
                    ('Salary ATM - Dim', 'Salary loan via ATM', 1),
                    ('Salary MOA - Dim', 'Salary loan via MOA', 1),
                    ('Car Loan - Dim (surplus)', 'Car loan for surplus vehicles', 1),
                    ('Car Loan (Brand New) - Dim', 'Car loan for brand new vehicles', 1),
                    ('Back-to-back Loan', 'Back-to-back loan', 1),
                    ('Pension Loan', 'Pension loan', 1),
                    ('Hospitalization Loan', 'Hospitalization loan', 1),
                    ('Petty Cash Loan', 'Petty cash loan', 1),
                    ('Incentive Loan', 'Incentive loan', 1)
                ]
                
                for loan_name, description, is_active in loan_types:
                    try:
                        conn.execute('''
                            INSERT INTO loan_types (loan_name, description, is_active)
                            VALUES (?, ?, ?)
                        ''', (loan_name, description, is_active))
                    except Exception as loan_error:
                        print(f"⚠️  Loan type warning for {loan_name}: {loan_error}")
                        continue
                
                conn.commit()
                print(f"✓ Created {len(loan_types)} default loan types")
        except Exception as loan_types_error:
            print(f"⚠️  Loan types setup warning: {loan_types_error}")
        
        # Setup default system settings if table is empty
        try:
            count = conn.execute('SELECT COUNT(*) as count FROM system_settings').fetchone()
            if count and count['count'] == 0:
                print("Setting up default system settings...")
                settings = [
                    ('company_name', 'DCCCO Multipurpose Cooperative', 'Company name displayed in the system'),
                    ('max_loan_amount', '500000', 'Maximum loan amount allowed'),
                    ('min_loan_amount', '5000', 'Minimum loan amount allowed'),
                    ('default_interest_rate', '12', 'Default annual interest rate (%)'),
                    ('ci_required_threshold', '50000', 'Loan amount threshold requiring CI')
                ]
                
                for key, value, description in settings:
                    try:
                        conn.execute('''
                            INSERT INTO system_settings (setting_key, setting_value, description)
                            VALUES (?, ?, ?)
                        ''', (key, value, description))
                    except Exception as setting_error:
                        print(f"⚠️  Setting warning for {key}: {setting_error}")
                        continue
                
                conn.commit()
                print(f"✓ Created {len(settings)} default system settings")
        except Exception as settings_error:
            print(f"⚠️  System settings setup warning: {settings_error}")
        
        conn.close()
    except Exception as e:
        print(f"⚠️  Setup warning: {e}")
        import traceback
        traceback.print_exc()
        print("⚠️  Continuing app startup despite setup warnings...")

try:
    setup_production_users()
except Exception as e:
    print(f"⚠️  Production users setup failed: {e}")
    print("⚠️  App will continue without default users")

def create_notification(user_id, message, link=None):
    try:
        conn = get_db()
        conn.execute('INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)',
                     (user_id, message, link))
        conn.commit()
        conn.close()
        socketio.emit('new_notification', {'message': message}, room=str(user_id))
    except Exception as e:
        pass

def send_sms(phone_number, message):
    """
    Send SMS using TextBelt (FREE - works immediately, no registration needed)
    Supports INTERNATIONAL phone numbers
    """
    try:
        # Clean phone number (remove spaces, dashes, etc.)
        phone = re.sub(r'[^\d+]', '', phone_number)
        
        # Auto-format Philippine numbers (09xx -> +639xx)
        if phone.startswith('09') and len(phone) == 11:
            phone = '+63' + phone[1:]
        # Ensure + prefix for international format
        elif not phone.startswith('+'):
            # If no country code, assume Philippines
            if len(phone) == 10:
                phone = '+63' + phone
            else:
                phone = '+' + phone
        
        print(f"\n[SMS] Attempting to send to {phone}")
        print(f"[SMS] Message: {message[:50]}...")
        
        # Use TextBelt (FREE - 1 SMS per day per number, works internationally)
        # No registration needed, works immediately!
        try:
            print(f"[SMS] Using TextBelt (FREE, no registration needed)...")
            url = 'https://textbelt.com/text'
            payload = {
                'phone': phone,
                'message': f"DCCCO: {message}",  # Add DCCCO prefix
                'key': 'textbelt'  # Free tier key
            }
            
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            
            print(f"[SMS] TextBelt Response: {result}")
            
            if result.get('success'):
                print(f"✓ SMS sent via TextBelt to {phone}")
                print(f"  Text ID: {result.get('textId', 'N/A')}")
                print(f"  Quota remaining today: {result.get('quotaRemaining', 'N/A')}")
                return True
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"✗ TextBelt failed: {error_msg}")
                
                # If quota exceeded, show helpful message
                if 'quota' in error_msg.lower():
                    print(f"  Note: TextBelt free tier allows 1 SMS per day per number")
                    print(f"  You can get more at https://textbelt.com")
                
                return False
                
        except Exception as e:
            print(f"✗ TextBelt exception: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"✗ SMS error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def build_system_context():
    """
    Build comprehensive system context for AI assistant
    Includes database schema, routes, features, and workflows
    """
    context = """
# DCCCO Loan Management System Documentation

## System Overview
Flask-based loan management system for DCCCO Multipurpose Cooperative with real-time features using Socket.IO.

## User Roles
1. **admin**: Full system access, approves/rejects loans, manages users
2. **loan_staff**: Submits loan applications, assigns to CI staff
3. **ci_staff**: Conducts credit investigations, completes checklists

## Database Schema

### users table
- id, email, password_hash, name, role, is_approved
- signature_path, backup_email, profile_photo
- is_online, last_seen, current_workload

### loan_applications table
- id, member_name, member_contact, member_address, loan_amount
- status: submitted, assigned_to_ci, ci_completed, approved, disapproved
- needs_ci_interview, submitted_by, assigned_ci_staff
- ci_notes, ci_checklist_data, ci_signature, ci_completed_at
- admin_notes, admin_decision_at, submitted_at

### documents table
- id, loan_application_id, file_name, file_path, uploaded_by, uploaded_at

### direct_messages table
- id, sender_id, receiver_id, message, sent_at, is_read, is_edited, is_deleted

### notifications table
- id, user_id, message, link, is_read, created_at

### location_tracking table
- id, user_id, latitude, longitude, activity, tracked_at

## Key Features

### Loan Application Workflow
1. Loan staff submits application via /loan/submit
2. System auto-assigns to CI staff with lowest workload
3. CI staff completes interview and checklist
4. Admin reviews and approves/rejects
5. SMS notification sent to applicant

### Real-Time Messaging
- Direct messages between users via Socket.IO
- Application-specific messaging threads
- Typing indicators and read receipts
- Voice message support

### CI Tracking
- GPS location tracking for CI staff
- Real-time map display for admin
- Activity status updates

### User Management
- Admin approves new user registrations
- Role-based access control
- Password reset with email verification

### Dark Mode
- Toggle via localStorage
- Applies to all pages
- CSS variables for theming

## Common Issues & Solutions

### Issue: User not approved
**Solution**: Admin must approve via /manage_users

### Issue: CI staff not receiving assignments
**Solution**: Check current_workload in users table, verify is_approved=1

### Issue: SMS not sending
**Solution**: Check SEMAPHORE_API_KEY or TEXTBELT_API_KEY in .env

### Issue: Real-time features not working
**Solution**: Verify Socket.IO connection, check browser console for errors

### Issue: File upload failing
**Solution**: Check UPLOAD_FOLDER permissions, verify file extension in ALLOWED_EXTENSIONS

## File Structure
- app.py: Main Flask application
- templates/: HTML templates (Jinja2)
- static/: CSS, JavaScript, images
- uploads/: User-uploaded documents
- signatures/: Digital signatures
- schema.sql: Database schema

## Environment Variables
- SECRET_KEY: Flask session secret
- RESEND_API_KEY: Email service
- SEMAPHORE_API_KEY: SMS service (primary)
- OPENAI_API_KEY or ANTHROPIC_API_KEY: AI assistant
- FLASK_DEBUG: Debug mode flag

## API Endpoints
- /api/send_direct_message: Send message
- /api/update_location: Update CI location
- /api/unread_message_count: Get unread count
- /api/ai_query: AI assistant query (admin only)
"""
    return context


def call_ai_engine(query, history, context):
    """
    Call AI API with system context and conversation history
    Supports OpenAI and Anthropic APIs
    """
    # Get API key from environment
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not openai_key and not anthropic_key:
        raise Exception('No AI API key configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file.')
    
    # Build messages array
    messages = []
    
    # Add conversation history
    for msg in history:
        messages.append({
            'role': msg['role'],
            'content': msg['content']
        })
    
    # Add current query
    messages.append({'role': 'user', 'content': query})
    
    # Call OpenAI API (preferred)
    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            
            # Build system message with context
            system_message = f"""You are DaisyandCoco, an AI assistant for the DCCCO Multipurpose Cooperative loan management system.

You help administrators understand and troubleshoot the system.

SYSTEM KNOWLEDGE:
{context}

Provide clear, accurate, and helpful responses. Use bullet points and code examples when appropriate.
Reference specific file paths, database tables, and functions when relevant.
Be friendly and conversational while maintaining professionalism."""
            
            response = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {'role': 'system', 'content': system_message}
                ] + messages,
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            app.logger.error(f"OpenAI API error: {str(e)}")
            raise Exception(f"AI service error: {str(e)}")
    
    # Fallback to Anthropic API
    elif anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            
            # Build system message with context
            system_message = f"""You are DaisyandCoco, an AI assistant for the DCCCO Multipurpose Cooperative loan management system.

You help administrators understand and troubleshoot the system.

SYSTEM KNOWLEDGE:
{context}

Provide clear, accurate, and helpful responses. Use bullet points and code examples when appropriate.
Reference specific file paths, database tables, and functions when relevant.
Be friendly and conversational while maintaining professionalism."""
            
            response = client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=1000,
                system=system_message,
                messages=messages
            )
            return response.content[0].text
        except Exception as e:
            app.logger.error(f"Anthropic API error: {str(e)}")
            raise Exception(f"AI service error: {str(e)}")


@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    if row:
        backup_email = row['backup_email'] if 'backup_email' in row.keys() else None
        profile_photo = row['profile_photo'] if 'profile_photo' in row.keys() else None
        assigned_route = row['assigned_route'] if 'assigned_route' in row.keys() else None
        permissions = row['permissions'] if 'permissions' in row.keys() else None
        return User(row['id'], row['email'], row['name'], row['role'], row['signature_path'], backup_email, profile_photo, assigned_route, permissions)
    return None

# Add security headers to prevent caching of authenticated pages
@app.after_request
def add_security_headers(response):
    # Prevent caching for authenticated users
    if current_user.is_authenticated:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# Helper functions for role-based access control
def is_admin():
    """Check if current user is super admin"""
    return current_user.is_authenticated and current_user.role == 'admin'

def is_loan_officer():
    """Check if current user is loan officer"""
    return current_user.is_authenticated and current_user.role == 'loan_officer'

def is_admin_or_loan_officer():
    """Check if current user is admin or loan officer"""
    return current_user.is_authenticated and current_user.role in ['admin', 'loan_officer']

def require_admin():
    """Decorator to require admin role"""
    if not is_admin():
        flash('Unauthorized - Admin access required', 'danger')
        return redirect(url_for('index'))

def require_admin_or_loan_officer():
    """Decorator to require admin or loan officer role"""
    if not is_admin_or_loan_officer():
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role in ['admin', 'loan_officer']:
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'loan_staff':
            return redirect(url_for('loan_dashboard'))
        else:
            return redirect(url_for('ci_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        conn.close()
        if row and check_password_hash(row['password_hash'], password):
            # Check if user is approved
            if row['is_approved'] == 0:
                flash('Your account is pending admin approval. Please wait.', 'warning')
                return render_template('login.html')
            
            user = User(row['id'], row['email'], row['name'], row['role'], row['signature_path'], 
                       row['backup_email'] if 'backup_email' in row.keys() else None,
                       row['profile_photo'] if 'profile_photo' in row.keys() else None)
            login_user(user, remember=False)  # Session expires when browser closes
            session.permanent = False  # Ensure session is not permanent
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # Clear AI chat history from session
    if 'ai_chat_history' in session:
        session.pop('ai_chat_history', None)
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))

# LOAN STAFF ROUTES
@app.route('/loan/dashboard')
@login_required
def loan_dashboard():
    if current_user.role != 'loan_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    conn = get_db()
    applications = conn.execute('''
        SELECT la.*, u.name as ci_staff_name 
        FROM loan_applications la
        LEFT JOIN users u ON la.assigned_ci_staff = u.id
        ORDER BY la.submitted_at ASC
    ''').fetchall()
    
    # Get all CI staff for the dropdown
    ci_staff_list = conn.execute('''
        SELECT id, name, email 
        FROM users 
        WHERE role='ci_staff' 
        ORDER BY name ASC
    ''').fetchall()
    
    # Fixed: Handle None case when no notifications exist
    unread_count_row = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''', 
                                (current_user.id,)).fetchone()
    unread_count = unread_count_row['count'] if unread_count_row else 0
    conn.close()
    return render_template('loan_dashboard.html', applications=applications, unread_count=unread_count, ci_staff_list=ci_staff_list)

@app.route('/notifications/count')
@login_required
def notification_count():
    conn = get_db()
    # Fixed: Handle None case when no notifications exist
    count_row = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''', 
                        (current_user.id,)).fetchone()
    count = count_row['count'] if count_row else 0
    conn.close()
    return jsonify({'count': count})

@app.route('/loan/update_status/<int:app_id>', methods=['POST'])
@login_required
def update_application_status(app_id):
    if current_user.role != 'loan_staff':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    conn = get_db()
    conn.execute('UPDATE loan_applications SET status=? WHERE id=?', (new_status, app_id))
    conn.commit()
    
    # Get application details for real-time update
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (app_id,)).fetchone()
    conn.close()
    
    # Emit real-time update to all connected dashboards
    socketio.emit('application_updated', {
        'id': app_id,
        'status': new_status,
        'member_name': app_data['member_name'] if app_data else '',
        'loan_amount': float(app_data['loan_amount']) if app_data else 0,
        'timestamp': now_ph().isoformat()
    })
    
    return jsonify({'success': True})

@app.route('/loan/update_ci_staff/<int:app_id>', methods=['POST'])
@login_required
def update_ci_staff_assignment(app_id):
    if current_user.role != 'loan_staff':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    ci_staff_id = data.get('ci_staff_id')
    
    conn = get_db()
    if ci_staff_id:
        conn.execute('UPDATE loan_applications SET assigned_ci_staff=?, status=? WHERE id=?', 
                    (ci_staff_id, 'assigned_to_ci', app_id))
        # Send notification to CI staff
        create_notification(int(ci_staff_id), 
                          f'New loan application assigned to you',
                          f'/ci/application/{app_id}')
    else:
        conn.execute('UPDATE loan_applications SET assigned_ci_staff=NULL WHERE id=?', (app_id,))
    
    conn.commit()
    
    # Get application details for real-time update
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (app_id,)).fetchone()
    conn.close()
    
    # Emit real-time update to all connected dashboards
    socketio.emit('application_updated', {
        'id': app_id,
        'status': 'assigned_to_ci' if ci_staff_id else app_data['status'],
        'member_name': app_data['member_name'] if app_data else '',
        'loan_amount': float(app_data['loan_amount']) if app_data else 0,
        'ci_staff_id': ci_staff_id,
        'timestamp': now_ph().isoformat()
    })
    
    return jsonify({'success': True})

@app.route('/loan/submit', methods=['GET','POST'])
@login_required
def submit_application():
    if current_user.role != 'loan_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            member_name = request.form['member_name']
            member_contact = request.form.get('member_contact')
            member_address = request.form.get('member_address')
            loan_amount = request.form.get('loan_amount')
            loan_type = request.form.get('loan_type')
            lps_remarks = request.form.get('lps_remarks', '').strip()
            needs_ci_value = request.form.get('needs_ci', '1')
            
            print(f"DEBUG: Submitting application - Name: {member_name}, Amount: {loan_amount}")
            
            conn = get_db()
            
            # Check for duplicate member name
            existing = conn.execute('''
                SELECT id, member_name FROM loan_applications 
                WHERE LOWER(member_name) = LOWER(?) 
                AND status NOT IN ('disapproved', 'approved')
            ''', (member_name,)).fetchone()
            
            if existing:
                conn.close()
                flash(f'An active application for "{member_name}" already exists (ID: #{existing["id"]}). Please complete or disapprove the existing application first.', 'warning')
                return redirect(url_for('submit_application'))
            
            # Check if specific CI staff was selected
            specific_ci_id = None
            if needs_ci_value.startswith('ci_'):
                specific_ci_id = int(needs_ci_value.replace('ci_', ''))
                needs_ci = 1
            else:
                needs_ci = int(needs_ci_value)
        except Exception as e:
            print(f"ERROR in form processing: {str(e)}")
            import traceback
            traceback.print_exc()
            flash(f'Error processing form data: {str(e)}', 'danger')
            return redirect(url_for('submit_application'))
        try:
            print(f"DEBUG: Inserting application into database")
            cursor = conn.execute('''
                INSERT INTO loan_applications 
                (member_name, member_contact, member_address, loan_amount, loan_type, lps_remarks, needs_ci_interview, submitted_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (member_name, member_contact, member_address, loan_amount, loan_type, lps_remarks, needs_ci, current_user.id))
            app_id = cursor.lastrowid
            print(f"DEBUG: Application created with ID: {app_id}")
            
            # Handle file uploads
            if 'documents' in request.files:
                files = request.files.getlist('documents')
                print(f"DEBUG: Processing {len(files)} files")
                for file in files:
                    if file and file.filename:
                        # Validate file extension
                        if not allowed_file(file.filename):
                            conn.rollback()
                            conn.close()
                            flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, PDF, DOC, DOCX', 'danger')
                            return redirect(url_for('submit_application'))
                        
                        filename = sanitize_filename(file.filename)
                        unique_filename = f"{app_id}_{uuid.uuid4().hex[:8]}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        print(f"DEBUG: Saving file to {filepath}")
                        file.save(filepath)
                        conn.execute('INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by) VALUES (?, ?, ?, ?)',
                                   (app_id, filename, filepath, current_user.id))
            
            # Assign to CI staff
            if needs_ci:
                if specific_ci_id:
                    # Assign to specific CI staff
                    ci_staff_id = specific_ci_id
                    print(f"DEBUG: Assigning to specific CI staff: {ci_staff_id}")
                else:
                    # ROUTE-BASED ASSIGNMENT: Match applicant address to CI route
                    ci_staff_id = None
                    
                    # Parse address to find matching route
                    if member_address:
                        address_lower = member_address.lower()
                        
                        # Define route matching logic
                        route_matches = {
                            'route_1_bayawan_kalumboyan': ['kalumboyan', 'kalamtukan', 'malabugas', 'bugay', 'nangka'],
                            'route_2_bayawan_basay': ['basay', 'actin', 'bal-os', 'bongalonan', 'cabalayongan', 'maglinao', 'nagbo-alao', 'olandao'],
                            'route_3_bayawan_sipalay': ['sipalay', 'cabadiangan', 'camindangan', 'canturay', 'cartagena', 'mambaroto', 'maricalum'],
                            'route_4_bayawan_santa_catalina': ['santa catalina', 'alangilan', 'amio', 'buenavista', 'caigangan', 'cawitan', 'manalongon', 'milagrosa', 'obat', 'talalak'],
                            'route_5_bayawan_center': ['ali-is', 'banaybanay', 'banga', 'boyco', 'cansumalig', 'dawis', 'manduao', 'mandu-ao', 'maninihon', 'minaba', 'narra', 'pagatban', 'poblacion', 'san isidro', 'san jose', 'san miguel', 'san roque', 'suba', 'tabuan', 'tayawan', 'tinago', 'ubos', 'villareal', 'villasol'],
                            'route_6_bayawan_omod': ['omod', 'tamisu']
                        }
                        
                        # Find matching route
                        matched_route = None
                        for route_id, keywords in route_matches.items():
                            for keyword in keywords:
                                if keyword in address_lower:
                                    matched_route = route_id
                                    break
                            if matched_route:
                                break
                        
                        # Find CI staff assigned to this route (check if route is in their comma-separated list)
                        if matched_route:
                            ci_staff = conn.execute('''
                                SELECT id, assigned_route FROM users 
                                WHERE role='ci_staff' AND is_approved=1 
                                AND (assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route = ?)
                                LIMIT 1
                            ''', (f'%{matched_route}%,%', f'%,{matched_route}%', f'%,{matched_route},%', matched_route)).fetchone()
                            ci_staff_id = ci_staff['id'] if ci_staff else None
                            print(f"DEBUG: Route-based assignment - Route: {matched_route}, CI: {ci_staff_id}")
                        else:
                            print(f"DEBUG: No matching route found for address: {member_address}")
                    
                    # Fallback to workload-based if no route match
                    if not ci_staff_id:
                        print(f"DEBUG: Falling back to workload-based assignment")
                        ci_staff = conn.execute('''
                            SELECT id FROM users 
                            WHERE role='ci_staff' AND is_approved=1
                            ORDER BY current_workload ASC 
                            LIMIT 1
                        ''').fetchone()
                        ci_staff_id = ci_staff['id'] if ci_staff else None
                        print(f"DEBUG: Workload-based assignment - CI: {ci_staff_id}")
                
                if ci_staff_id:
                    conn.execute('UPDATE loan_applications SET status=?, assigned_ci_staff=? WHERE id=?',
                               ('assigned_to_ci', ci_staff_id, app_id))
                    conn.execute('UPDATE users SET current_workload = current_workload + 1 WHERE id=?',
                               (ci_staff_id,))
                    conn.commit()
                    conn.close()
                    create_notification(ci_staff_id, 
                                      f'New loan application assigned: {member_name}',
                                      f'/ci/application/{app_id}')
                else:
                    conn.commit()
                    conn.close()
            else:
                # Send directly to loan officer
                loan_officer = conn.execute('SELECT id FROM users WHERE role="loan_officer" LIMIT 1').fetchone()
                conn.commit()
                conn.close()
                if loan_officer:
                    create_notification(loan_officer['id'],
                                      f'New loan application submitted: {member_name}',
                                      f'/admin/application/{app_id}')
            
            print(f"DEBUG: Application submitted successfully")
            flash('Application submitted successfully!', 'success')
            
            # Emit WebSocket event for instant dashboard update
            socketio.emit('new_application', {
                'id': app_id,
                'member_name': member_name,
                'status': 'assigned_to_ci' if needs_ci else 'submitted'
            })
            
            return redirect(url_for('loan_dashboard'))
        except Exception as e:
            print(f"ERROR in database operations: {str(e)}")
            import traceback
            traceback.print_exc()
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            flash(f'Error submitting application: {str(e)}', 'danger')
            return redirect(url_for('submit_application'))
    
    conn = get_db()
    # Get all CI staff (both approved and pending)
    ci_staff_list = conn.execute('''
        SELECT id, name, email, is_approved 
        FROM users 
        WHERE role='ci_staff' 
        ORDER BY name ASC
    ''').fetchall()
    
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('submit_application.html', unread_count=unread_count, ci_staff_list=ci_staff_list)

# CI STAFF ROUTES
@app.route('/ci/dashboard')
@login_required
def ci_dashboard():
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    conn = get_db()
    applications = conn.execute('''
        SELECT la.*, u.name as loan_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.submitted_by = u.id
        WHERE la.assigned_ci_staff = ?
        ORDER BY la.submitted_at ASC
    ''', (current_user.id,)).fetchall()
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('ci_dashboard.html', applications=applications, unread_count=unread_count)

@app.route('/ci/checklist/<int:id>', methods=['GET'])
@login_required
def ci_checklist(id):
    """Redirect to checkbox summary page first"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    # Redirect to checkbox summary
    return redirect(url_for('ci_checklist_summary', id=id))


@app.route('/ci/checklist/summary/<int:id>')
@login_required
def ci_checklist_summary(id):
    """CI Checklist Summary - All checkboxes in one page before 5-page wizard"""
    try:
        # Check authorization
        if not hasattr(current_user, 'role'):
            flash('Session error. Please login again.', 'danger')
            return redirect(url_for('login'))
            
        if current_user.role != 'ci_staff':
            flash('Unauthorized access. CI Staff only.', 'danger')
            return redirect(url_for('index'))
        
        conn = get_db()
        
        # Get application data with all fields
        app_data = conn.execute('''
            SELECT 
                la.id,
                la.member_name,
                la.member_contact,
                la.member_address,
                la.loan_amount,
                la.loan_type,
                la.status,
                la.submitted_at,
                la.submitted_by,
                u.name as loan_staff_name
            FROM loan_applications la
            LEFT JOIN users u ON la.submitted_by = u.id
            WHERE la.id=?
        ''', (id,)).fetchone()
        
        if not app_data:
            conn.close()
            flash('Application not found', 'danger')
            return redirect(url_for('ci_dashboard'))
        
        # Convert to dict for easier access
        application = dict(app_data)
        
        # Get unread notifications count safely
        unread_count = 0
        try:
            result = conn.execute('''
                SELECT COUNT(*) as count 
                FROM notifications 
                WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"
            ''', (current_user.id,)).fetchone()
            if result:
                unread_count = result['count']
        except Exception as e:
            print(f"Error getting unread count: {e}")
        
        conn.close()
        
        # Render simple checkbox summary template
        return render_template('ci_checklist_summary_simple.html', 
                             application=application,
                             unread_count=unread_count)
    
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"=== ERROR in ci_checklist_summary ===")
        print(f"Error: {str(e)}")
        print(f"Details: {error_details}")
        print(f"=== END ERROR ===")
        
        flash('An error occurred while loading the page. Please try again.', 'danger')
        
        try:
            return redirect(url_for('ci_dashboard'))
        except:
            return redirect(url_for('index'))


@app.route('/ci/checklist/wizard/<int:id>', methods=['GET'])
@login_required
def ci_checklist_wizard(id):
    """Display the multi-page CI checklist wizard (5 pages)"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    
    if not app_data:
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('ci_dashboard'))
    
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''',
                                (current_user.id,)).fetchone()['count']
    
    conn.close()
    return render_template('ci_checklist_wizard.html', application=app_data, unread_count=unread_count)

@app.route('/ci/application/<int:id>', methods=['GET','POST'])
@login_required
def ci_application(id):
    """Show review page with documents and verification checkboxes"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    # Redirect to review page
    return redirect(url_for('ci_review_application', id=id))

@app.route('/ci/review/<int:id>')
@login_required
def ci_review_application(id):
    """CI Review Page - View documents and verify before interview"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('''
        SELECT la.*, u.name as loan_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.submitted_by = u.id
        WHERE la.id=? AND la.assigned_ci_staff=?
    ''', (id, current_user.id)).fetchone()
    
    if not app_data:
        flash('Application not found or not assigned to you', 'danger')
        conn.close()
        return redirect(url_for('ci_dashboard'))
    
    # Get uploaded documents
    documents = conn.execute('SELECT * FROM documents WHERE loan_application_id=? ORDER BY uploaded_at DESC', (id,)).fetchall()
    
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('ci_review_application.html', 
                         application=app_data, 
                         documents=documents,
                         unread_count=unread_count)


@app.route('/view/checklist/<int:id>')
@login_required
def view_ci_checklist(id):
    """View completed CI checklist (for loan officer/admin)"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    
    if not app_data:
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    # Parse checklist data
    checklist_data = {}
    if app_data['ci_checklist_data']:
        try:
            import json
            checklist_data = json.loads(app_data['ci_checklist_data'])
        except:
            pass
    
    conn.close()
    return render_template('view_ci_checklist.html', application=app_data, checklist_data=checklist_data)

@app.route('/ci/checklist/<int:id>', methods=['POST'])
@login_required
def submit_ci_checklist(id):
    """Submit the completed CI checklist"""
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    
    if not app_data or app_data['assigned_ci_staff'] != current_user.id:
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('ci_dashboard'))
    
    try:
        checklist_data = request.form.get('checklist_data')
        ci_signature = request.form.get('ci_signature')
        ci_latitude = request.form.get('ci_latitude')
        ci_longitude = request.form.get('ci_longitude')
        
        # Use registered signature if not provided
        if not ci_signature:
            if current_user.signature_path:
                # Use the registered signature URL
                ci_signature = url_for('serve_signature', 
                                      filename=current_user.signature_path.split('/')[-1].split('\\')[-1], 
                                      _external=True)
            else:
                flash('Signature is required. Please update your signature in Change Password page.', 'danger')
                conn.close()
                return redirect(url_for('ci_checklist', id=id))
        
        # Update application
        conn.execute('''
            UPDATE loan_applications 
            SET status=?, ci_checklist_data=?, ci_signature=?, ci_completed_at=?, ci_latitude=?, ci_longitude=?
            WHERE id=?
        ''', ('ci_completed', checklist_data, ci_signature, now_ph().isoformat(), ci_latitude, ci_longitude, id))
        
        # Handle interview photo uploads
        if 'interview_photos' in request.files:
            files = request.files.getlist('interview_photos')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_filename = f"{id}_interview_{uuid.uuid4().hex[:8]}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(filepath)
                    conn.execute('INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by) VALUES (?, ?, ?, ?)',
                               (id, filename, filepath, current_user.id))
        
        # Update workload
        conn.execute('UPDATE users SET current_workload = current_workload - 1 WHERE id=?', (current_user.id,))
        conn.commit()
        
        # Emit real-time update
        socketio.emit('application_updated', {
            'id': id,
            'status': 'ci_completed',
            'member_name': app_data['member_name'],
            'loan_amount': float(app_data['loan_amount']),
            'timestamp': now_ph().isoformat()
        })
        
        # Notify loan officer
        loan_officer = conn.execute('SELECT id FROM users WHERE role="loan_officer" LIMIT 1').fetchone()
        conn.close()
        
        if loan_officer:
            create_notification(loan_officer['id'],
                              f'CI interview completed for: {app_data["member_name"]}',
                              f'/admin/application/{id}')
        
        flash('CI Checklist submitted successfully!', 'success')
        return redirect(url_for('ci_dashboard'))
        
    except Exception as e:
        conn.close()
        flash(f'Error: {str(e)}', 'danger')
        return redirect(url_for('ci_checklist', id=id))

# ADMIN ROUTES
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    conn = get_db()
    
    # Get applications for review (ci_completed, approved, disapproved, deferred, or direct submissions)
    applications = conn.execute('''
        SELECT la.*, 
               u1.name as loan_staff_name,
               u2.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u1 ON la.submitted_by = u1.id
        LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
        WHERE la.status IN ('ci_completed', 'approved', 'disapproved', 'deferred')
           OR (la.needs_ci_interview = 0 AND la.status = 'submitted')
        ORDER BY la.submitted_at ASC
    ''').fetchall()
    
    # Get "In Process" applications (between LPS and CI)
    in_process_applications = conn.execute('''
        SELECT la.*, 
               u1.name as loan_staff_name,
               u2.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u1 ON la.submitted_by = u1.id
        LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
        WHERE la.status IN ('submitted', 'assigned_to_ci')
        ORDER BY la.submitted_at ASC
    ''').fetchall()
    
    # Get online CI staff
    ci_staff = conn.execute('''
        SELECT id, name, email, is_online, last_seen, profile_photo
        FROM users 
        WHERE role = 'ci_staff'
        ORDER BY is_online DESC, name ASC
    ''').fetchall()
    
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('admin_dashboard.html', 
                         applications=applications, 
                         in_process_applications=in_process_applications,
                         ci_staff=ci_staff, 
                         unread_count=unread_count)

@app.route('/admin/application/<int:id>', methods=['GET','POST'])
@login_required
def admin_application(id):
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('''
        SELECT la.*, 
               u1.name as loan_staff_name,
               u2.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u1 ON la.submitted_by = u1.id
        LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
        WHERE la.id=?
    ''', (id,)).fetchone()
    
    if not app_data:
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        decision = request.form.get('decision')
        admin_notes = request.form.get('admin_notes')
        
        try:
            conn.execute('''
                UPDATE loan_applications 
                SET status=?, admin_notes=?, admin_decision_at=?
                WHERE id=?
            ''', (decision, admin_notes, now_ph().isoformat(), id))
            
            conn.commit()
            
            # Emit real-time update to all connected dashboards
            socketio.emit('application_updated', {
                'id': id,
                'status': decision,
                'member_name': app_data['member_name'],
                'loan_amount': float(app_data['loan_amount']),
                'timestamp': now_ph().isoformat()
            })
            
            # Send SMS notification to applicant
            if app_data['member_contact']:
                if decision == 'approved':
                    sms_message = f"Good news! Your loan application for {app_data['member_name']} has been APPROVED. Amount: ₱{app_data['loan_amount']:,.2f}. Please visit DCCCO office for processing. - DCCCO Coop"
                elif decision == 'disapproved':
                    sms_message = f"We regret to inform you that your loan application for {app_data['member_name']} has been DISAPPROVED. Reason: {admin_notes[:100] if admin_notes else 'See office for details'}. - DCCCO Coop"
                else:
                    sms_message = None
                
                if sms_message:
                    send_sms(app_data['member_contact'], sms_message)
            
            conn.close()
            
            # Notify loan staff
            create_notification(app_data['submitted_by'],
                              f'Application {decision}: {app_data["member_name"]}',
                              f'/loan/application/{id}')
            
            flash(f'Application {decision}! SMS notification sent to applicant.', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            conn.close()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('admin_application', id=id))
    
    documents = conn.execute('SELECT * FROM documents WHERE loan_application_id=?', (id,)).fetchall()
    messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.loan_application_id=?
        ORDER BY m.sent_at ASC
    ''', (id,)).fetchall()
    
    # Get CI staff list for reassignment
    ci_staff_list = conn.execute('''
        SELECT id, name, email 
        FROM users 
        WHERE role='ci_staff' AND is_approved=1
        ORDER BY name ASC
    ''').fetchall()
    
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('admin_application.html', 
                         application=app_data, 
                         documents=documents, 
                         messages=messages, 
                         ci_staff_list=ci_staff_list,
                         unread_count=unread_count)

@app.route('/reassign_ci_staff/<int:app_id>', methods=['POST'])
@login_required
def reassign_ci_staff(app_id):
    """Reassign application to different CI staff (admin/loan officer only)"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    new_ci_staff_id = request.form.get('new_ci_staff_id')
    
    if not new_ci_staff_id:
        flash('Please select a CI staff member', 'warning')
        return redirect(url_for('admin_application', id=app_id))
    
    conn = get_db()
    
    try:
        # Get current assignment
        app = conn.execute('SELECT assigned_ci_staff, member_name FROM loan_applications WHERE id=?', (app_id,)).fetchone()
        old_ci_staff_id = app['assigned_ci_staff']
        
        # Update assignment
        conn.execute('''
            UPDATE loan_applications 
            SET assigned_ci_staff=? 
            WHERE id=?
        ''', (new_ci_staff_id, app_id))
        
        # Update workload counts
        if old_ci_staff_id:
            conn.execute('UPDATE users SET current_workload = current_workload - 1 WHERE id=?', (old_ci_staff_id,))
        
        conn.execute('UPDATE users SET current_workload = current_workload + 1 WHERE id=?', (new_ci_staff_id,))
        
        conn.commit()
        conn.close()
        
        # Notify new CI staff
        create_notification(int(new_ci_staff_id),
                          f'Application reassigned to you: {app["member_name"]}',
                          f'/ci/application/{app_id}')
        
        # Notify old CI staff if exists
        if old_ci_staff_id:
            create_notification(old_ci_staff_id,
                              f'Application {app["member_name"]} has been reassigned',
                              f'/ci/dashboard')
        
        flash('CI staff reassigned successfully!', 'success')
        return redirect(url_for('admin_application', id=app_id))
        
    except Exception as e:
        conn.rollback()
        conn.close()
        flash(f'Error reassigning CI staff: {str(e)}', 'danger')
        return redirect(url_for('admin_application', id=app_id))

# SHARED ROUTES
@app.route('/application/<int:id>')
@login_required
def view_application(id):
    if current_user.role in ['admin', 'loan_officer']:
        return redirect(url_for('admin_application', id=id))
    elif current_user.role == 'ci_staff':
        return redirect(url_for('ci_application', id=id))
    else:
        return redirect(url_for('loan_application', id=id))

@app.route('/loan/application/<int:id>', methods=['GET', 'POST'])
@login_required
def loan_application(id):
    if current_user.role != 'loan_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('''
        SELECT la.*, u.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.assigned_ci_staff = u.id
        WHERE la.id=? AND la.submitted_by=?
    ''', (id, current_user.id)).fetchone()
    
    if not app_data:
        flash('Application not found or you do not have permission to edit it', 'danger')
        conn.close()
        return redirect(url_for('loan_dashboard'))
    
    # Handle POST request (update application)
    if request.method == 'POST':
        # Check if application can still be edited
        if app_data['status'] not in ['submitted', 'assigned_to_ci']:
            flash('Cannot edit application - it has already been processed by CI or admin', 'warning')
            conn.close()
            return redirect(url_for('loan_application', id=id))
        
        try:
            member_name = request.form['member_name']
            member_contact = request.form.get('member_contact')
            member_address = request.form.get('member_address')
            loan_amount = request.form.get('loan_amount')
            loan_type = request.form.get('loan_type')
            needs_ci_value = request.form.get('needs_ci', '1')
            
            # Check for duplicate member name (excluding current application)
            existing = conn.execute('''
                SELECT id, member_name FROM loan_applications 
                WHERE LOWER(member_name) = LOWER(?) 
                AND status NOT IN ('disapproved', 'approved')
                AND id != ?
            ''', (member_name, id)).fetchone()
            
            if existing:
                conn.close()
                flash(f'An active application for "{member_name}" already exists (ID: #{existing["id"]}). Please use a different name.', 'warning')
                return redirect(url_for('loan_application', id=id))
            
            # Check if specific CI staff was selected
            specific_ci_id = None
            if needs_ci_value.startswith('ci_'):
                specific_ci_id = int(needs_ci_value.replace('ci_', ''))
                needs_ci = 1
            else:
                needs_ci = int(needs_ci_value)
            
            # Update application
            conn.execute('''
                UPDATE loan_applications 
                SET member_name=?, member_contact=?, member_address=?, 
                    loan_amount=?, loan_type=?, needs_ci_interview=?
                WHERE id=?
            ''', (member_name, member_contact, member_address, loan_amount, loan_type, needs_ci, id))
            
            # Handle new file uploads
            if 'documents' in request.files:
                files = request.files.getlist('documents')
                for file in files:
                    if file and file.filename:
                        if not allowed_file(file.filename):
                            conn.rollback()
                            conn.close()
                            flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF, PDF, DOC, DOCX', 'danger')
                            return redirect(url_for('loan_application', id=id))
                        
                        filename = sanitize_filename(file.filename)
                        unique_filename = f"{id}_{uuid.uuid4().hex[:8]}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(filepath)
                        conn.execute('INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by) VALUES (?, ?, ?, ?)',
                                   (id, filename, filepath, current_user.id))
            
            # Update CI staff assignment if changed
            old_ci_staff = app_data['assigned_ci_staff']
            new_ci_staff_id = None
            
            if needs_ci:
                if specific_ci_id:
                    new_ci_staff_id = specific_ci_id
                else:
                    # Route-based assignment
                    if member_address:
                        address_lower = member_address.lower()
                        route_matches = {
                            'route_1_bayawan_kalumboyan': ['kalumboyan', 'kalamtukan', 'malabugas', 'bugay', 'nangka'],
                            'route_2_bayawan_basay': ['basay', 'actin', 'bal-os', 'bongalonan', 'cabalayongan', 'maglinao', 'nagbo-alao', 'olandao'],
                            'route_3_bayawan_sipalay': ['sipalay', 'cabadiangan', 'camindangan', 'canturay', 'cartagena', 'mambaroto', 'maricalum'],
                            'route_4_bayawan_santa_catalina': ['santa catalina', 'alangilan', 'amio', 'buenavista', 'caigangan', 'cawitan', 'manalongon', 'milagrosa', 'obat', 'talalak'],
                            'route_5_bayawan_center': ['ali-is', 'banaybanay', 'banga', 'boyco', 'cansumalig', 'dawis', 'manduao', 'mandu-ao', 'maninihon', 'minaba', 'narra', 'pagatban', 'poblacion', 'san isidro', 'san jose', 'san miguel', 'san roque', 'suba', 'tabuan', 'tayawan', 'tinago', 'ubos', 'villareal', 'villasol'],
                            'route_6_bayawan_omod': ['omod', 'tamisu']
                        }
                        
                        matched_route = None
                        for route_id, keywords in route_matches.items():
                            for keyword in keywords:
                                if keyword in address_lower:
                                    matched_route = route_id
                                    break
                            if matched_route:
                                break
                        
                        if matched_route:
                            ci_staff = conn.execute('''
                                SELECT id FROM users 
                                WHERE role='ci_staff' AND is_approved=1 
                                AND (assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route LIKE ? OR assigned_route = ?)
                                LIMIT 1
                            ''', (f'%{matched_route}%,%', f'%,{matched_route}%', f'%,{matched_route},%', matched_route)).fetchone()
                            new_ci_staff_id = ci_staff['id'] if ci_staff else None
                    
                    # Fallback to workload-based
                    if not new_ci_staff_id:
                        ci_staff = conn.execute('''
                            SELECT id FROM users 
                            WHERE role='ci_staff' AND is_approved=1
                            ORDER BY current_workload ASC 
                            LIMIT 1
                        ''').fetchone()
                        new_ci_staff_id = ci_staff['id'] if ci_staff else None
                
                # Update CI staff assignment if changed
                if new_ci_staff_id and new_ci_staff_id != old_ci_staff:
                    # Decrease old CI staff workload
                    if old_ci_staff:
                        conn.execute('UPDATE users SET current_workload = current_workload - 1 WHERE id=?', (old_ci_staff,))
                    
                    # Increase new CI staff workload
                    conn.execute('UPDATE users SET current_workload = current_workload + 1 WHERE id=?', (new_ci_staff_id,))
                    
                    # Update assignment
                    conn.execute('UPDATE loan_applications SET assigned_ci_staff=?, status=? WHERE id=?',
                               (new_ci_staff_id, 'assigned_to_ci', id))
                    
                    # Notify new CI staff
                    create_notification(new_ci_staff_id, 
                                      f'Loan application reassigned to you: {member_name}',
                                      f'/ci/application/{id}')
            
            conn.commit()
            conn.close()
            
            flash('Application updated successfully!', 'success')
            socketio.emit('application_updated', {'id': id, 'member_name': member_name})
            
            return redirect(url_for('loan_application', id=id))
            
        except Exception as e:
            print(f"ERROR updating application: {str(e)}")
            import traceback
            traceback.print_exc()
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            flash(f'Error updating application: {str(e)}', 'danger')
            return redirect(url_for('loan_application', id=id))
    
    # GET request - show form
    documents = conn.execute('SELECT * FROM documents WHERE loan_application_id=?', (id,)).fetchall()
    messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.loan_application_id=?
        ORDER BY m.sent_at ASC
    ''', (id,)).fetchall()
    
    # Get all CI staff for dropdown
    ci_staff_list = conn.execute('''
        SELECT id, name, email, is_approved 
        FROM users 
        WHERE role='ci_staff' 
        ORDER BY name ASC
    ''').fetchall()
    
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    # Check if application can be edited
    can_edit = app_data['status'] in ['submitted', 'assigned_to_ci']
    
    return render_template('loan_application.html', 
                         application=app_data, 
                         documents=documents, 
                         messages=messages, 
                         unread_count=unread_count,
                         ci_staff_list=ci_staff_list,
                         can_edit=can_edit)

@app.route('/messages')
@login_required
def messages():
    conn = get_db()
    
    # Get all staff members for chat
    staff = conn.execute('''
        SELECT id, name, email, role, profile_photo 
        FROM users 
        WHERE id != ?
        ORDER BY name
    ''', (current_user.id,)).fetchall()
    
    # Get unique users we've chatted with
    chat_users = conn.execute('''
        SELECT DISTINCT
            CASE 
                WHEN sender_id = ? THEN receiver_id 
                ELSE sender_id 
            END as user_id
        FROM direct_messages
        WHERE sender_id = ? OR receiver_id = ?
    ''', (current_user.id, current_user.id, current_user.id)).fetchall()
    
    conversations = []
    for chat_user in chat_users:
        other_id = chat_user['user_id']
        
        # Get user info
        user_info = conn.execute('SELECT name, role, profile_photo FROM users WHERE id = ?', (other_id,)).fetchone()
        
        # Get last message
        last_msg = conn.execute('''
            SELECT message, sent_at 
            FROM direct_messages 
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY sent_at DESC 
            LIMIT 1
        ''', (current_user.id, other_id, other_id, current_user.id)).fetchone()
        
        # Get unread count
        unread = conn.execute('''
            SELECT COUNT(*) as count 
            FROM direct_messages 
            WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
        ''', (other_id, current_user.id)).fetchone()
        
        conversations.append({
            'other_user_id': other_id,
            'other_user_name': user_info['name'],
            'other_user_role': user_info['role'],
            'other_user_photo': user_info['profile_photo'],
            'last_message': last_msg['message'] if last_msg else '',
            'last_message_time': last_msg['sent_at'] if last_msg else '',
            'unread_count': unread['count']
        })
    
    # Sort by last message time
    conversations.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    conn.close()
    
    return render_template('messages_dark.html', staff=staff, conversations=conversations, unread_count=0)

@app.route('/messages/<int:user_id>')
@login_required
def chat_with_user(user_id):
    conn = get_db()
    
    # Get the other user's info
    other_user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    # Get all messages between current user and other user
    messages = conn.execute('''
        SELECT dm.*, u.name as sender_name
        FROM direct_messages dm
        JOIN users u ON dm.sender_id = u.id
        WHERE (dm.sender_id = ? AND dm.receiver_id = ?)
           OR (dm.sender_id = ? AND dm.receiver_id = ?)
        ORDER BY dm.sent_at ASC
    ''', (current_user.id, user_id, user_id, current_user.id)).fetchall()
    
    # Mark messages as read
    conn.execute('''
        UPDATE direct_messages 
        SET is_read = 1 
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (user_id, current_user.id))
    conn.commit()
    conn.close()
    
    return render_template('chat.html', other_user=other_user, messages=messages, unread_count=0)

@app.route('/notifications')
@login_required
def notifications():
    conn = get_db()
    
    # Get regular notifications
    notifs = conn.execute('''
        SELECT * FROM notifications 
        WHERE user_id=? 
        ORDER BY created_at DESC 
        LIMIT 50
    ''', (current_user.id,)).fetchall()
    
    # Mark notifications as read
    conn.execute('UPDATE notifications SET is_read=1 WHERE user_id=?', (current_user.id,))
    conn.commit()
    conn.close()
    
    return render_template('notifications.html', notifications=notifs, unread_count=0)

@app.route('/ci-tracking')
@login_required
def ci_tracking():
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get all CI staff with their latest location
    ci_staff = conn.execute('''
        SELECT 
            u.id, u.name, u.email,
            lt.latitude, lt.longitude, lt.activity, lt.tracked_at,
            (SELECT COUNT(*) FROM loan_applications WHERE assigned_ci_staff = u.id AND status = 'assigned_to_ci') as active_cases
        FROM users u
        LEFT JOIN location_tracking lt ON u.id = lt.user_id
        WHERE u.role = 'ci_staff'
        AND (lt.id IS NULL OR lt.id = (
            SELECT id FROM location_tracking 
            WHERE user_id = u.id 
            ORDER BY tracked_at DESC 
            LIMIT 1
        ))
        ORDER BY u.name
    ''').fetchall()
    
    conn.close()
    
    return render_template('ci_tracking.html', ci_staff=ci_staff, unread_count=0)

@app.route('/api/update_location', methods=['POST'])
@login_required
def update_location():
    data = request.json
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    activity = data.get('activity', 'Active')
    
    if not latitude or not longitude:
        return jsonify({'success': False, 'error': 'Missing coordinates'})
    
    conn = get_db()
    conn.execute('''
        INSERT INTO location_tracking (user_id, latitude, longitude, activity)
        VALUES (?, ?, ?, ?)
    ''', (current_user.id, latitude, longitude, activity))
    conn.commit()
    conn.close()
    
    # Emit realtime location update to admin tracking room
    from datetime import datetime
    socketio.emit('ci_location_update', {
        'user_id': current_user.id,
        'name': current_user.name,
        'latitude': latitude,
        'longitude': longitude,
        'activity': activity,
        'tracked_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }, room='admin_tracking')
    
    return jsonify({'success': True})

@app.route('/api/online_users')
@login_required
def get_online_users():
    """Get list of currently online users"""
    conn = get_db()
    users = conn.execute('''
        SELECT id, name, role, is_online, last_seen 
        FROM users 
        WHERE id != ?
        ORDER BY is_online DESC, last_seen DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return jsonify({
        'online_users': [dict(u) for u in users if u['is_online']],
        'all_users': [dict(u) for u in users]
    })

@app.route('/api/get_messages/<int:user_id>')
@login_required
def get_messages(user_id):
    conn = get_db()
    
    # Get all messages between current user and other user
    messages = conn.execute('''
        SELECT dm.*, u.name as sender_name
        FROM direct_messages dm
        JOIN users u ON dm.sender_id = u.id
        WHERE (dm.sender_id = ? AND dm.receiver_id = ?)
           OR (dm.sender_id = ? AND dm.receiver_id = ?)
        ORDER BY dm.sent_at ASC
    ''', (current_user.id, user_id, user_id, current_user.id)).fetchall()
    
    # Mark messages as read
    conn.execute('''
        UPDATE direct_messages 
        SET is_read = 1 
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (user_id, current_user.id))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'messages': [dict(msg) for msg in messages]
    })

@app.route('/api/mark_messages_read/<int:sender_id>', methods=['POST'])
@login_required
def mark_messages_read(sender_id):
    conn = get_db()
    conn.execute('''
        UPDATE direct_messages SET is_read = 1
        WHERE sender_id = ? AND receiver_id = ? AND is_read = 0
    ''', (sender_id, current_user.id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/unread_message_count')
@login_required
def unread_message_count():
    conn = get_db()
    row = conn.execute('''
        SELECT COUNT(*) as count FROM direct_messages
        WHERE receiver_id = ? AND is_read = 0
    ''', (current_user.id,)).fetchone()
    conn.close()
    return jsonify({'count': row['count'] if row else 0})

@app.route('/api/unread_messages_count')
@login_required
def unread_messages_count():
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) as count FROM direct_messages WHERE receiver_id=? AND is_read=0 AND is_deleted=0', (current_user.id,)).fetchone()['count']
    conn.close()
    return jsonify({'count': count})

@app.route('/api/send_direct_message', methods=['POST'])
@login_required
def send_direct_message():
    data = request.json
    receiver_id = data.get('receiver_id')
    message = data.get('message')
    
    if not receiver_id or not message:
        return jsonify({'success': False, 'error': 'Missing data'})
    
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO direct_messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (current_user.id, receiver_id, message))
    msg_id = cursor.lastrowid
    conn.commit()
    
    # Get receiver info for socket notification
    receiver = conn.execute('SELECT * FROM users WHERE id=?', (receiver_id,)).fetchone()
    conn.close()
    
    # Emit socket event to both receiver and sender for zero-delay realtime
    payload = {
        'message_id': msg_id,
        'sender_id': current_user.id,
        'sender_name': current_user.name,
        'receiver_id': receiver_id,
        'message': message,
        'timestamp': now_ph().isoformat()
    }
    socketio.emit('new_direct_message', payload, room=str(receiver_id))
    socketio.emit('new_direct_message', payload, room=str(current_user.id))
    
    return jsonify({'success': True, 'message_id': msg_id})

@app.route('/api/send_image_message', methods=['POST'])
@login_required
def send_image_message():
    receiver_id = request.form.get('receiver_id')
    
    if not receiver_id or 'image' not in request.files:
        return jsonify({'success': False, 'error': 'Missing data'})
    
    file = request.files['image']
    if not file or not file.filename:
        return jsonify({'success': False, 'error': 'No file'})
    
    # Save image
    filename = secure_filename(file.filename)
    unique_filename = f"dm_img_{current_user.id}_{uuid.uuid4().hex[:8]}_{filename}"
    filepath = os.path.join('message_attachments', unique_filename)
    
    # Create folder if not exists
    os.makedirs('message_attachments', exist_ok=True)
    file.save(filepath)
    
    # Save to database
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO direct_messages (sender_id, receiver_id, message, message_type, file_path, file_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (current_user.id, receiver_id, '[Image]', 'image', filepath, filename))
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message_id': msg_id})

@app.route('/api/send_voice_message', methods=['POST'])
@login_required
def send_voice_message():
    receiver_id = request.form.get('receiver_id')
    
    if not receiver_id or 'voice' not in request.files:
        return jsonify({'success': False, 'error': 'Missing data'})
    
    file = request.files['voice']
    if not file:
        return jsonify({'success': False, 'error': 'No file'})
    
    # Save voice message
    unique_filename = f"voice_dm_{current_user.id}_{uuid.uuid4().hex[:8]}.webm"
    filepath = os.path.join('voice_messages', unique_filename)
    
    # Create folder if not exists
    os.makedirs('voice_messages', exist_ok=True)
    file.save(filepath)
    
    # Save to database
    conn = get_db()
    cursor = conn.execute('''
        INSERT INTO direct_messages (sender_id, receiver_id, message, message_type, file_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (current_user.id, receiver_id, '[Voice Message]', 'voice', filepath))
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message_id': msg_id})

@app.route('/api/edit_direct_message', methods=['POST'])
@login_required
def edit_direct_message():
    data = request.json
    message_id = data.get('message_id')
    new_text = data.get('new_text')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id, receiver_id FROM direct_messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('''
            UPDATE direct_messages 
            SET message=?, is_edited=1, edited_at=? 
            WHERE id=?
        ''', (new_text, now_ph().isoformat(), message_id))
        conn.commit()
        conn.close()
        # Emit realtime edit to both users
        payload = {'message_id': message_id, 'new_text': new_text}
        socketio.emit('message_edited', payload, room=str(current_user.id))
        socketio.emit('message_edited', payload, room=str(msg['receiver_id']))
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/api/delete_direct_message', methods=['POST'])
@login_required
def delete_direct_message():
    data = request.json
    message_id = data.get('message_id')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id, receiver_id FROM direct_messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('UPDATE direct_messages SET is_deleted=1 WHERE id=?', (message_id,))
        conn.commit()
        conn.close()
        # Emit realtime delete to both users
        payload = {'message_id': message_id}
        socketio.emit('message_deleted', payload, room=str(current_user.id))
        socketio.emit('message_deleted', payload, room=str(msg['receiver_id']))
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    conn = get_db()
    doc = conn.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
    conn.close()
    
    if not doc:
        flash('Document not found', 'danger')
        return redirect(url_for('index'))
    
    # Validate file path is within upload folder (prevent path traversal)
    file_path = doc['file_path']
    upload_folder = os.path.abspath(app.config['UPLOAD_FOLDER'])
    requested_path = os.path.abspath(file_path)
    
    if not requested_path.startswith(upload_folder):
        flash('Invalid file path', 'danger')
        return redirect(url_for('index'))
    
    try:
        return send_file(file_path, as_attachment=True, download_name=doc['file_name'])
    except:
        flash('File not found on server', 'danger')
        return redirect(url_for('index'))

@app.route('/signatures/<path:filename>')
def serve_signature(filename):
    """Serve signature images"""
    return send_from_directory(app.config['SIGNATURE_FOLDER'], filename)

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    """Serve uploaded files"""
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            print(f"ERROR: File not found: {file_path}")
            return "File not found", 404
        
        # Security check - ensure file is within upload folder
        if not os.path.abspath(file_path).startswith(os.path.abspath(upload_folder)):
            print(f"ERROR: Security violation - path traversal attempt: {filename}")
            return "Access denied", 403
        
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        print(f"ERROR serving upload {filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error loading file: {str(e)}", 500

@app.route('/serve_message_file/<path:filename>')
@login_required
def serve_message_file(filename):
    """Serve message media files (images and voice messages)"""
    # Check if file exists in message_attachments folder (for images)
    message_attachments_path = os.path.join('message_attachments', filename)
    if os.path.exists(message_attachments_path):
        return send_from_directory('message_attachments', filename)
    
    # Otherwise check voice_messages folder
    voice_messages_path = os.path.join('voice_messages', filename)
    if os.path.exists(voice_messages_path):
        return send_from_directory('voice_messages', filename)
    
    # File not found
    return "File not found", 404

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    data = request.json
    app_id = data.get('application_id')
    message = data.get('message')
    
    if not app_id or not message:
        return jsonify({'error': 'Missing data'}), 400
    
    conn = get_db()
    conn.execute('INSERT INTO messages (loan_application_id, sender_id, message) VALUES (?, ?, ?)',
                (app_id, current_user.id, message))
    conn.commit()
    
    # Get all users involved in this application
    app_data = conn.execute('SELECT submitted_by, assigned_ci_staff FROM loan_applications WHERE id=?', 
                           (app_id,)).fetchone()
    conn.close()
    
    # Notify other users
    users_to_notify = []
    if app_data['submitted_by'] and app_data['submitted_by'] != current_user.id:
        users_to_notify.append(app_data['submitted_by'])
    if app_data['assigned_ci_staff'] and app_data['assigned_ci_staff'] != current_user.id:
        users_to_notify.append(app_data['assigned_ci_staff'])
    
    for user_id in users_to_notify:
        create_notification(user_id, f'New message from {current_user.name}', f'/application/{app_id}')
    
    socketio.emit('new_message', {
        'application_id': app_id,
        'sender': current_user.name,
        'message': message,
        'timestamp': now_ph().isoformat()
    }, room=f'app_{app_id}')
    
    return jsonify({'success': True})

# Modern Messenger Routes
@app.route('/api/send_message_with_attachment', methods=['POST'])
@login_required
def send_message_with_attachment():
    app_id = request.form.get('application_id')
    message = request.form.get('message', '')
    message_type = request.form.get('message_type', 'text')
    
    file_path = None
    file_name = None
    
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename:
            filename = secure_filename(file.filename)
            
            if message_type == 'voice':
                folder = 'voice_messages'
                unique_filename = f"voice_{app_id}_{uuid.uuid4().hex[:8]}.webm"
            elif message_type == 'image':
                folder = 'message_attachments'
                unique_filename = f"img_{app_id}_{uuid.uuid4().hex[:8]}_{filename}"
            else:
                folder = 'message_attachments'
                unique_filename = f"file_{app_id}_{uuid.uuid4().hex[:8]}_{filename}"
            
            file_path = os.path.join(folder, unique_filename)
            file.save(file_path)
            file_name = filename
    
    conn = get_db()
    conn.execute('''
        INSERT INTO messages (loan_application_id, sender_id, message, message_type, file_path, file_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (app_id, current_user.id, message, message_type, file_path, file_name))
    conn.commit()
    
    # Get all users involved
    app_data = conn.execute('SELECT submitted_by, assigned_ci_staff FROM loan_applications WHERE id=?', 
                           (app_id,)).fetchone()
    conn.close()
    
    # Notify other users
    users_to_notify = []
    if app_data['submitted_by'] and app_data['submitted_by'] != current_user.id:
        users_to_notify.append(app_data['submitted_by'])
    if app_data['assigned_ci_staff'] and app_data['assigned_ci_staff'] != current_user.id:
        users_to_notify.append(app_data['assigned_ci_staff'])
    
    for user_id in users_to_notify:
        create_notification(user_id, f'New message from {current_user.name}', f'/application/{app_id}')
    
    socketio.emit('new_message', {
        'application_id': int(app_id),
        'sender': current_user.name,
        'message': message,
        'timestamp': now_ph().isoformat()
    }, room=f'app_{app_id}')
    
    return jsonify({'success': True})

@app.route('/api/edit_message', methods=['POST'])
@login_required
def edit_message():
    data = request.json
    message_id = data.get('message_id')
    new_text = data.get('new_text')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id FROM messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('''
            UPDATE messages 
            SET message=?, is_edited=1, edited_at=? 
            WHERE id=?
        ''', (new_text, now_ph().isoformat(), message_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/api/delete_message', methods=['POST'])
@login_required
def delete_message():
    data = request.json
    message_id = data.get('message_id')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id FROM messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('UPDATE messages SET is_deleted=1 WHERE id=?', (message_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/download_message_file/<int:msg_id>')
@login_required
def download_message_file(msg_id):
    conn = get_db()
    msg = conn.execute('SELECT * FROM messages WHERE id=?', (msg_id,)).fetchone()
    conn.close()
    
    if not msg or not msg['file_path']:
        flash('File not found', 'danger')
        return redirect(url_for('index'))
    
    # Validate file path (prevent path traversal)
    file_path = msg['file_path']
    allowed_folders = [
        os.path.abspath('voice_messages'),
        os.path.abspath('message_attachments')
    ]
    requested_path = os.path.abspath(file_path)
    
    is_valid = any(requested_path.startswith(folder) for folder in allowed_folders)
    if not is_valid:
        flash('Invalid file path', 'danger')
        return redirect(url_for('index'))
    
    try:
        return send_file(msg['file_path'], as_attachment=True, download_name=msg['file_name'])
    except:
        flash('File not found on server', 'danger')
        return redirect(url_for('index'))

@app.route('/api/get_messages/<int:app_id>')
@login_required
def get_messages_api(app_id):
    conn = get_db()
    messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.loan_application_id=?
        ORDER BY m.sent_at ASC
    ''', (app_id,)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'messages': [dict(msg) for msg in messages]
    })

# SocketIO events
@socketio.on('connect')
def handle_connect(auth=None):
    if current_user.is_authenticated:
        join_room(str(current_user.id))
        # Mark user as online
        online_users[current_user.id] = {
            'name': current_user.name,
            'role': current_user.role,
            'last_seen': now_ph().isoformat()
        }
        # Update database
        conn = get_db()
        conn.execute('UPDATE users SET last_seen=?, is_online=1 WHERE id=?', 
                    (now_ph().isoformat(), current_user.id))
        conn.commit()
        conn.close()
        # Broadcast to all users that this user is online
        socketio.emit('user_online', {
            'user_id': current_user.id,
            'name': current_user.name,
            'role': current_user.role
        }, to=None, include_self=True)

@socketio.on('disconnect')
def handle_disconnect(reason=None):
    if current_user.is_authenticated:
        # Mark user as offline
        if current_user.id in online_users:
            del online_users[current_user.id]
        # Update database
        conn = get_db()
        conn.execute('UPDATE users SET last_seen=?, is_online=0 WHERE id=?', 
                    (now_ph().isoformat(), current_user.id))
        conn.commit()
        conn.close()
        # Broadcast to all users that this user is offline
        socketio.emit('user_offline', {
            'user_id': current_user.id
        }, to=None, include_self=True)

@socketio.on('join_application')
def handle_join_application(data):
    app_id = data.get('application_id')
    if app_id:
        join_room(f'app_{app_id}')

@socketio.on('join')
def handle_join(data):
    room = data.get('room')
    if room:
        join_room(room)

@socketio.on('join_tracking')
def handle_join_tracking(data):
    if current_user.is_authenticated and current_user.role in ['admin', 'loan_officer']:
        join_room('admin_tracking')

# Flutter Mobile App API Endpoints
@app.route('/api/user_info')
@login_required
def user_info():
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'role': current_user.role
    })

@app.route('/api/ci_applications')
@login_required
def ci_applications():
    if current_user.role != 'ci_staff':
        return jsonify([])
    
    conn = get_db()
    apps = conn.execute('''
        SELECT * FROM loan_applications 
        WHERE assigned_ci_staff = ? 
        ORDER BY submitted_at DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return jsonify([dict(app) for app in apps])

@app.route('/api/ci_application/<int:id>')
@login_required
def ci_application_api(id):
    conn = get_db()
    app = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    documents = conn.execute('SELECT * FROM documents WHERE loan_application_id=?', (id,)).fetchall()
    conn.close()
    
    return jsonify({
        'application': dict(app) if app else None,
        'documents': [dict(doc) for doc in documents]
    })

# OFFLINE PWA API ENDPOINTS
@app.route('/api/ci/download_applications', methods=['GET'])
@login_required
def api_download_applications():
    """Get all applications assigned to current CI staff for offline download"""
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    apps = conn.execute('''
        SELECT * FROM loan_applications 
        WHERE assigned_ci_staff = ? AND status = 'assigned_to_ci'
        ORDER BY submitted_at DESC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'applications': [dict(app) for app in apps],
        'count': len(apps)
    })

@app.route('/api/ci/upload_checklist', methods=['POST'])
@login_required
def api_upload_checklist():
    """Upload completed checklist from offline storage"""
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        application_id = data.get('application_id')
        checklist_data = data.get('checklist_data')
        signature = data.get('signature')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not all([application_id, checklist_data, signature]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        conn = get_db()
        
        # Update application
        conn.execute('''
            UPDATE loan_applications 
            SET status = 'ci_completed',
                ci_checklist_data = ?,
                ci_signature = ?,
                ci_completed_at = ?,
                ci_notes = 'Submitted offline'
            WHERE id = ? AND assigned_ci_staff = ?
        ''', (checklist_data, signature, now_ph().strftime('%Y-%m-%d %H:%M:%S'), 
              application_id, current_user.id))
        
        # Track location if provided
        if latitude and longitude:
            conn.execute('''
                INSERT INTO location_tracking (user_id, latitude, longitude, activity, tracked_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, latitude, longitude, 'CI Checklist Submitted', 
                  now_ph().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Checklist uploaded successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ci/sync_status', methods=['GET'])
@login_required
def api_sync_status():
    """Get sync status for offline PWA"""
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    
    # Count pending applications
    pending = conn.execute('''
        SELECT COUNT(*) as count FROM loan_applications 
        WHERE assigned_ci_staff = ? AND status = 'assigned_to_ci'
    ''', (current_user.id,)).fetchone()
    
    # Count completed applications
    completed = conn.execute('''
        SELECT COUNT(*) as count FROM loan_applications 
        WHERE assigned_ci_staff = ? AND status = 'ci_completed'
    ''', (current_user.id,)).fetchone()
    
    conn.close()
    
    return jsonify({
        'success': True,
        'pending_count': pending['count'] if pending else 0,
        'completed_count': completed['count'] if completed else 0,
        'is_online': True
    })

# USER REGISTRATION & APPROVAL ROUTES
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        signature_data = request.form.get('signature_data')
        
        # Validation
        if not all([name, email, password, confirm_password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('signup'))
        
        if not signature_data:
            flash('Signature is required', 'danger')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signup'))
        
        # Validate password strength
        is_valid, message = validate_password_strength(password)
        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('signup'))
        
        conn = get_db()
        
        # Check if email already exists
        existing = conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if existing:
            flash('Email already registered', 'danger')
            conn.close()
            return redirect(url_for('signup'))
        
        # Save signature
        signature_path = None
        if signature_data and signature_data.startswith('data:image'):
            import base64
            signature_base64 = signature_data.split(',')[1]
            signature_bytes = base64.b64decode(signature_base64)
            signature_filename = f"signature_{email.replace('@', '_').replace('.', '_')}_{uuid.uuid4().hex[:8]}.png"
            signature_path = os.path.join(app.config['SIGNATURE_FOLDER'], signature_filename)
            with open(signature_path, 'wb') as f:
                f.write(signature_bytes)
        
        # Create new user (not approved yet, no role assigned - admin will assign)
        try:
            password_hash = generate_password_hash(password)
            conn.execute('''
                INSERT INTO users (email, password_hash, name, role, signature_path, assigned_route, is_approved, created_at)
                VALUES (?, ?, ?, NULL, ?, NULL, 0, ?)
            ''', (email, password_hash, name, signature_path, now_ph().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            # Notify admin
            admin = conn.execute('SELECT id FROM users WHERE role="admin" LIMIT 1').fetchone()
            conn.close()
            
            if admin:
                create_notification(admin['id'], 
                                  f'New staff registration: {name} - Role and route assignment required',
                                  '/manage_users')
            
            flash('Registration successful! Please wait for admin to assign your role and approve your account.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/manage_users')
@login_required
def manage_users():
    # Check if user has permission
    if current_user.role == 'admin':
        # Super admin always has access
        pass
    elif current_user.role == 'loan_officer':
        # Check if loan officer has manage_users permission
        if not has_permission(current_user, 'manage_users'):
            flash('Access Denied - You do not have permission to manage users. Contact super admin.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get pending users
    pending_users = conn.execute('''
        SELECT id, name, email, role, assigned_route, created_at, approval_type
        FROM users
        WHERE is_approved = 0
        ORDER BY created_at DESC
    ''').fetchall()
    
    # Get active users
    active_users = conn.execute('''
        SELECT id, name, email, role, assigned_route, created_at
        FROM users
        WHERE is_approved = 1
        ORDER BY name ASC
    ''').fetchall()
    
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('manage_users.html', 
                         pending_users=pending_users, 
                         active_users=active_users,
                         unread_count=unread_count)

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    if not user:
        flash('User not found', 'danger')
        conn.close()
        return redirect(url_for('manage_users'))
    
    # Check if role is assigned
    if not user['role']:
        flash(f'Cannot approve {user["name"]} - Please assign a role first!', 'warning')
        conn.close()
        return redirect(url_for('manage_users'))
    
    # Check if CI staff has route assigned
    if user['role'] == 'ci_staff' and not user['assigned_route']:
        flash(f'Cannot approve {user["name"]} - CI staff must have a route assigned!', 'warning')
        conn.close()
        return redirect(url_for('manage_users'))
    
    conn.execute('UPDATE users SET is_approved = 1 WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    
    # Notify the user
    create_notification(user_id, 
                      'Your account has been approved! You can now login.',
                      '/login')
    
    flash(f'User {user["name"]} approved successfully!', 'success')
    return redirect(url_for('manage_users'))

@app.route('/disapprove_user/<int:user_id>', methods=['POST'])
@login_required
def disapprove_user(user_id):
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    if not user:
        flash('User not found', 'danger')
        conn.close()
        return redirect(url_for('manage_users'))
    
    # Delete the user
    conn.execute('DELETE FROM users WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'User {user["name"]} disapproved and removed.', 'info')
    return redirect(url_for('manage_users'))

@app.route('/assign_role/<int:user_id>', methods=['POST'])
@login_required
def assign_role(user_id):
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    role = data.get('role')
    
    if not role or role not in ['admin', 'loan_officer', 'loan_staff', 'ci_staff']:
        return jsonify({'success': False, 'error': 'Invalid role'}), 400
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Update role
    conn.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
    
    # If changing from ci_staff to another role, clear assigned_route
    if user['role'] == 'ci_staff' and role != 'ci_staff':
        conn.execute('UPDATE users SET assigned_route=NULL WHERE id=?', (user_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Role assigned successfully'})

@app.route('/deactivate_user/<int:user_id>', methods=['POST'])
@login_required
def deactivate_user(user_id):
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    if not user:
        flash('User not found', 'danger')
        conn.close()
        return redirect(url_for('manage_users'))
    
    if user['role'] == 'admin':
        flash('Cannot deactivate admin users', 'danger')
        conn.close()
        return redirect(url_for('manage_users'))
    
    conn.execute('UPDATE users SET is_approved = 0 WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    
    flash(f'User {user["name"]} deactivated.', 'warning')
    return redirect(url_for('manage_users'))

@app.route('/update_ci_route', methods=['POST'])
@login_required
def update_ci_route():
    if current_user.role not in ['admin', 'loan_officer']:
        # Check if it's JSON request
        if request.is_json:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
        user_id = data.get('user_id')
        assigned_route = data.get('assigned_route')
    else:
        user_id = request.form.get('user_id')
        assigned_route = request.form.get('assigned_route')
    
    if not user_id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        flash('Invalid request', 'danger')
        return redirect(url_for('manage_users'))
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    if not user:
        conn.close()
        if request.is_json:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        flash('User not found', 'danger')
        return redirect(url_for('manage_users'))
    
    # Update route
    conn.execute('UPDATE users SET assigned_route=? WHERE id=?', (assigned_route, user_id))
    conn.commit()
    conn.close()
    
    # Notify the CI staff if route assigned
    if assigned_route:
        create_notification(int(user_id), 
                          f'Your assigned route has been updated',
                          '/ci/dashboard')
    
    # Return appropriate response
    if request.is_json:
        return jsonify({'success': True, 'message': 'Route assigned successfully'})
    
    flash(f'Route assigned successfully!', 'success')
    return redirect(url_for('manage_users'))

# REPORT GENERATION ROUTES
@app.route('/reports')
@login_required
def reports():
    """Reports dashboard page"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    ci_staff = conn.execute('SELECT id, name FROM users WHERE role="ci_staff" ORDER BY name').fetchall()
    conn.close()
    
    return render_template('reports.html', ci_staff=ci_staff)

@app.route('/system_settings')
@login_required
def system_settings():
    """System configuration page (admin only or loan officer with permission)"""
    # Check if user has permission
    if current_user.role == 'admin':
        # Super admin always has access
        pass
    elif current_user.role == 'loan_officer':
        # Check if loan officer has system_settings permission
        if not has_permission(current_user, 'system_settings'):
            flash('Access Denied - You do not have permission to access system settings. Contact super admin.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('Unauthorized - Admin access required', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get all system settings
    settings = conn.execute('SELECT * FROM system_settings ORDER BY setting_key').fetchall()
    
    # Get system statistics
    stats = {
        'total_users': conn.execute('SELECT COUNT(*) as count FROM users WHERE is_approved=1').fetchone()['count'],
        'total_applications': conn.execute('SELECT COUNT(*) as count FROM loan_applications').fetchone()['count'],
        'pending_ci': conn.execute('SELECT COUNT(*) as count FROM loan_applications WHERE status="assigned_to_ci"').fetchone()['count'],
        'approved_loans': conn.execute('SELECT COUNT(*) as count FROM loan_applications WHERE status="approved"').fetchone()['count'],
        'total_loan_amount': conn.execute('SELECT COALESCE(SUM(loan_amount), 0) as total FROM loan_applications WHERE status="approved"').fetchone()['total']
    }
    
    conn.close()
    
    return render_template('system_settings.html', settings=settings, stats=stats)

@app.route('/update_system_settings', methods=['POST'])
@login_required
def update_system_settings():
    """Update system settings (admin only or loan officer with permission)"""
    # Check if user has permission
    if current_user.role == 'admin':
        pass
    elif current_user.role == 'loan_officer':
        if not has_permission(current_user, 'system_settings'):
            flash('Access Denied - You do not have permission to update system settings.', 'danger')
            return redirect(url_for('admin_dashboard'))
    else:
        flash('Unauthorized - Admin access required', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get all settings
    settings = conn.execute('SELECT id FROM system_settings').fetchall()
    
    # Update each setting
    for setting in settings:
        setting_id = setting['id']
        new_value = request.form.get(f'setting_{setting_id}')
        if new_value is not None:
            conn.execute('UPDATE system_settings SET setting_value=? WHERE id=?', (new_value, setting_id))
    
    conn.commit()
    conn.close()
    
    flash('System settings updated successfully!', 'success')
    return redirect(url_for('system_settings'))

@app.route('/manage_permissions')
@login_required
def manage_permissions():
    """Manage loan officer permissions (super admin only)"""
    if current_user.role != 'admin':
        flash('Unauthorized - Super Admin access required', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    try:
        # Check if permissions column exists, if not add it
        columns = conn.execute('PRAGMA table_info(users)').fetchall()
        column_names = [col[1] for col in columns]
        
        if 'permissions' not in column_names:
            # Add permissions column
            conn.execute('ALTER TABLE users ADD COLUMN permissions TEXT')
            conn.commit()
            flash('Permissions system initialized successfully!', 'success')
        
        # Get all loan officers
        loan_officers = conn.execute('''
            SELECT id, name, email, permissions
            FROM users
            WHERE role = 'loan_officer' AND is_approved = 1
            ORDER BY name ASC
        ''').fetchall()
        
        # Get unread notification count
        unread_count = conn.execute('''
            SELECT COUNT(*) as count 
            FROM notifications 
            WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"
        ''', (current_user.id,)).fetchone()['count']
        
        conn.close()
        
        return render_template('manage_permissions.html', 
                             loan_officers=loan_officers,
                             unread_count=unread_count)
    
    except Exception as e:
        conn.close()
        flash(f'Error loading permissions page: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/update_permissions/<int:user_id>', methods=['POST'])
@login_required
def update_permissions(user_id):
    """Update loan officer permissions (super admin only)"""
    if current_user.role != 'admin':
        flash('Unauthorized - Super Admin access required', 'danger')
        return redirect(url_for('index'))
    
    try:
        conn = get_db()
        
        # Get selected permissions
        permissions = []
        if request.form.get('manage_users'):
            permissions.append('manage_users')
        if request.form.get('system_settings'):
            permissions.append('system_settings')
        
        # Update user permissions
        permissions_str = ','.join(permissions) if permissions else None
        conn.execute('UPDATE users SET permissions=? WHERE id=? AND role="loan_officer"', 
                     (permissions_str, user_id))
        conn.commit()
        
        # Get user name for flash message
        user = conn.execute('SELECT name FROM users WHERE id=?', (user_id,)).fetchone()
        conn.close()
        
        flash(f'Permissions updated successfully for {user["name"]}!', 'success')
        return redirect(url_for('manage_permissions'))
    
    except Exception as e:
        flash(f'Error updating permissions: {str(e)}', 'danger')
        return redirect(url_for('manage_permissions'))

# Migration route removed - permissions column already exists in database
# Superadmin has full access without needing migrations

@app.route('/get_user_permissions/<int:user_id>', methods=['GET'])
@login_required
def get_user_permissions(user_id):
    """Get current permissions for a user (super admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        conn = get_db()
        user = conn.execute('SELECT permissions FROM users WHERE id=? AND role="loan_officer"', (user_id,)).fetchone()
        conn.close()
        
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        permissions = user['permissions'].split(',') if user['permissions'] else []
        return jsonify({'success': True, 'permissions': permissions})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update_permissions_inline/<int:user_id>', methods=['POST'])
@login_required
def update_permissions_inline(user_id):
    """Update loan officer permissions inline (super admin only)"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        permissions = data.get('permissions', [])
        
        # Validate permissions
        valid_permissions = ['manage_users', 'system_settings']
        for perm in permissions:
            if perm not in valid_permissions:
                return jsonify({'success': False, 'error': f'Invalid permission: {perm}'}), 400
        
        conn = get_db()
        
        # Verify user is a loan officer
        user = conn.execute('SELECT name FROM users WHERE id=? AND role="loan_officer"', (user_id,)).fetchone()
        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'User not found or not a loan officer'}), 404
        
        # Update permissions
        permissions_str = ','.join(permissions) if permissions else None
        conn.execute('UPDATE users SET permissions=? WHERE id=?', (permissions_str, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Permissions updated for {user["name"]}',
            'permissions': permissions
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generate_report/<report_type>', methods=['POST'])
@login_required
def generate_report(report_type):
    """Generate PDF reports with date range filters"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from io import BytesIO
    
    # Get date range from form
    from_date = request.form.get('from_date')
    to_date = request.form.get('to_date')
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1e3a5f'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    conn = get_db()
    
    if report_type == 'applications':
        # Application List Report
        status_filter = request.form.get('status_filter', 'all')
        
        # Title
        elements.append(Paragraph('DCCCO - Loan Application Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Query data
        if status_filter == 'all':
            apps = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.loan_type, la.status, 
                       la.submitted_at, u.name as submitted_by_name
                FROM loan_applications la
                LEFT JOIN users u ON la.submitted_by = u.id
                WHERE DATE(la.submitted_at) BETWEEN ? AND ?
                ORDER BY la.submitted_at DESC
            ''', (from_date, to_date)).fetchall()
        else:
            apps = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.loan_type, la.status, 
                       la.submitted_at, u.name as submitted_by_name
                FROM loan_applications la
                LEFT JOIN users u ON la.submitted_by = u.id
                WHERE DATE(la.submitted_at) BETWEEN ? AND ? AND la.status = ?
                ORDER BY la.submitted_at DESC
            ''', (from_date, to_date, status_filter)).fetchall()
        
        # Create table
        data = [['ID', 'Member Name', 'Amount', 'Type', 'Status', 'Submitted By', 'Date']]
        for app in apps:
            data.append([
                str(app['id']),
                app['member_name'][:20],
                f"₱{app['loan_amount']:,.0f}",
                (app['loan_type'] or 'N/A')[:15],
                app['status'],
                (app['submitted_by_name'] or 'N/A')[:15],
                app['submitted_at'][:10] if app['submitted_at'] else 'N/A'
            ])
        
        table = Table(data, colWidths=[0.5*inch, 1.5*inch, 1*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f'Total Applications: {len(apps)}', styles['Normal']))
        
    elif report_type == 'ci_reports':
        # CI Reports
        ci_staff_filter = request.form.get('ci_staff_filter', 'all')
        
        elements.append(Paragraph('DCCCO - Credit Investigation Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        if ci_staff_filter == 'all':
            cis = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.ci_completed_at,
                       u.name as ci_staff_name, la.ci_latitude, la.ci_longitude
                FROM loan_applications la
                LEFT JOIN users u ON la.assigned_ci_staff = u.id
                WHERE la.status = 'ci_completed' 
                AND DATE(la.ci_completed_at) BETWEEN ? AND ?
                ORDER BY la.ci_completed_at DESC
            ''', (from_date, to_date)).fetchall()
        else:
            cis = conn.execute('''
                SELECT la.id, la.member_name, la.loan_amount, la.ci_completed_at,
                       u.name as ci_staff_name, la.ci_latitude, la.ci_longitude
                FROM loan_applications la
                LEFT JOIN users u ON la.assigned_ci_staff = u.id
                WHERE la.status = 'ci_completed' 
                AND DATE(la.ci_completed_at) BETWEEN ? AND ?
                AND la.assigned_ci_staff = ?
                ORDER BY la.ci_completed_at DESC
            ''', (from_date, to_date, ci_staff_filter)).fetchall()
        
        data = [['ID', 'Member Name', 'Amount', 'CI Staff', 'Completed Date', 'Location']]
        for ci in cis:
            location = 'N/A'
            if ci['ci_latitude'] and ci['ci_longitude']:
                location = f"{ci['ci_latitude'][:8]}, {ci['ci_longitude'][:8]}"
            
            data.append([
                str(ci['id']),
                ci['member_name'][:25],
                f"₱{ci['loan_amount']:,.0f}",
                (ci['ci_staff_name'] or 'N/A')[:20],
                ci['ci_completed_at'][:10] if ci['ci_completed_at'] else 'N/A',
                location
            ])
        
        table = Table(data, colWidths=[0.5*inch, 1.8*inch, 1*inch, 1.5*inch, 1.2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f'Total CI Completed: {len(cis)}', styles['Normal']))
        
    elif report_type == 'user_reports':
        # User Reports
        role_filter = request.form.get('role_filter', 'all')
        
        elements.append(Paragraph('DCCCO - User Activity Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        if role_filter == 'all':
            users = conn.execute('''
                SELECT u.id, u.name, u.email, u.role, u.created_at,
                       COUNT(DISTINCT la.id) as app_count
                FROM users u
                LEFT JOIN loan_applications la ON 
                    (u.id = la.submitted_by OR u.id = la.assigned_ci_staff)
                    AND DATE(la.submitted_at) BETWEEN ? AND ?
                WHERE u.is_approved = 1
                GROUP BY u.id
                ORDER BY app_count DESC, u.name
            ''', (from_date, to_date)).fetchall()
        else:
            users = conn.execute('''
                SELECT u.id, u.name, u.email, u.role, u.created_at,
                       COUNT(DISTINCT la.id) as app_count
                FROM users u
                LEFT JOIN loan_applications la ON 
                    (u.id = la.submitted_by OR u.id = la.assigned_ci_staff)
                    AND DATE(la.submitted_at) BETWEEN ? AND ?
                WHERE u.is_approved = 1 AND u.role = ?
                GROUP BY u.id
                ORDER BY app_count DESC, u.name
            ''', (from_date, to_date, role_filter)).fetchall()
        
        data = [['ID', 'Name', 'Email', 'Role', 'Applications', 'Joined']]
        for user in users:
            data.append([
                str(user['id']),
                user['name'][:20],
                user['email'][:25],
                user['role'],
                str(user['app_count']),
                user['created_at'][:10] if user['created_at'] else 'N/A'
            ])
        
        table = Table(data, colWidths=[0.5*inch, 1.5*inch, 2*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f'Total Users: {len(users)}', styles['Normal']))
        
    elif report_type == 'transaction_summary':
        # Transaction Summary
        group_by = request.form.get('group_by', 'status')
        
        elements.append(Paragraph('DCCCO - Transaction Summary Report', title_style))
        elements.append(Paragraph(f'Period: {from_date} to {to_date}', subtitle_style))
        elements.append(Spacer(1, 0.2*inch))
        
        if group_by == 'status':
            summary = conn.execute('''
                SELECT status, COUNT(*) as count, SUM(loan_amount) as total_amount
                FROM loan_applications
                WHERE DATE(submitted_at) BETWEEN ? AND ?
                GROUP BY status
                ORDER BY count DESC
            ''', (from_date, to_date)).fetchall()
            
            data = [['Status', 'Count', 'Total Amount']]
            for row in summary:
                data.append([
                    row['status'],
                    str(row['count']),
                    f"₱{row['total_amount']:,.2f}" if row['total_amount'] else '₱0.00'
                ])
                
        elif group_by == 'loan_type':
            summary = conn.execute('''
                SELECT loan_type, COUNT(*) as count, SUM(loan_amount) as total_amount
                FROM loan_applications
                WHERE DATE(submitted_at) BETWEEN ? AND ?
                GROUP BY loan_type
                ORDER BY count DESC
            ''', (from_date, to_date)).fetchall()
            
            data = [['Loan Type', 'Count', 'Total Amount']]
            for row in summary:
                data.append([
                    row['loan_type'] or 'N/A',
                    str(row['count']),
                    f"₱{row['total_amount']:,.2f}" if row['total_amount'] else '₱0.00'
                ])
                
        else:  # month
            summary = conn.execute('''
                SELECT strftime('%Y-%m', submitted_at) as month, 
                       COUNT(*) as count, SUM(loan_amount) as total_amount
                FROM loan_applications
                WHERE DATE(submitted_at) BETWEEN ? AND ?
                GROUP BY month
                ORDER BY month DESC
            ''', (from_date, to_date)).fetchall()
            
            data = [['Month', 'Count', 'Total Amount']]
            for row in summary:
                data.append([
                    row['month'] or 'N/A',
                    str(row['count']),
                    f"₱{row['total_amount']:,.2f}" if row['total_amount'] else '₱0.00'
                ])
        
        table = Table(data, colWidths=[3*inch, 1.5*inch, 2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f59e0b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        elements.append(table)
        
        # Add grand total
        total = conn.execute('''
            SELECT COUNT(*) as count, SUM(loan_amount) as total_amount
            FROM loan_applications
            WHERE DATE(submitted_at) BETWEEN ? AND ?
        ''', (from_date, to_date)).fetchone()
        
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f'<b>Grand Total:</b> {total["count"]} applications, ₱{total["total_amount"]:,.2f}', styles['Normal']))
    
    conn.close()
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Return PDF
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'DCCCO_{report_type}_{from_date}_to_{to_date}.pdf'
    )

# PASSWORD CHANGE & RESET ROUTES
@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([current_password, new_password, confirm_password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('change_password'))
        
        # Verify current password
        conn = get_db()
        user = conn.execute('SELECT * FROM users WHERE id=?', (current_user.id,)).fetchone()
        conn.close()
        
        if not check_password_hash(user['password_hash'], current_password):
            flash('Current password is incorrect', 'danger')
            return redirect(url_for('change_password'))
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'danger')
            return redirect(url_for('change_password'))
        
        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            flash(message, 'danger')
            return redirect(url_for('change_password'))
        
        # Update password
        conn = get_db()
        new_hash = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password_hash=? WHERE id=?', (new_hash, current_user.id))
        conn.commit()
        conn.close()
        
        flash('Password updated successfully!', 'success')
        return redirect(url_for('index'))
    
    conn = get_db()
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('change_password.html', unread_count=unread_count)

@app.route('/update_backup_email', methods=['POST'])
@login_required
def update_backup_email():
    backup_email = request.form.get('backup_email', '').strip()
    
    conn = get_db()
    conn.execute('UPDATE users SET backup_email=? WHERE id=?', (backup_email, current_user.id))
    conn.commit()
    conn.close()
    
    flash('Backup email updated successfully!', 'success')
    return redirect(url_for('change_password'))

@app.route('/update_signature', methods=['POST'])
@login_required
def update_signature():
    signature_data = request.form.get('signature_data')
    
    if not signature_data or not signature_data.startswith('data:image'):
        flash('Invalid signature data', 'danger')
        return redirect(url_for('change_password'))
    
    try:
        import base64
        # Delete old signature if exists
        conn = get_db()
        old_sig = conn.execute('SELECT signature_path FROM users WHERE id=?', (current_user.id,)).fetchone()
        if old_sig and old_sig['signature_path']:
            try:
                os.remove(old_sig['signature_path'])
            except:
                pass
        
        # Save new signature
        signature_base64 = signature_data.split(',')[1]
        signature_bytes = base64.b64decode(signature_base64)
        signature_filename = f"signature_{current_user.email.replace('@', '_').replace('.', '_')}_{uuid.uuid4().hex[:8]}.png"
        signature_path = os.path.join(app.config['SIGNATURE_FOLDER'], signature_filename)
        with open(signature_path, 'wb') as f:
            f.write(signature_bytes)
        
        # Update database
        conn.execute('UPDATE users SET signature_path=? WHERE id=?', (signature_path, current_user.id))
        conn.commit()
        conn.close()
        
        flash('Signature updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating signature: {str(e)}', 'danger')
    
    return redirect(url_for('change_password'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    
    if not name or not email:
        flash('Name and email are required', 'danger')
        return redirect(url_for('change_password'))
    
    # Check if email is already taken by another user
    conn = get_db()
    existing = conn.execute('SELECT id FROM users WHERE email=? AND id!=?', (email, current_user.id)).fetchone()
    if existing:
        conn.close()
        flash('Email already in use by another account', 'danger')
        return redirect(url_for('change_password'))
    
    # Handle profile photo upload
    profile_photo_path = None
    if 'profile_photo' in request.files:
        file = request.files['profile_photo']
        if file and file.filename:
            if not allowed_file(file.filename):
                conn.close()
                flash('Invalid file type. Allowed: PNG, JPG, JPEG, GIF', 'danger')
                return redirect(url_for('change_password'))
            
            # Delete old photo if exists
            old_photo = conn.execute('SELECT profile_photo FROM users WHERE id=?', (current_user.id,)).fetchone()
            if old_photo and old_photo['profile_photo']:
                try:
                    os.remove(old_photo['profile_photo'])
                except:
                    pass
            
            # Save new photo
            filename = sanitize_filename(file.filename)
            unique_filename = f"profile_{current_user.id}_{uuid.uuid4().hex[:8]}_{filename}"
            profile_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(profile_photo_path)
    
    # Update database
    if profile_photo_path:
        conn.execute('UPDATE users SET name=?, email=?, profile_photo=? WHERE id=?', 
                    (name, email, profile_photo_path, current_user.id))
    else:
        conn.execute('UPDATE users SET name=?, email=? WHERE id=?', 
                    (name, email, current_user.id))
    conn.commit()
    conn.close()
    
    # Update current_user object
    current_user.name = name
    current_user.email = email
    
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('change_password'))

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        try:
            step = request.form.get('step', 'send_code')
            email = request.form.get('email', '').strip()
            
            if not email:
                flash('Please enter your email address.', 'danger')
                return render_template('forgot_password.html', email='', code='')
            
            conn = get_db()
            
            if step == 'send_code':
                # ONLY use the registered email (not backup email)
                user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                
                if user:
                    import random
                    code = str(random.randint(100000, 999999))
                    expires = (now_ph() + timedelta(minutes=15)).isoformat()
                    
                    conn.execute('UPDATE users SET password_reset_token=?, password_reset_expires=? WHERE id=?',
                                (code, expires, user['id']))
                    conn.commit()
                    
                    # Send code to the registered email only
                    email_sent = send_verification_email(user['email'], code, user['name'])
                    conn.close()
                    
                    if email_sent == True:
                        flash('Verification code sent to your registered email! Check your inbox.', 'success')
                        return render_template('forgot_password.html', show_code_input=True, email=email, code='')
                    elif email_sent == "RESEND_LIMIT":
                        flash(f'Testing Mode: Email can only be sent to tangentejerremiah9@gmail.com. For production use, a domain needs to be verified. Please contact admin.', 'info')
                        return redirect(url_for('forgot_password'))
                    else:
                        flash('Unable to send email. Please try again later.', 'danger')
                        return redirect(url_for('forgot_password'))
                else:
                    conn.close()
                    flash('If that email exists, a verification code has been sent.', 'info')
                    return redirect(url_for('forgot_password'))
            
            elif step == 'verify_code':
                code = request.form.get('code', '').strip()
                
                if not code:
                    flash('Please enter the verification code.', 'danger')
                    conn.close()
                    return render_template('forgot_password.html', show_code_input=True, email=email, code='')
                
                # ONLY check registered email (not backup email)
                user = conn.execute('SELECT * FROM users WHERE email=? AND password_reset_token=?', 
                                  (email, code)).fetchone()
                
                if user and user['password_reset_expires']:
                    expires = datetime.fromisoformat(user['password_reset_expires'])
                    if now_ph() <= expires:
                        conn.close()
                        flash('Code verified! Enter your new password.', 'success')
                        return render_template('forgot_password.html', show_password_input=True, email=email, code=code)
                    else:
                        conn.close()
                        flash('Verification code has expired. Please request a new one.', 'danger')
                        return redirect(url_for('forgot_password'))
                else:
                    conn.close()
                    flash('Invalid verification code. Please try again.', 'danger')
                    return render_template('forgot_password.html', show_code_input=True, email=email, code='')
            
            elif step == 'reset_password':
                code = request.form.get('code', '').strip()
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')
                
                if not new_password or not confirm_password:
                    flash('Please enter both password fields.', 'danger')
                    conn.close()
                    return render_template('forgot_password.html', show_password_input=True, email=email, code=code)
                
                if new_password != confirm_password:
                    flash('Passwords do not match!', 'danger')
                    conn.close()
                    return render_template('forgot_password.html', show_password_input=True, email=email, code=code)
                
                # ONLY check registered email (not backup email)
                user = conn.execute('SELECT * FROM users WHERE email=? AND password_reset_token=?', 
                                  (email, code)).fetchone()
                
                if user:
                    hashed = generate_password_hash(new_password)
                    # Update password without changing approval status
                    conn.execute('UPDATE users SET password_hash=?, password_reset_token=NULL, password_reset_expires=NULL WHERE id=?',
                                (hashed, user['id']))
                    conn.commit()
                    conn.close()
                    
                    flash('Password reset successful! You can now login with your new password.', 'success')
                    return redirect(url_for('login'))
                else:
                    conn.close()
                    flash('Session expired. Please start over.', 'danger')
                    return redirect(url_for('forgot_password'))
            
            conn.close()
            return redirect(url_for('forgot_password'))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('forgot_password'))
    
    return render_template('forgot_password.html', email='', code='')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE password_reset_token=?', (token,)).fetchone()
    
    if not user:
        flash('Invalid or expired reset link', 'danger')
        conn.close()
        return redirect(url_for('login'))
    
    # Check if token expired
    if user['password_reset_expires']:
        expires = datetime.fromisoformat(user['password_reset_expires'])
        if now_ph() > expires:
            flash('Reset link has expired', 'danger')
            conn.close()
            return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Passwords do not match', 'danger')
            conn.close()
            return redirect(url_for('reset_password', token=token))
        
        # Validate password strength
        is_valid, message = validate_password_strength(new_password)
        if not is_valid:
            flash(message, 'danger')
            conn.close()
            return redirect(url_for('reset_password', token=token))
        
        # Update password and clear reset token
        new_hash = generate_password_hash(new_password)
        conn.execute('UPDATE users SET password_hash=?, password_reset_token=NULL, password_reset_expires=NULL WHERE id=?',
                    (new_hash, user['id']))
        conn.commit()
        conn.close()
        
        flash('Password reset successfully! You can now login.', 'success')
        return redirect(url_for('login'))
    
    conn.close()
    return render_template('reset_password.html')

# Real-time Dashboard API Endpoints
@app.route('/api/admin/applications')
@login_required
def api_admin_applications():
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    applications = conn.execute('''
        SELECT la.*, 
               u1.name as loan_staff_name,
               u2.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u1 ON la.submitted_by = u1.id
        LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
        WHERE la.status IN ('ci_completed', 'approved', 'disapproved')
           OR (la.needs_ci_interview = 0 AND la.status = 'submitted')
        ORDER BY la.submitted_at ASC
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(app) for app in applications])

@app.route('/api/loan/applications')
@login_required
def api_loan_applications():
    if current_user.role != 'loan_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    applications = conn.execute('''
        SELECT la.*, u.name as ci_staff_name 
        FROM loan_applications la
        LEFT JOIN users u ON la.assigned_ci_staff = u.id
        ORDER BY la.submitted_at ASC
    ''').fetchall()
    conn.close()
    
    return jsonify([dict(app) for app in applications])

@app.route('/api/ci/applications')
@login_required
def api_ci_applications():
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = get_db()
    applications = conn.execute('''
        SELECT la.*, u.name as loan_staff_name
        FROM loan_applications la
        LEFT JOIN users u ON la.submitted_by = u.id
        WHERE la.assigned_ci_staff = ?
        ORDER BY la.submitted_at ASC
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return jsonify([dict(app) for app in applications])

# LOAN TYPES MANAGEMENT ROUTES
@app.route('/admin/loan-types')
@login_required
def manage_loan_types():
    if current_user.role != 'admin':
        flash('Unauthorized - Admin access required', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    loan_types = conn.execute('SELECT * FROM loan_types ORDER BY name ASC').fetchall()
    unread_count = conn.execute('''SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"''', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('manage_loan_types.html', loan_types=loan_types, unread_count=unread_count)

@app.route('/api/loan-types')
def get_loan_types():
    """Get all active loan types for dropdowns - Public API for submit form"""
    conn = get_db()
    loan_types = conn.execute('SELECT id, name FROM loan_types WHERE is_active=1 ORDER BY name ASC').fetchall()
    conn.close()
    return jsonify([{'id': lt['id'], 'name': lt['name']} for lt in loan_types])

@app.route('/api/loan-types/add', methods=['POST'])
@login_required
def add_loan_type():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    
    conn = get_db()
    try:
        conn.execute('INSERT INTO loan_types (name, description) VALUES (?, ?)', (name, description))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Loan type added successfully'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'error': 'Loan type already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/loan-types/update/<int:id>', methods=['POST'])
@login_required
def update_loan_type(id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'success': False, 'error': 'Name is required'}), 400
    
    conn = get_db()
    try:
        conn.execute('UPDATE loan_types SET name=?, description=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', 
                    (name, description, id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Loan type updated successfully'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'success': False, 'error': 'Loan type name already exists'}), 400
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/loan-types/toggle/<int:id>', methods=['POST'])
@login_required
def toggle_loan_type(id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db()
    loan_type = conn.execute('SELECT is_active FROM loan_types WHERE id=?', (id,)).fetchone()
    
    if not loan_type:
        conn.close()
        return jsonify({'success': False, 'error': 'Loan type not found'}), 404
    
    new_status = 0 if loan_type['is_active'] == 1 else 1
    conn.execute('UPDATE loan_types SET is_active=?, updated_at=CURRENT_TIMESTAMP WHERE id=?', (new_status, id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Loan type status updated', 'is_active': new_status})

@app.route('/api/loan-types/delete/<int:id>', methods=['POST'])
@login_required
def delete_loan_type(id):
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db()
    try:
        conn.execute('DELETE FROM loan_types WHERE id=?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Loan type deleted successfully'})
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'error': str(e)}), 500

# Autocomplete API Endpoints - Auto-fill from previous applications
@app.route('/api/autocomplete/names', methods=['GET'])
@login_required
def autocomplete_names():
    """Get member names matching query"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT member_name, member_contact, member_address
        FROM loan_applications
        WHERE member_name LIKE ? 
        ORDER BY submitted_at DESC
        LIMIT 10
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    suggestions = [{
        'value': row['member_name'],
        'context': f"{row['member_contact']} - {row['member_address'][:50]}..." if row['member_address'] else row['member_contact']
    } for row in results]
    
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/contacts', methods=['GET'])
@login_required
def autocomplete_contacts():
    """Get contact numbers matching query"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT member_contact, member_name
        FROM loan_applications
        WHERE member_contact LIKE ?
        ORDER BY submitted_at DESC
        LIMIT 10
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    suggestions = [{
        'value': row['member_contact'],
        'context': row['member_name']
    } for row in results if row['member_contact']]
    
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/addresses', methods=['GET'])
@login_required
def autocomplete_addresses():
    """Get addresses matching query"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT member_address, member_name
        FROM loan_applications
        WHERE member_address LIKE ?
        ORDER BY submitted_at DESC
        LIMIT 10
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    suggestions = [{
        'value': row['member_address'],
        'context': row['member_name']
    } for row in results if row['member_address']]
    
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/member_details', methods=['GET'])
@login_required
def autocomplete_member_details():
    """Get full member details by name for auto-fill"""
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'error': 'Name required'})
    
    conn = get_db()
    # Get most recent application for this member
    result = conn.execute('''
        SELECT member_name, member_contact, member_address
        FROM loan_applications
        WHERE member_name = ?
        ORDER BY submitted_at DESC
        LIMIT 1
    ''', (name,)).fetchone()
    conn.close()
    
    if result:
        return jsonify({
            'success': True,
            'details': {
                'name': result['member_name'],
                'contact': result['member_contact'],
                'address': result['member_address']
            }
        })
    
    return jsonify({'success': False, 'error': 'Member not found'})

@app.route('/api/autocomplete/last_names', methods=['GET'])
@login_required
def autocomplete_last_names():
    """Get last names from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    # Search in ci_checklist_data JSON field
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    last_names = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'applicant_last_name' in data and query.lower() in data['applicant_last_name'].lower():
                last_names.add(data['applicant_last_name'])
            if 'spouse_last_name' in data and query.lower() in data['spouse_last_name'].lower():
                last_names.add(data['spouse_last_name'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(last_names)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/first_names', methods=['GET'])
@login_required
def autocomplete_first_names():
    """Get first names from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    first_names = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'applicant_first_name' in data and query.lower() in data['applicant_first_name'].lower():
                first_names.add(data['applicant_first_name'])
            if 'spouse_first_name' in data and query.lower() in data['spouse_first_name'].lower():
                first_names.add(data['spouse_first_name'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(first_names)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/middle_names', methods=['GET'])
@login_required
def autocomplete_middle_names():
    """Get middle names from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    middle_names = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'applicant_middle_name' in data and query.lower() in data['applicant_middle_name'].lower():
                middle_names.add(data['applicant_middle_name'])
            if 'spouse_middle_name' in data and query.lower() in data['spouse_middle_name'].lower():
                middle_names.add(data['spouse_middle_name'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(middle_names)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/barangays', methods=['GET'])
@login_required
def autocomplete_barangays():
    """Get barangays from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    barangays = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'barangay' in data and query.lower() in data['barangay'].lower():
                barangays.add(data['barangay'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(barangays)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/municipalities', methods=['GET'])
@login_required
def autocomplete_municipalities():
    """Get municipalities from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    municipalities = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'municipality' in data and query.lower() in data['municipality'].lower():
                municipalities.add(data['municipality'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(municipalities)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

@app.route('/api/autocomplete/provinces', methods=['GET'])
@login_required
def autocomplete_provinces():
    """Get provinces from CI checklist data"""
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'success': True, 'suggestions': []})
    
    conn = get_db()
    results = conn.execute('''
        SELECT DISTINCT ci_checklist_data
        FROM loan_applications
        WHERE ci_checklist_data IS NOT NULL
        AND ci_checklist_data LIKE ?
        LIMIT 20
    ''', (f'%{query}%',)).fetchall()
    conn.close()
    
    provinces = set()
    for row in results:
        try:
            import json
            data = json.loads(row['ci_checklist_data'])
            if 'province' in data and query.lower() in data['province'].lower():
                provinces.add(data['province'])
        except:
            pass
    
    suggestions = [{'value': name, 'context': ''} for name in sorted(provinces)[:10]]
    return jsonify({'success': True, 'suggestions': suggestions})

# SMS Templates Management Routes
@app.route('/manage_sms_templates')
@login_required
def manage_sms_templates():
    """Manage SMS templates page"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    try:
        # Check if sms_templates table exists
        table_check = conn.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='sms_templates'
        ''').fetchone()
        
        if not table_check:
            # Create sms_templates table
            conn.execute('''
                CREATE TABLE sms_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('approved', 'disapproved', 'deferred', 'custom')),
                    message TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            flash('SMS Templates system initialized successfully!', 'success')
        
        # Get all templates
        templates = conn.execute('''
            SELECT * FROM sms_templates 
            ORDER BY category, name
        ''').fetchall()
        
        # Categorize templates
        approved_templates = [t for t in templates if t['category'] == 'approved']
        disapproved_templates = [t for t in templates if t['category'] == 'disapproved']
        deferred_templates = [t for t in templates if t['category'] == 'deferred']
        custom_templates = [t for t in templates if t['category'] == 'custom']
        
        # Get counts
        approved_count = len(approved_templates)
        disapproved_count = len(disapproved_templates)
        deferred_count = len(deferred_templates)
        custom_count = len(custom_templates)
        
        unread_count = conn.execute('''
            SELECT COUNT(*) as count FROM notifications 
            WHERE user_id=? AND is_read=0 AND message NOT LIKE "New message from%"
        ''', (current_user.id,)).fetchone()['count']
        
        conn.close()
        
        return render_template('manage_sms_templates.html', 
                             templates=templates,
                             approved_templates=approved_templates,
                             disapproved_templates=disapproved_templates,
                             deferred_templates=deferred_templates,
                             custom_templates=custom_templates,
                             approved_count=approved_count,
                             disapproved_count=disapproved_count,
                             deferred_count=deferred_count,
                             custom_count=custom_count,
                             unread_count=unread_count)
    
    except Exception as e:
        conn.close()
        flash(f'Error loading SMS templates: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

@app.route('/api/get_sms_templates/<category>')
@login_required
def get_sms_templates(category):
    """Get SMS templates by category (approved, disapproved, deferred)"""
    conn = get_db()
    templates = conn.execute('''
        SELECT id, name, message, category 
        FROM sms_templates 
        WHERE category = ? AND is_active = 1
        ORDER BY name
    ''', (category,)).fetchall()
    conn.close()
    
    return jsonify({
        'success': True,
        'templates': [dict(t) for t in templates]
    })

@app.route('/send_sms_and_update_status/<int:app_id>', methods=['POST'])
@login_required
def send_sms_and_update_status(app_id):
    """Send SMS and update application status (approve/disapprove/defer)"""
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        action = data.get('action')  # 'approved', 'disapproved', or 'deferred'
        message = data.get('message', '').strip()
        notes = data.get('notes', '').strip()
        
        if not action or action not in ['approved', 'disapproved', 'deferred']:
            return jsonify({'success': False, 'error': 'Invalid action'}), 400
        
        if not message:
            return jsonify({'success': False, 'error': 'SMS message is required'}), 400
        
        conn = get_db()
        
        # Get application details
        app_data = conn.execute('''
            SELECT * FROM loan_applications WHERE id = ?
        ''', (app_id,)).fetchone()
        
        if not app_data:
            conn.close()
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Update application status
        conn.execute('''
            UPDATE loan_applications 
            SET status = ?, admin_notes = ?, admin_decision_at = ?
            WHERE id = ?
        ''', (action, notes, now_ph().isoformat(), app_id))
        
        conn.commit()
        conn.close()
        
        # Send SMS notification
        if app_data['member_contact']:
            sms_sent = send_sms(app_data['member_contact'], message)
            if not sms_sent:
                print(f"Warning: SMS failed to send to {app_data['member_contact']}")
        
        # Emit real-time update
        socketio.emit('application_updated', {
            'id': app_id,
            'status': action,
            'member_name': app_data['member_name'],
            'loan_amount': float(app_data['loan_amount']),
            'timestamp': now_ph().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': f'Application {action} and SMS sent successfully'
        })
        
    except Exception as e:
        print(f"Error in send_sms_and_update_status: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/send_bulk_sms', methods=['POST'])
@login_required
def send_bulk_sms_route():
    """Send SMS to multiple phone numbers at once"""
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        phone_numbers = data.get('phone_numbers', '')  # Comma-separated or list
        message = data.get('message', '').strip()
        
        if not phone_numbers:
            return jsonify({'success': False, 'error': 'Phone numbers are required'}), 400
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        # Send bulk SMS
        results = send_bulk_sms(phone_numbers, message)
        
        return jsonify({
            'success': True,
            'results': results,
            'message': f'Sent to {results["success"]} of {results["total"]} numbers'
        })
        
    except Exception as e:
        print(f"Error in send_bulk_sms_route: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add_sms_template', methods=['POST'])
@login_required
def add_sms_template():
    """Add new SMS template"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    try:
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        message = request.form.get('message', '').strip()
        
        if not name or not category or not message:
            flash('All fields are required', 'danger')
            return redirect(url_for('manage_sms_templates'))
        
        conn = get_db()
        
        # Check if template with same name already exists
        existing = conn.execute('SELECT id FROM sms_templates WHERE name = ? AND category = ?', (name, category)).fetchone()
        if existing:
            conn.close()
            flash(f'Template "{name}" already exists in {category} category', 'warning')
            return redirect(url_for('manage_sms_templates'))
        
        conn.execute('''
            INSERT INTO sms_templates (name, category, message, is_active)
            VALUES (?, ?, ?, 1)
        ''', (name, category, message))
        conn.commit()
        conn.close()
        
        flash('SMS template added successfully', 'success')
        return redirect(url_for('manage_sms_templates'))
        
    except Exception as e:
        print(f"Error adding SMS template: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error adding template: {str(e)}', 'danger')
        return redirect(url_for('manage_sms_templates'))

@app.route('/update_sms_template', methods=['POST'])
@login_required
def update_sms_template():
    """Update existing SMS template"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    try:
        template_id = request.form.get('template_id')
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        message = request.form.get('message', '').strip()
        
        if not template_id or not name or not category or not message:
            flash('All fields are required', 'danger')
            return redirect(url_for('manage_sms_templates'))
        
        conn = get_db()
        
        # Check if template exists
        existing = conn.execute('SELECT id FROM sms_templates WHERE id = ?', (template_id,)).fetchone()
        if not existing:
            conn.close()
            flash('Template not found', 'danger')
            return redirect(url_for('manage_sms_templates'))
        
        conn.execute('''
            UPDATE sms_templates 
            SET name = ?, category = ?, message = ?
            WHERE id = ?
        ''', (name, category, message, template_id))
        conn.commit()
        conn.close()
        
        flash('SMS template updated successfully', 'success')
        return redirect(url_for('manage_sms_templates'))
        
    except Exception as e:
        print(f"Error updating SMS template: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f'Error updating template: {str(e)}', 'danger')
        return redirect(url_for('manage_sms_templates'))

@app.route('/delete_sms_template/<int:template_id>', methods=['POST'])
@login_required
def delete_sms_template(template_id):
    """Delete SMS template"""
    if current_user.role not in ['admin', 'loan_officer']:
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    conn.execute('DELETE FROM sms_templates WHERE id = ?', (template_id,))
    conn.commit()
    conn.close()
    
    flash('SMS template deleted successfully', 'success')
    return redirect(url_for('manage_sms_templates'))

@app.route('/toggle_sms_template/<int:template_id>', methods=['POST'])
@login_required
def toggle_sms_template(template_id):
    """Toggle SMS template active status"""
    if current_user.role not in ['admin', 'loan_officer']:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    conn = get_db()
    template = conn.execute('SELECT is_active FROM sms_templates WHERE id = ?', (template_id,)).fetchone()
    
    if not template:
        conn.close()
        return jsonify({'success': False, 'error': 'Template not found'}), 404
    
    new_status = 0 if template['is_active'] else 1
    conn.execute('UPDATE sms_templates SET is_active = ? WHERE id = ?', (new_status, template_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'is_active': new_status})

if __name__ == '__main__':
    import os
    
    # Create required folders if they don't exist
    folders = [
        app.config['UPLOAD_FOLDER'],
        app.config['SIGNATURE_FOLDER'],
        'message_attachments',
        'voice_messages'
    ]
    
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created folder: {folder}")
    
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 to accept connections from all interfaces
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
