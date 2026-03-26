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
        role TEXT NOT NULL CHECK(role IN ('admin', 'worker', 'user')),
        phone TEXT,
        village TEXT,
        district TEXT,
        state TEXT DEFAULT 'Northeast India',
        is_approved INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
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

    -- Create default admin if not exists
    INSERT OR IGNORE INTO users (username, email, password_hash, full_name, role, is_approved, village, district)
    VALUES ('admin', 'admin@health.gov.in', 'NEEDS_SETUP', 'System Administrator', 'admin', 1, 'HQ', 'Guwahati');
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")


if __name__ == "__main__":
    init_db()
