from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, send_from_directory, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import uuid
import mimetypes
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import resend
from offline_interview_api import (
    offline_interview_bp,
    ensure_offline_migrations,
    upsert_offline_package_row_after_complete,
)
from mobile_api import mobile_api_bp, _verify as mobile_verify_token, json_login_handler

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Single absolute paths so Gunicorn/Render cwd never splits SQLite vs. offline blueprint or uploads.
_FLASK_ROOT = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(_FLASK_ROOT, 'app.db')

app.secret_key = os.getenv('SECRET_KEY', 'replace-this-with-a-secure-random-secret')
app.config['UPLOAD_FOLDER'] = os.path.join(_FLASK_ROOT, 'uploads')
app.config['SIGNATURE_FOLDER'] = os.path.join(_FLASK_ROOT, 'signatures')
app.config['MAX_CONTENT_LENGTH'] = 48 * 1024 * 1024  # offline evidence bundles
# DEBUG=True in production can destabilize workers behind Render/nginx and cause 502s.
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', '').strip().lower() in ('1', 'true', 'yes')
app.config['DATABASE'] = DATABASE

# Stay logged in across WebView tabs, camera/gallery, long field visits (defaults: 90-day remember cookie).
try:
    _SESSION_DAYS = max(1, min(365, int(os.environ.get('SESSION_REMEMBER_DAYS', '90'))))
except ValueError:
    _SESSION_DAYS = 90
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=_SESSION_DAYS)
# Sliding expiration: each request pushes session end forward so active staff are not cut off mid-interview.
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
_is_production = (
    os.environ.get('RENDER', '').lower() in ('1', 'true', 'yes')
    or os.environ.get('FLASK_ENV', '').lower() == 'production'
)
if _is_production:
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configure Resend
resend.api_key = os.getenv('RESEND_API_KEY')

socketio = SocketIO(app, cors_allowed_origins="*")

# Track online users
online_users = {}  # {user_id: {'name': name, 'role': role, 'last_seen': timestamp}}

# Serve static files for PWA
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Bundled CI offline dashboard (prefer static snapshot; fallback to sibling Android assets for dev)
_STATIC_OFFLINE_SHELL = os.path.join(_FLASK_ROOT, 'static', 'ci_offline_shell.html')
_OFFLINE_SHELL_ASSET_LEGACY = os.path.normpath(
    os.path.join(_FLASK_ROOT, '..', 'app', 'src', 'main', 'assets', 'offline.html')
)


@app.route('/ci/offline_shell')
def ci_offline_shell():
    """Serve offline.html over HTTPS so session cookies apply to API uploads."""
    for path in (_STATIC_OFFLINE_SHELL, _OFFLINE_SHELL_ASSET_LEGACY):
        if os.path.isfile(path):
            return send_file(path, max_age=0, mimetype='text/html; charset=utf-8')
    return ('Offline shell asset is not present on this server build.', 404)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.remember_cookie_duration = timedelta(days=_SESSION_DAYS)
# Default "basic" protection ties the session to User-Agent. Our WebView switches UA for desktop mode,
# which can look like a new client and force a re-login during a long CI interview.
login_manager.session_protection = False
login_manager.init_app(app)


@app.before_request
def _keep_session_sliding_for_authenticated_users():
    """Ensure every authenticated hit refreshes the long-lived session (see SESSION_REFRESH_EACH_REQUEST)."""
    if current_user.is_authenticated:
        session.permanent = True

class User(UserMixin):
    def __init__(self, id, email, name, role, signature_path=None, backup_email=None):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.signature_path = signature_path
        self.backup_email = backup_email

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

