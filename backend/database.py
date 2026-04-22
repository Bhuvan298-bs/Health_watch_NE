"""
Database setup and models for the Health Monitoring System.
Uses SQLite with raw SQL for simplicity.
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "health_monitor.db")


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Initialize database with all tables."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript("""
    -- Users table (all roles)
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'worker', 'user', 'developer')),
        phone TEXT,
        village TEXT,
        district TEXT,
        state TEXT DEFAULT 'Northeast India',
        is_approved INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        is_blocked INTEGER DEFAULT 0,
        blocked_reason TEXT,
        blocked_at TIMESTAMP,
        blocked_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        FOREIGN KEY (blocked_by) REFERENCES users(id)
    );

    -- Health Reports submitted by workers
    CREATE TABLE IF NOT EXISTS health_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        patient_name TEXT NOT NULL,
        patient_age INTEGER,
        patient_gender TEXT,
        village TEXT NOT NULL,
        district TEXT NOT NULL,
        symptoms TEXT NOT NULL,
        disease_suspected TEXT,
        water_source TEXT,
        water_source_type TEXT,
        severity TEXT DEFAULT 'low' CHECK(severity IN ('low', 'medium', 'high', 'critical')),
        notes TEXT,
        photo_path TEXT,
        is_flagged INTEGER DEFAULT 0,
        flag_reason TEXT,
        latitude REAL,
        longitude REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_id) REFERENCES users(id)
    );

    -- Symptom reports from public users
    CREATE TABLE IF NOT EXISTS symptom_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        village TEXT NOT NULL,
        district TEXT NOT NULL,
        symptoms TEXT NOT NULL,
        duration_days INTEGER,
        water_source TEXT,
        is_anonymous INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Alerts & Notifications
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        alert_level TEXT DEFAULT 'green' CHECK(alert_level IN ('green', 'yellow', 'red')),
        target_village TEXT,
        target_district TEXT,
        is_global INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );

    -- Notifications for individual users
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        notification_type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Water Sources tracking
    CREATE TABLE IF NOT EXISTS water_sources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        source_type TEXT NOT NULL,
        village TEXT NOT NULL,
        district TEXT NOT NULL,
        status TEXT DEFAULT 'safe' CHECK(status IN ('safe', 'warning', 'contaminated')),
        last_tested TIMESTAMP,
        report_count INTEGER DEFAULT 0,
        contamination_score REAL DEFAULT 0.0,
        latitude REAL,
        longitude REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- AI Predictions log
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        village TEXT NOT NULL,
        district TEXT NOT NULL,
        risk_level TEXT NOT NULL CHECK(risk_level IN ('green', 'yellow', 'red')),
        risk_score REAL NOT NULL,
        factors TEXT,
        prediction_date DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Notices / Community Feed
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        notice_type TEXT DEFAULT 'general',
        target_village TEXT,
        target_district TEXT,
        is_global INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );

    -- User Activity Sessions (for monitoring)
    CREATE TABLE IF NOT EXISTS user_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        logout_time TIMESTAMP,
        duration_minutes INTEGER,
        ip_address TEXT,
        user_agent TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Error Logs
    CREATE TABLE IF NOT EXISTS error_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        error_type TEXT NOT NULL,
        error_message TEXT NOT NULL,
        endpoint TEXT,
        user_id INTEGER,
        stack_trace TEXT,
        severity TEXT DEFAULT 'low' CHECK(severity IN ('low', 'medium', 'high', 'critical')),
        is_resolved INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Feedback from Users/Workers/Admins
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user_id INTEGER NOT NULL,
        from_role TEXT NOT NULL,
        feedback_text TEXT NOT NULL,
        feedback_type TEXT DEFAULT 'general' CHECK(feedback_type IN ('bug', 'feature', 'general', 'urgent')),
        page_or_feature TEXT,
        is_resolved INTEGER DEFAULT 0,
        dev_response TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP,
        FOREIGN KEY (from_user_id) REFERENCES users(id)
    );

    -- Developer Notices (broadcast to all)
    CREATE TABLE IF NOT EXISTS dev_notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        notice_type TEXT DEFAULT 'info' CHECK(notice_type IN ('info', 'warning', 'maintenance', 'urgent')),
        target_roles TEXT DEFAULT 'all',
        created_by INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        FOREIGN KEY (created_by) REFERENCES users(id)
    );

    -- Track failed secret code attempts
    CREATE TABLE IF NOT EXISTS secret_code_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        user_email TEXT NOT NULL,
        user_role TEXT NOT NULL,
        attempt_count INTEGER DEFAULT 1,
        blocked INTEGER DEFAULT 0,
        blocked_at TIMESTAMP,
        last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Log deletion history
    CREATE TABLE IF NOT EXISTS log_deletions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deleted_by INTEGER NOT NULL,
        log_type TEXT NOT NULL,
        log_count INTEGER,
        deletion_reason TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (deleted_by) REFERENCES users(id)
    );

    -- User Profiles with photos
    CREATE TABLE IF NOT EXISTS user_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        bio TEXT,
        photo_path TEXT,
        profile_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        days_active INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    -- Worker Messages to Admin
    CREATE TABLE IF NOT EXISTS worker_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        worker_id INTEGER NOT NULL,
        admin_id INTEGER,
        message_text TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        read_at TIMESTAMP,
        replied_at TIMESTAMP,
        reply_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (worker_id) REFERENCES users(id),
        FOREIGN KEY (admin_id) REFERENCES users(id)
    );

    -- Create default admin if not exists
    INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role, is_approved, village, district)
    VALUES ('admin', 'admin@health.gov.in', 'NEEDS_SETUP', 'System Administrator', 'admin', 1, 'HQ', 'Guwahati');
    """)

    conn.commit()
    
    # Add rating column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE feedback ADD COLUMN rating INTEGER DEFAULT 5 CHECK(rating BETWEEN 1 AND 5)")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    # Add blocking columns to users table if they don't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN blocked_reason TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN blocked_at TIMESTAMP")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN blocked_by INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.close()
    print("[OK] Database initialized successfully!")


if __name__ == "__main__":
    init_db()
