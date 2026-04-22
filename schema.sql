DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS loan_applications;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS loan_types;
DROP TABLE IF EXISTS system_settings;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT CHECK(role IN ('admin', 'loan_officer', 'loan_staff', 'ci_staff') OR role IS NULL),
    signature_path TEXT,
    profile_photo TEXT,
    current_workload INTEGER DEFAULT 0,
    is_approved INTEGER DEFAULT 0,
    is_online INTEGER DEFAULT 0,
    last_seen TEXT,
    backup_email TEXT,
    password_reset_token TEXT,
    password_reset_expires TEXT,
    approval_type TEXT,
    assigned_route TEXT,  -- Can store multiple routes as comma-separated: "route_1,route_2,route_3"
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE loan_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_name TEXT NOT NULL,
    member_contact TEXT,
    member_address TEXT,
    loan_amount REAL,
    loan_type TEXT,
    status TEXT DEFAULT 'submitted' CHECK(status IN ('submitted', 'assigned_to_ci', 'ci_completed', 'approved', 'disapproved', 'deferred')),
    needs_ci_interview INTEGER DEFAULT 1,
    submitted_by INTEGER,
    assigned_ci_staff INTEGER,
    submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    ci_completed_at TEXT,
    admin_decision_at TEXT,
    ci_latitude REAL,
    ci_longitude REAL,
    ci_notes TEXT,
    ci_checklist_data TEXT,
    ci_signature TEXT,
    admin_notes TEXT,
    lps_remarks TEXT,
    FOREIGN KEY (submitted_by) REFERENCES users(id),
    FOREIGN KEY (assigned_ci_staff) REFERENCES users(id)
);

CREATE TABLE documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_application_id INTEGER NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_by INTEGER NOT NULL,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loan_application_id) REFERENCES loan_applications(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_application_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    message TEXT,
    message_type TEXT DEFAULT 'text' CHECK(message_type IN ('text', 'image', 'file', 'voice')),
    file_path TEXT,
    file_name TEXT,
    is_edited INTEGER DEFAULT 0,
    is_deleted INTEGER DEFAULT 0,
    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
    edited_at TEXT,
    FOREIGN KEY (loan_application_id) REFERENCES loan_applications(id),
    FOREIGN KEY (sender_id) REFERENCES users(id)
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE direct_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    message TEXT NOT NULL,
    message_type TEXT DEFAULT 'text',
    file_path TEXT,
    file_name TEXT,
    is_read INTEGER DEFAULT 0,
    sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id),
    FOREIGN KEY (receiver_id) REFERENCES users(id)
);

CREATE TABLE location_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    activity TEXT,
    tracked_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- New table for dynamic loan types
CREATE TABLE loan_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- New table for system settings
CREATE TABLE system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    setting_type TEXT DEFAULT 'text',
    description TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