def get_db():
    conn = sqlite3.connect(DATABASE, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
    except sqlite3.Error:
        pass
    return conn


def ci_staff_assignee_matches(assigned_ci_staff, user_id):
    """SQLite may return int or str; avoid false 'not your application' redirects."""
    if assigned_ci_staff is None or user_id is None:
        return False
    try:
        return int(assigned_ci_staff) == int(user_id)
    except (TypeError, ValueError):
        return False


def user_may_access_loan_documents(app_row):
    """Allow admin, assigned CI staff, or the loan staff who submitted the application."""
    if not app_row:
        return False
    r = current_user.role
    uid = current_user.id
    if r == 'admin':
        return True
    if r == 'ci_staff' and app_row['assigned_ci_staff'] is not None and int(app_row['assigned_ci_staff']) == int(uid):
        return True
    if r == 'loan_staff' and app_row['submitted_by'] is not None and int(app_row['submitted_by']) == int(uid):
        return True
    return False


def init_db():
    """Initialize database if it doesn't exist"""
    os.makedirs(os.path.join(_FLASK_ROOT, 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(_FLASK_ROOT, 'signatures'), exist_ok=True)
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        schema_path = os.path.join(_FLASK_ROOT, 'schema.sql')
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        
        # Create demo users
        from werkzeug.security import generate_password_hash
        admin_hash = generate_password_hash('admin123')
        loan_hash = generate_password_hash('loan123')
        ci_hash = generate_password_hash('ci123')
        
        conn.execute('INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)',
                     ('admin@dccco.test', admin_hash, 'Admin User', 'admin'))
        conn.execute('INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)',
                     ('loan@dccco.test', loan_hash, 'Loan Staff', 'loan_staff'))
        conn.execute('INSERT INTO users (email, password_hash, name, role) VALUES (?, ?, ?, ?)',
                     ('ci@dccco.test', ci_hash, 'CI Staff', 'ci_staff'))
        
        conn.commit()
        conn.close()

# Initialize database on startup
init_db()

with app.app_context():
    ensure_offline_migrations()
app.register_blueprint(offline_interview_bp)
app.register_blueprint(mobile_api_bp)

# Native Android JSON login — mounted on the app so /api/login is always bound (not only via blueprint).
app.add_url_rule(
    "/api/login",
    "api_json_login",
    json_login_handler,
    methods=["GET", "POST"],
)


@app.route('/health')
def health():
    """Lightweight check for load balancers (Render, nginx). Does not touch SQLite."""
    return jsonify({'ok': True}), 200

def _emit_new_notification_socket(user_id, message):
    try:
        socketio.emit('new_notification', {'message': message}, room=str(user_id))
    except Exception:
        pass


def create_notification(user_id, message, link=None):
    try:
        conn = get_db()
        conn.execute('INSERT INTO notifications (user_id, message, link) VALUES (?, ?, ?)',
                     (user_id, message, link))
        conn.commit()
        conn.close()
        try:
            socketio.start_background_task(_emit_new_notification_socket, user_id, message)
        except (AttributeError, RuntimeError):
            _emit_new_notification_socket(user_id, message)
    except Exception as e:
        pass

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    conn.close()
    if row:
        backup_email = row['backup_email'] if 'backup_email' in row.keys() else None
        return User(row['id'], row['email'], row['name'], row['role'], row['signature_path'], backup_email)
    return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
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
                       row['backup_email'] if 'backup_email' in row.keys() else None)
            # Remember persists login in WebView/mobile (camera, other apps); avoids “random logout”.
            session.permanent = True
            login_user(user, remember=True, duration=timedelta(days=_SESSION_DAYS))
            flash('Logged in successfully.', 'success')
            return redirect(url_for('index'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.', 'info')
    return redirect(url_for('login'))


def _sanitize_mobile_web_next(next_raw):
    """
    Only allow same-origin relative paths so ?next= cannot become an open redirect.
    """
    if not next_raw or not isinstance(next_raw, str):
        return '/loan/dashboard'
    s = next_raw.strip()
    if not s.startswith('/') or s.startswith('//') or '\n' in s or '\r' in s:
        return '/loan/dashboard'
    return s


@app.route('/api/session_bridge', methods=['GET', 'OPTIONS'])
def api_session_bridge():
    """
    Promote a native (Bearer token) login into a Flask-Login cookie session inside the WebView.

    Clients should call GET with Authorization: Bearer <token> (no-follow redirect),
    apply Set-Cookie via CookieManager, then navigate the WebView to the matching path.
    """
    if request.method == 'OPTIONS':
        return ('', 204)

    auth = request.headers.get('Authorization', '').strip()
    if not auth.lower().startswith('bearer '):
        return jsonify({'error': 'missing_token'}), 401

    payload = mobile_verify_token(auth[7:].strip())
    if not payload:
        return jsonify({'error': 'invalid_token'}), 401

    if int(time.time()) - int(payload.get('iat', 0)) > 60 * 60 * 24 * 30:
        return jsonify({'error': 'expired_token'}), 401

    uid = int(payload['sub'])
    conn = get_db()
    row = conn.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'not_found'}), 404
    if row['is_approved'] == 0:
        return jsonify({'error': 'pending_approval'}), 403

    backup_email = row['backup_email'] if 'backup_email' in row.keys() else None
    user = User(
        row['id'], row['email'], row['name'], row['role'], row['signature_path'],
        backup_email
    )
    session.permanent = True
    login_user(user, remember=True, duration=timedelta(days=_SESSION_DAYS))

    safe_next = _sanitize_mobile_web_next(request.args.get('next'))
    return redirect(safe_next)


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
        ORDER BY la.submitted_at DESC
    ''').fetchall()
    
    # Get all CI staff for the dropdown
    ci_staff_list = conn.execute('''
        SELECT id, name, email 
        FROM users 
        WHERE role='ci_staff' 
        ORDER BY name ASC
    ''').fetchall()
    
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('loan_dashboard.html', applications=applications, unread_count=unread_count, ci_staff_list=ci_staff_list)

@app.route('/notifications/count')
@login_required
def notification_count():
    conn = get_db()
    count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0', 
                        (current_user.id,)).fetchone()['count']
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
    conn.close()
    
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
    conn.close()
    
    return jsonify({'success': True})

@app.route('/loan/submit', methods=['GET','POST'])
@login_required
def submit_application():
    if current_user.role != 'loan_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        member_name = request.form['member_name']
        member_contact = request.form.get('member_contact')
        member_address = request.form.get('member_address')
        loan_amount = request.form.get('loan_amount')
        needs_ci_value = request.form.get('needs_ci', '1')
        
        conn = get_db()
        
        # Check for duplicate member name
        existing = conn.execute('''
            SELECT id, member_name FROM loan_applications 
            WHERE LOWER(member_name) = LOWER(?) 
            AND status NOT IN ('rejected', 'approved')
        ''', (member_name,)).fetchone()
        
        if existing:
            conn.close()
            flash(f'An active application for "{member_name}" already exists (ID: #{existing["id"]}). Please complete or reject the existing application first.', 'warning')
            return redirect(url_for('submit_application'))
        
        # Check if specific CI staff was selected
        specific_ci_id = None
        if needs_ci_value.startswith('ci_'):
            specific_ci_id = int(needs_ci_value.replace('ci_', ''))
            needs_ci = 1
        else:
            needs_ci = int(needs_ci_value)
        try:
            cursor = conn.execute('''
                INSERT INTO loan_applications 
                (member_name, member_contact, member_address, loan_amount, needs_ci_interview, submitted_by)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (member_name, member_contact, member_address, loan_amount, needs_ci, current_user.id))
            app_id = cursor.lastrowid
            
            # Handle file uploads
            if 'documents' in request.files:
                files = request.files.getlist('documents')
                for file in files:
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        unique_filename = f"{app_id}_{uuid.uuid4().hex[:8]}_{filename}"
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(filepath)
                        conn.execute('INSERT INTO documents (loan_application_id, file_name, file_path, uploaded_by) VALUES (?, ?, ?, ?)',
                                   (app_id, filename, filepath, current_user.id))
            
            # Assign to CI staff
            if needs_ci:
                if specific_ci_id:
                    # Assign to specific CI staff
                    ci_staff_id = specific_ci_id
                else:
                    # Auto-assign to CI staff with lowest workload
                    ci_staff = conn.execute('''
                        SELECT id FROM users 
                        WHERE role='ci_staff' AND is_approved=1
                        ORDER BY current_workload ASC 
                        LIMIT 1
                    ''').fetchone()
                    ci_staff_id = ci_staff['id'] if ci_staff else None
                
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
                # Send directly to admin
                admin = conn.execute('SELECT id FROM users WHERE role="admin" LIMIT 1').fetchone()
                conn.commit()
                conn.close()
                if admin:
                    create_notification(admin['id'],
                                      f'New loan application submitted: {member_name}',
                                      f'/admin/application/{app_id}')
            
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('loan_dashboard'))
        except Exception as e:
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
    
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0', 
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
        ORDER BY la.submitted_at DESC
    ''', (current_user.id,)).fetchall()
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('ci_dashboard.html', applications=applications, unread_count=unread_count)

@app.route('/ci/checklist/<int:id>')
@login_required
def ci_checklist(id):
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    conn.close()
    
    if not app_data or not ci_staff_assignee_matches(app_data['assigned_ci_staff'], current_user.id):
        flash('Application not found', 'danger')
        return redirect(url_for('ci_dashboard'))
    
    return render_template('ci_checklist_form.html', application=app_data)

@app.route('/ci/application/<int:id>', methods=['GET','POST'])
@login_required
def ci_application(id):
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    app_data = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    
    if not app_data or not ci_staff_assignee_matches(app_data['assigned_ci_staff'], current_user.id):
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('ci_dashboard'))

    offline_merge = None
    merge_id = request.args.get('merge_offline', type=int)
    if merge_id and request.method == 'GET':
        pkg = conn.execute(
            'SELECT * FROM ci_offline_packages WHERE id = ? AND ci_staff_id = ? AND application_id = ?',
            (merge_id, current_user.id, id)
        ).fetchone()
        if pkg:
            import json as _json
            try:
                pl = _json.loads(pkg['payload_json'] or '{}')
            except Exception:
                pl = {}
            conn.execute(
                "UPDATE ci_offline_packages SET status = 'in_progress', updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), merge_id)
            )
            conn.commit()
            offline_merge = {
                'server_row_id': merge_id,
                'notes': (pl.get('notes') or '').strip(),
                'checklist': pl.get('checklist'),
                'reviewSnapshot': pl.get('reviewSnapshot'),
            }
    
    if request.method == 'POST':
        ci_notes = request.form.get('ci_notes')
        checklist_data = request.form.get('checklist_data')
        signature_data = request.form.get('signature_data')
        prev_status = app_data['status']

        try:
            # Keep existing on-disk signature unless a new canvas snapshot is posted (avoid wiping on every update)
            signature_path_final = app_data['ci_signature']
            if signature_data and signature_data.startswith('data:image'):
                import base64
                signature_base64 = signature_data.split(',')[1]
                signature_bytes = base64.b64decode(signature_base64)
                signature_filename = f"ci_signature_{id}_{uuid.uuid4().hex[:8]}.png"
                signature_path_final = os.path.join(app.config['SIGNATURE_FOLDER'], signature_filename)
                with open(signature_path_final, 'wb') as f:
                    f.write(signature_bytes)

            conn.execute('''
                UPDATE loan_applications 
                SET status=?, ci_notes=?, ci_checklist_data=?, ci_signature=?, ci_completed_at=?
                WHERE id=?
            ''', ('ci_completed', ci_notes, checklist_data, signature_path_final, datetime.now().isoformat(), id))

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

            # Only count toward workload the first time this case moves to CI completed
            if prev_status != 'ci_completed':
                conn.execute('UPDATE users SET current_workload = current_workload - 1 WHERE id=?',
                             (current_user.id,))

            op_done = request.form.get('offline_package_row_id', type=int)
            if op_done:
                try:
                    conn.execute(
                        "UPDATE ci_offline_packages SET status = 'done', updated_at = ? WHERE id = ? AND ci_staff_id = ?",
                        (datetime.now().isoformat(), op_done, current_user.id)
                    )
                except Exception:
                    pass
            elif checklist_data is not None:
                # Website form never hits /api/ci/complete_interview — still queue a row for Offline field saves
                web_row = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
                if web_row:
                    upsert_offline_package_row_after_complete(
                        conn,
                        ci_staff_id=current_user.id,
                        application_id=id,
                        client_request_id=f'website-ci-{id}',
                        ci_notes=ci_notes,
                        checklist_data=checklist_data,
                        app_row=web_row,
                    )

            conn.commit()

            admin = conn.execute('SELECT id FROM users WHERE role="admin" LIMIT 1').fetchone()
            conn.close()

            if admin and prev_status != 'ci_completed':
                create_notification(admin['id'],
                                    f'CI interview completed for: {app_data["member_name"]}',
                                    f'/admin/application/{id}')

            flash('Interview completed and sent to admin!' if prev_status != 'ci_completed' else 'Interview report updated.', 'success')
            return redirect(url_for('ci_dashboard'))
        except Exception as e:
            conn.close()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('ci_application', id=id))
    
    documents = conn.execute('SELECT * FROM documents WHERE loan_application_id=?', (id,)).fetchall()
    messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.loan_application_id=?
        ORDER BY m.sent_at ASC
    ''', (id,)).fetchall()
    
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template(
        'ci_application.html',
        application=app_data,
        documents=documents,
        messages=messages,
        unread_count=unread_count,
        offline_merge=offline_merge
    )


@app.route('/ci/offline_saves')
@login_required
def ci_offline_saves():
    if current_user.role != 'ci_staff':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    conn = get_db()
    packages = conn.execute('''
        SELECT op.id, op.package_id, op.application_id, op.client_request_id, op.status, op.format,
               op.created_at, op.updated_at, la.member_name
        FROM ci_offline_packages op
        JOIN loan_applications la ON la.id = op.application_id
        WHERE op.ci_staff_id = ?
        ORDER BY op.updated_at DESC
    ''', (current_user.id,)).fetchall()
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0',
                                 (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('ci_offline_saves.html', packages=packages, unread_count=unread_count)


# ADMIN ROUTES
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    conn = get_db()
    applications = conn.execute('''
        SELECT la.*, 
               u1.name as loan_staff_name,
               u2.name as ci_staff_name
        FROM loan_applications la
        LEFT JOIN users u1 ON la.submitted_by = u1.id
        LEFT JOIN users u2 ON la.assigned_ci_staff = u2.id
        ORDER BY la.submitted_at DESC
    ''').fetchall()
    
    # Get online CI staff
    ci_staff = conn.execute('''
        SELECT id, name, email, is_online, last_seen
        FROM users 
        WHERE role = 'ci_staff'
        ORDER BY is_online DESC, name ASC
    ''').fetchall()
    
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    return render_template('admin_dashboard.html', applications=applications, ci_staff=ci_staff, unread_count=unread_count)

@app.route('/admin/application/<int:id>', methods=['GET','POST'])
@login_required
def admin_application(id):
    if current_user.role != 'admin':
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
            ''', (decision, admin_notes, datetime.now().isoformat(), id))
            
            conn.commit()
            conn.close()
            
            # Notify loan staff
            create_notification(app_data['submitted_by'],
                              f'Application {decision}: {app_data["member_name"]}',
                              f'/loan/application/{id}')
            
            flash(f'Application {decision}!', 'success')
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
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('admin_application.html', application=app_data, documents=documents, messages=messages, unread_count=unread_count)

# SHARED ROUTES
@app.route('/application/<int:id>')
@login_required
def view_application(id):
    if current_user.role == 'admin':
        return redirect(url_for('admin_application', id=id))
    elif current_user.role == 'ci_staff':
        return redirect(url_for('ci_application', id=id))
    else:
        return redirect(url_for('loan_application', id=id))

@app.route('/loan/application/<int:id>')
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
        WHERE la.id=?
    ''', (id,)).fetchone()
    
    if not app_data:
        flash('Application not found', 'danger')
        conn.close()
        return redirect(url_for('loan_dashboard'))
    
    documents = conn.execute('SELECT * FROM documents WHERE loan_application_id=?', (id,)).fetchall()
    messages = conn.execute('''
        SELECT m.*, u.name as sender_name 
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.loan_application_id=?
        ORDER BY m.sent_at ASC
    ''', (id,)).fetchall()
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0', 
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('loan_application.html', application=app_data, documents=documents, messages=messages, unread_count=unread_count)

@app.route('/messages')
@login_required
def messages():
    conn = get_db()
    
    # Get all staff members for chat
    staff = conn.execute('''
        SELECT id, name, email, role 
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
        user_info = conn.execute('SELECT name, role FROM users WHERE id = ?', (other_id,)).fetchone()
        
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
            'last_message': last_msg['message'] if last_msg else '',
            'last_message_time': last_msg['sent_at'] if last_msg else '',
            'unread_count': unread['count']
        })
    
    # Sort by last message time
    conversations.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    conn.close()
    
    unread_count = sum(conv['unread_count'] for conv in conversations)
    
    return render_template('messages_dark.html', staff=staff, conversations=conversations, unread_count=unread_count)

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
    if current_user.role != 'admin':
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

@app.route('/api/send_direct_message', methods=['POST'])
@login_required
def send_direct_message():
    data = request.json
    receiver_id = data.get('receiver_id')
    message = data.get('message')
    
    if not receiver_id or not message:
        return jsonify({'success': False, 'error': 'Missing data'})
    
    conn = get_db()
    conn.execute('''
        INSERT INTO direct_messages (sender_id, receiver_id, message)
        VALUES (?, ?, ?)
    ''', (current_user.id, receiver_id, message))
    conn.commit()
    
    # Get receiver info for socket notification
    receiver = conn.execute('SELECT * FROM users WHERE id=?', (receiver_id,)).fetchone()
    conn.close()
    
    # Emit socket event
    socketio.emit('new_direct_message', {
        'sender_id': current_user.id,
        'sender_name': current_user.name,
        'receiver_id': receiver_id,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }, room=f'user_{receiver_id}')
    
    return jsonify({'success': True})

@app.route('/api/edit_direct_message', methods=['POST'])
@login_required
def edit_direct_message():
    data = request.json
    message_id = data.get('message_id')
    new_text = data.get('new_text')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id FROM direct_messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('''
            UPDATE direct_messages 
            SET message=?, is_edited=1, edited_at=? 
            WHERE id=?
        ''', (new_text, datetime.now().isoformat(), message_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/api/delete_direct_message', methods=['POST'])
@login_required
def delete_direct_message():
    data = request.json
    message_id = data.get('message_id')
    
    conn = get_db()
    msg = conn.execute('SELECT sender_id FROM direct_messages WHERE id=?', (message_id,)).fetchone()
    
    if msg and msg['sender_id'] == current_user.id:
        conn.execute('UPDATE direct_messages SET is_deleted=1 WHERE id=?', (message_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn.close()
    return jsonify({'success': False, 'error': 'Unauthorized'})

@app.route('/download/<int:doc_id>')
@login_required
def download_document(doc_id):
    conn = get_db()
    doc = conn.execute('SELECT * FROM documents WHERE id=?', (doc_id,)).fetchone()
    if not doc:
        conn.close()
        return jsonify({'error': 'Document not found'}), 404

    app_loan = conn.execute('SELECT * FROM loan_applications WHERE id=?', (doc['loan_application_id'],)).fetchone()
    conn.close()

    if not app_loan or not user_may_access_loan_documents(app_loan):
        return jsonify({'error': 'Forbidden'}), 403

    path = doc['file_path']
    if not path or not os.path.isfile(path):
        return jsonify({'error': 'File not found on server'}), 404

    fname = doc['file_name'] or 'file'
    mime, _ = mimetypes.guess_type(fname)
    if not mime and fname:
        mlow = fname.lower()
        if mlow.endswith(('.jpg', '.jpeg', '.jpe', '.png', '.gif', '.webp', '.bmp', '.heic', '.heif')):
            img_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.jpe': 'image/jpeg', '.png': 'image/png',
                       '.gif': 'image/gif', '.webp': 'image/webp', '.bmp': 'image/bmp', '.heic': 'image/heic', '.heif': 'image/heif'}
            for ext, mt in img_map.items():
                if mlow.endswith(ext):
                    mime = mt
                    break
    # Inline display for images (CI gallery, offline PWA fetch → blob) — attachments for PDF/others
    is_image = bool(mime and mime.startswith('image/'))
    try:
        return send_file(
            path,
            mimetype=mime or 'application/octet-stream',
            as_attachment=not is_image,
            download_name=fname
        )
    except OSError:
        return jsonify({'error': 'Could not read file'}), 500

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
        'timestamp': datetime.now().isoformat()
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
        'timestamp': datetime.now().isoformat()
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
        ''', (new_text, datetime.now().isoformat(), message_id))
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
            'last_seen': datetime.now().isoformat()
        }
        # Update database
        conn = get_db()
        conn.execute('UPDATE users SET last_seen=?, is_online=1 WHERE id=?', 
                    (datetime.now().isoformat(), current_user.id))
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
                    (datetime.now().isoformat(), current_user.id))
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
    out = []
    for app in apps:
        row = dict(app)
        row['documents'] = [
            dict(d)
            for d in conn.execute(
                'SELECT id, file_name, uploaded_at FROM documents WHERE loan_application_id = ? ORDER BY uploaded_at ASC',
                (row['id'],),
            ).fetchall()
        ]
        out.append(row)
    conn.close()
    return jsonify(out)

@app.route('/api/ci_application/<int:id>')
@login_required
def ci_application_api(id):
    if current_user.role != 'ci_staff':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db()
    app = conn.execute('SELECT * FROM loan_applications WHERE id=?', (id,)).fetchone()
    if not app or app['assigned_ci_staff'] is None or int(app['assigned_ci_staff']) != int(current_user.id):
        conn.close()
        return jsonify({'error': 'Not found'}), 404
    documents = conn.execute('SELECT * FROM documents WHERE loan_application_id=?', (id,)).fetchall()
    conn.close()

    return jsonify({
        'application': dict(app) if app else None,
        'documents': [dict(doc) for doc in documents]
    })

# USER REGISTRATION & APPROVAL ROUTES
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([name, email, role, password, confirm_password]):
            flash('All fields are required', 'danger')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('signup'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'danger')
            return redirect(url_for('signup'))
        
        if role not in ['ci_staff', 'loan_staff']:
            flash('Invalid role selected', 'danger')
            return redirect(url_for('signup'))
        
        conn = get_db()
        
        # Check if email already exists
        existing = conn.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if existing:
            flash('Email already registered', 'danger')
            conn.close()
            return redirect(url_for('signup'))
        
        # Create new user (not approved yet)
        try:
            password_hash = generate_password_hash(password)
            conn.execute('''
                INSERT INTO users (email, password_hash, name, role, is_approved, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (email, password_hash, name, role, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            # Notify admin
            admin = conn.execute('SELECT id FROM users WHERE role="admin" LIMIT 1').fetchone()
            conn.close()
            
            if admin:
                create_notification(admin['id'], 
                                  f'New staff registration: {name} ({role.replace("_", " ").title()})',
                                  '/manage_users')
            
            flash('Registration successful! Please wait for admin approval.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            conn.close()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('signup'))
    
    return render_template('signup.html')

@app.route('/manage_users')
@login_required
def manage_users():
    if current_user.role != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    
    # Get pending users
    pending_users = conn.execute('''
        SELECT id, name, email, role, created_at, approval_type
        FROM users
        WHERE is_approved = 0
        ORDER BY created_at DESC
    ''').fetchall()
    
    # Get active users
    active_users = conn.execute('''
        SELECT id, name, email, role, created_at
        FROM users
        WHERE is_approved = 1
        ORDER BY name ASC
    ''').fetchall()
    
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0',
                                (current_user.id,)).fetchone()['count']
    conn.close()
    
    return render_template('manage_users.html', 
                         pending_users=pending_users, 
                         active_users=active_users,
                         unread_count=unread_count)

@app.route('/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    
    if not user:
        flash('User not found', 'danger')
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

@app.route('/reject_user/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
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
    
    flash(f'User {user["name"]} rejected and removed.', 'info')
    return redirect(url_for('manage_users'))

@app.route('/deactivate_user/<int:user_id>', methods=['POST'])
@login_required
def deactivate_user(user_id):
    if current_user.role != 'admin':
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
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters', 'danger')
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
    unread_count = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id=? AND is_read=0',
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
                user = conn.execute('SELECT * FROM users WHERE email=? OR backup_email=?', (email, email)).fetchone()
                
                if user:
                    import random
                    code = str(random.randint(100000, 999999))
                    expires = (datetime.now() + timedelta(minutes=15)).isoformat()
                    
                    conn.execute('UPDATE users SET password_reset_token=?, password_reset_expires=? WHERE id=?',
                                (code, expires, user['id']))
                    conn.commit()
                    conn.close()
                    
                    email_sent = send_verification_email(email, code, user['name'])
                    
                    if email_sent == True:
                        flash('Verification code sent to your email! Check your inbox.', 'success')
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
                
                user = conn.execute('SELECT * FROM users WHERE (email=? OR backup_email=?) AND password_reset_token=?', 
                                  (email, email, code)).fetchone()
                
                if user and user['password_reset_expires']:
                    expires = datetime.fromisoformat(user['password_reset_expires'])
                    if datetime.now() <= expires:
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
                
                user = conn.execute('SELECT * FROM users WHERE (email=? OR backup_email=?) AND password_reset_token=?', 
                                  (email, email, code)).fetchone()
                
                if user:
                    hashed = generate_password_hash(new_password)
                    # Set is_approved to 0 (pending) and approval_type to 'password_reset'
                    conn.execute('UPDATE users SET password_hash=?, password_reset_token=NULL, password_reset_expires=NULL, is_approved=0, approval_type=? WHERE id=?',
                                (hashed, 'password_reset', user['id']))
                    conn.commit()
                    conn.close()
                    
                    flash('Password reset successful! Please wait for admin approval before logging in.', 'success')
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
        if datetime.now() > expires:
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
        
        if len(new_password) < 6:
            flash('Password must be at least 6 characters', 'danger')
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

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    # Bind to 0.0.0.0 to accept connections from all interfaces
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)