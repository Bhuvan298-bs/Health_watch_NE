"""
Main FastAPI application.
Smart Community Health Monitoring & Early Warning System
"""
import os
import json
import shutil
import csv
import io
import time
import httpx
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import get_db, init_db
from backend.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin, require_worker, require_developer,
    verify_verification_code
)
from backend.ai_engine import (
    calculate_village_risk, detect_disease, detect_fake_report,
    analyze_water_source, generate_trend_data, get_health_tips,
    get_safe_water_guide, calculate_symptom_score
)

# ═══ LOGGING CONFIGURATION ═══
# Create logs directory if it doesn't exist
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logging
log_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# File handler with rotation (10MB per file, keep 10 backups)
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'app.log'),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=10,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_formatter)

# Console handler with UTF-8 encoding for Windows compatibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)
# Force UTF-8 encoding for console to handle Unicode characters
if hasattr(console_handler, 'stream'):
    import io
    console_handler.stream = io.TextIOWrapper(
        console_handler.stream.buffer,
        encoding='utf-8',
        errors='replace'
    )

# Root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Get logger for app
app_logger = logging.getLogger('health_monitor')

app = FastAPI(title="Health Monitor API", version="1.0.0")


# Error logging middleware
@app.middleware("http")
async def log_errors_middleware(request: Request, call_next):
    """Middleware to log API errors to database."""
    try:
        response = await call_next(request)
        
        # Log 5xx errors
        if response.status_code >= 500:
            try:
                error_msg = f"Server error: HTTP{response.status_code} on {request.method} {request.url.path}"
                app_logger.error(error_msg)
                db = get_db()
                db.execute("""
                    INSERT INTO error_logs (error_type, error_message, endpoint, severity, stack_trace)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    f"HTTP{response.status_code}",
                    f"Server error on {request.method} {request.url.path}",
                    request.url.path,
                    "high" if response.status_code == 500 else "critical",
                    f"Endpoint: {request.url.path}, Method: {request.method}"
                ))
                db.commit()
                db.close()
            except:
                pass  # Silently fail to avoid breaking request
        
        return response
    except Exception as e:
        # Log unexpected exceptions
        error_msg = f"Exception: {type(e).__name__}: {str(e)} at {request.url.path}"
        app_logger.error(error_msg)
        try:
            db = get_db()
            db.execute("""
                INSERT INTO error_logs (error_type, error_message, endpoint, severity, stack_trace)
                VALUES (?, ?, ?, ?, ?)
            """, (
                type(e).__name__,
                str(e),
                request.url.path,
                "critical",
                f"Exception: {type(e).__name__}: {str(e)}"
            ))
            db.commit()
            db.close()
        except:
            pass
        
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


def _load_env_file(env_path: str):
    """Minimal .env loader without external dependencies."""
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        # Keep app startup resilient even if .env parsing fails.
        pass


ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")
_load_env_file(ENV_PATH)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "ebacecc0a9abdfcb3849094a9b518a5b").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()

# ─── Startup ───
@app.on_event("startup")
async def startup():
    app_logger.info("=" * 60)
    app_logger.info("Starting Health Monitor Application")
    app_logger.info("=" * 60)
    
    init_db()
    app_logger.info("Database initialized successfully")
    
    db = get_db()
    
    # Set default admin password if not set yet
    admin = db.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    if admin and admin["password_hash"] == "NEEDS_SETUP":
        hashed = hash_password("admin123")
        db.execute("UPDATE users SET password_hash=? WHERE username='admin'", (hashed,))
        app_logger.info("Admin password initialized")
    
    # Initialize developer accounts
    developers = [
        {
            'email': 'bhuvan330bhuvi@gmail.com',
            'password': 'Bhuvan#2004',
            'full_name': 'Bhuvan Developer',
            'username': 'dev_bhuvan'
        },
        {
            'email': 'naikprashant837@gmail.com',
            'password': 'Prashant#2004',
            'full_name': 'Prashant Developer',
            'username': 'dev_prashant'
        }
    ]
    
    for dev in developers:
        existing = db.execute("SELECT id FROM users WHERE email=?", (dev['email'],)).fetchone()
        if not existing:
            hashed = hash_password(dev['password'])
            db.execute("""INSERT INTO users (username, email, password_hash, full_name, role, is_approved, is_active)
                         VALUES (?, ?, ?, ?, 'developer', 1, 1)""",
                      (dev['username'], dev['email'], hashed, dev['full_name']))
            app_logger.info(f"Developer account created: {dev['username']} ({dev['email']}))")
    
    db.commit()
    db.close()
    
    app_logger.info("Application startup completed successfully")
    app_logger.info("=" * 60)


# ─── Static Files ───
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# ═══════════════════════════════════════════
# AUTH ROUTES
# ═══════════════════════════════════════════
@app.post("/api/auth/register")
async def register(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    phone: str = Form(""),
    village: str = Form(""),
    district: str = Form("")
):
    db = get_db()
    try:
        existing = db.execute("SELECT id FROM users WHERE username=? OR email=?",
                              (username, email)).fetchone()
        if existing:
            app_logger.warning(f"Registration failed for {username}: Username or email already exists")
            raise HTTPException(400, "Username or email already exists")

        is_approved = 1 if role == "user" else 0
        db.execute("""INSERT INTO users (username, email, password_hash, full_name, role,
                      phone, village, district, is_approved)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (username, email, hash_password(password), full_name,
                    role, phone, village, district, is_approved))
        db.commit()

        msg = "Registration successful!" if role == "user" else "Registration submitted. Awaiting admin approval."
        app_logger.info(f"User registered: {username} ({role}) - Email: {email}")
        return {"message": msg, "role": role, "is_approved": is_approved}
    finally:
        db.close()


@app.post("/api/auth/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    verification_code: str = Form(...)
):
    db = get_db()
    try:
        # Verify the code first
        if not verify_verification_code(verification_code):
            app_logger.warning(f"Login failed for {username}: Invalid verification code")
            raise HTTPException(status_code=401, detail="Invalid or expired verification code")
        
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            app_logger.warning(f"Login failed for {username}: Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Convert Row to dict for safer access
        user = dict(user)
        
        if not user["is_approved"]:
            app_logger.warning(f"Login failed for {username}: Account not approved")
            raise HTTPException(status_code=403, detail="Account pending approval. Please wait for admin to approve.")
        if not user["is_active"]:
            app_logger.warning(f"Login failed for {username}: Account deactivated")
            raise HTTPException(status_code=403, detail="Account has been deactivated")
        if user.get("is_blocked"):
            app_logger.warning(f"Login failed for {username}: Account blocked - {user.get('blocked_reason', 'Unknown reason')}")
            raise HTTPException(status_code=403, detail=f"Account has been blocked. Reason: {user.get('blocked_reason', 'Contact administrator')}")

        db.execute("UPDATE users SET last_login=? WHERE id=?",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"]))
        
        # Log user session
        db.execute("""
            INSERT INTO user_sessions (user_id, login_time)
            VALUES (?, ?)
        """, (user["id"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        
        db.commit()
        app_logger.info(f"User logged in: {username} ({user['role']})")

        token = create_access_token({
            "sub": str(user["id"]),
            "username": user["username"],
            "role": user["role"],
            "full_name": user["full_name"],
            "village": user["village"],
            "district": user["district"]
        })
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "full_name": user["full_name"],
                "village": user["village"],
                "district": user["district"]
            }
        }
    finally:
        db.close()


@app.post("/api/auth/verify-secret-key")
async def verify_secret_key(
    request_data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """Verify admin secret key. Only for admin users."""
    try:
        # Check if user is admin
        if current_user.get("role") != "admin":
            raise HTTPException(403, "Secret key verification is for admin only")
        
        # Get secret key from request
        secret_key = request_data.get("secret_key", "")
        
        # Verify the secret key (8951)
        ADMIN_SECRET_KEY = "8951"
        if secret_key == ADMIN_SECRET_KEY:
            return {"verified": True, "message": "Secret key verified"}
        else:
            raise HTTPException(401, "Invalid secret key")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error verifying secret key: {str(e)}")


# ═══════════════════════════════════════════
# ADMIN ROUTES
# ═══════════════════════════════════════════
@app.get("/api/admin/workers")
async def get_workers(current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        workers = db.execute("""SELECT id, username, email, full_name, phone, village,
                               district, is_approved, is_active, created_at, last_login
                               FROM users WHERE role='worker' ORDER BY created_at DESC""").fetchall()
        return [dict(w) for w in workers]
    finally:
        db.close()


@app.post("/api/admin/workers/{worker_id}/approve")
async def approve_worker(worker_id: int, current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        db.execute("UPDATE users SET is_approved=1 WHERE id=? AND role='worker'", (worker_id,))
        db.commit()
        # Send notification
        db.execute("""INSERT INTO notifications (user_id, title, message, notification_type)
                      VALUES (?, 'Account Approved', 'Your worker account has been approved. You can now login and submit reports.', 'success')""",
                   (worker_id,))
        db.commit()
        return {"message": "Worker approved successfully"}
    finally:
        db.close()


@app.post("/api/admin/workers/{worker_id}/reject")
async def reject_worker(worker_id: int, current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        db.execute("UPDATE users SET is_approved=0, is_active=0 WHERE id=? AND role='worker'", (worker_id,))
        db.commit()
        db.execute("""INSERT INTO notifications (user_id, title, message, notification_type)
                      VALUES (?, 'Account Rejected', 'Your worker account registration has been rejected.', 'error')""",
                   (worker_id,))
        db.commit()
        return {"message": "Worker rejected"}
    finally:
        db.close()


@app.get("/api/admin/reports")
async def get_all_reports(
    district: str = Query(None),
    village: str = Query(None),
    severity: str = Query(None),
    current_user: dict = Depends(require_admin)
):
    db = get_db()
    try:
        query = """SELECT hr.*, u.full_name as worker_name, u.username as worker_username
                   FROM health_reports hr
                   LEFT JOIN users u ON hr.worker_id = u.id WHERE 1=1"""
        params = []
        if district:
            query += " AND hr.district=?"
            params.append(district)
        if village:
            query += " AND hr.village=?"
            params.append(village)
        if severity:
            query += " AND hr.severity=?"
            params.append(severity)
        query += " ORDER BY hr.created_at DESC"
        reports = db.execute(query, params).fetchall()
        return [dict(r) for r in reports]
    finally:
        db.close()


@app.get("/api/admin/dashboard")
async def admin_dashboard(current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        # Counts
        total_reports = db.execute("SELECT COUNT(*) c FROM health_reports").fetchone()["c"]
        total_workers = db.execute("SELECT COUNT(*) c FROM users WHERE role='worker'").fetchone()["c"]
        pending_workers = db.execute("SELECT COUNT(*) c FROM users WHERE role='worker' AND is_approved=0 AND is_active=1").fetchone()["c"]
        total_users = db.execute("SELECT COUNT(*) c FROM users WHERE role='user'").fetchone()["c"]
        total_alerts = db.execute("SELECT COUNT(*) c FROM alerts").fetchone()["c"]
        flagged_reports = db.execute("SELECT COUNT(*) c FROM health_reports WHERE is_flagged=1").fetchone()["c"]

        # Reports by severity
        severity_stats = db.execute("""SELECT severity, COUNT(*) c FROM health_reports
                                       GROUP BY severity""").fetchall()

        # Recent reports
        recent = db.execute("""SELECT hr.*, u.full_name as worker_name
                              FROM health_reports hr LEFT JOIN users u ON hr.worker_id=u.id
                              ORDER BY hr.created_at DESC LIMIT 10""").fetchall()

        # District-wise counts
        district_stats = db.execute("""SELECT district, COUNT(*) c FROM health_reports
                                       GROUP BY district ORDER BY c DESC""").fetchall()

        # Village risk levels
        villages = db.execute("SELECT DISTINCT village, district FROM health_reports").fetchall()
        village_risks = []
        for v in villages:
            v_reports = db.execute("""SELECT * FROM health_reports
                                     WHERE village=? AND created_at >= date('now', '-7 days')""",
                                  (v["village"],)).fetchall()
            risk = calculate_village_risk([dict(r) for r in v_reports])
            village_risks.append({
                "village": v["village"],
                "district": v["district"],
                **risk
            })
        village_risks.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "total_reports": total_reports,
            "total_workers": total_workers,
            "pending_workers": pending_workers,
            "total_users": total_users,
            "total_alerts": total_alerts,
            "flagged_reports": flagged_reports,
            "severity_stats": {s["severity"]: s["c"] for s in severity_stats},
            "recent_reports": [dict(r) for r in recent],
            "district_stats": [dict(d) for d in district_stats],
            "village_risks": village_risks[:20]
        }
    finally:
        db.close()


@app.get("/api/admin/worker-performance")
async def worker_performance(current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        workers = db.execute("""
            SELECT u.id, u.full_name, u.username, u.village, u.district, u.last_login,
                   COUNT(hr.id) as total_reports,
                   SUM(CASE WHEN hr.is_flagged=1 THEN 1 ELSE 0 END) as flagged_reports,
                   SUM(CASE WHEN hr.created_at >= date('now', '-7 days') THEN 1 ELSE 0 END) as weekly_reports,
                   SUM(CASE WHEN hr.created_at >= date('now', '-30 days') THEN 1 ELSE 0 END) as monthly_reports
            FROM users u
            LEFT JOIN health_reports hr ON u.id = hr.worker_id
            WHERE u.role='worker' AND u.is_approved=1
            GROUP BY u.id
            ORDER BY total_reports DESC
        """).fetchall()
        return [dict(w) for w in workers]
    finally:
        db.close()


@app.get("/api/admin/flagged-reports")
async def get_flagged_reports(current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        reports = db.execute("""SELECT hr.*, u.full_name as worker_name
                               FROM health_reports hr
                               LEFT JOIN users u ON hr.worker_id=u.id
                               WHERE hr.is_flagged=1
                               ORDER BY hr.created_at DESC""").fetchall()
        return [dict(r) for r in reports]
    finally:
        db.close()


@app.post("/api/admin/alerts")
async def create_alert(
    title: str = Form(...),
    message: str = Form(...),
    alert_level: str = Form("yellow"),
    target_village: str = Form(""),
    target_district: str = Form(""),
    is_global: int = Form(0),
    current_user: dict = Depends(require_admin)
):
    db = get_db()
    try:
        admin_id = int(current_user["sub"])
        db.execute("""INSERT INTO alerts (title, message, alert_level, target_village,
                      target_district, is_global, created_by)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (title, message, alert_level, target_village, target_district,
                    is_global, admin_id))
        db.commit()

        # Send notifications to affected users
        if is_global:
            users = db.execute("SELECT id FROM users WHERE is_active=1").fetchall()
        elif target_village:
            users = db.execute("SELECT id FROM users WHERE village=? AND is_active=1",
                               (target_village,)).fetchall()
        elif target_district:
            users = db.execute("SELECT id FROM users WHERE district=? AND is_active=1",
                               (target_district,)).fetchall()
        else:
            users = db.execute("SELECT id FROM users WHERE is_active=1").fetchall()

        for u in users:
            db.execute("""INSERT INTO notifications (user_id, title, message, notification_type)
                          VALUES (?, ?, ?, ?)""", (u["id"], title, message, alert_level))
        db.commit()

        return {"message": f"Alert sent to {len(users)} users"}
    finally:
        db.close()


@app.get("/api/admin/alerts")
async def get_admin_alerts(current_user: dict = Depends(require_admin)):
    """Get all alerts created by the current admin."""
    db = get_db()
    try:
        admin_id = int(current_user["sub"])
        alerts = db.execute(
            """SELECT id, title, message, alert_level, target_village, target_district, 
                      is_global, created_at FROM alerts WHERE created_by=? ORDER BY created_at DESC""",
            (admin_id,)
        ).fetchall()
        return {"alerts": [dict(a) for a in alerts]}
    finally:
        db.close()


@app.delete("/api/admin/alerts/{alert_id}")
async def delete_alert(alert_id: int, current_user: dict = Depends(require_admin)):
    """Delete an alert (only if created by the current admin)."""
    db = get_db()
    try:
        admin_id = int(current_user["sub"])
        
        # Check if alert exists and was created by this admin
        alert = db.execute(
            "SELECT created_by FROM alerts WHERE id=?",
            (alert_id,)
        ).fetchone()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        if alert["created_by"] != admin_id:
            raise HTTPException(status_code=403, detail="You can only delete your own alerts")
        
        # Delete the alert
        db.execute("DELETE FROM alerts WHERE id=?", (alert_id,))
        db.commit()
        
        return {"message": "Alert deleted successfully"}
    finally:
        db.close()


@app.post("/api/admin/notices")
async def create_notice(
    title: str = Form(...),
    content: str = Form(...),
    notice_type: str = Form("general"),
    target_village: str = Form(""),
    target_district: str = Form(""),
    is_global: int = Form(1),
    current_user: dict = Depends(require_admin)
):
    db = get_db()
    try:
        admin_id = int(current_user["sub"])
        db.execute("""INSERT INTO notices (title, content, notice_type, target_village,
                      target_district, is_global, created_by)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (title, content, notice_type, target_village, target_district,
                    is_global, admin_id))
        db.commit()
        return {"message": "Notice published successfully"}
    finally:
        db.close()


@app.get("/api/admin/water-sources")
async def get_water_sources(current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        # Get all unique water sources from reports
        sources_from_reports = db.execute("""
            SELECT water_source, water_source_type, village, district,
                   COUNT(*) as report_count,
                   GROUP_CONCAT(severity) as severities
            FROM health_reports
            WHERE water_source IS NOT NULL AND water_source != ''
            GROUP BY water_source, village
            ORDER BY report_count DESC
        """).fetchall()

        results = []
        for s in sources_from_reports:
            s_dict = dict(s)
            # Get linked reports for analysis
            linked = db.execute("""SELECT * FROM health_reports
                                  WHERE water_source=? AND village=?""",
                               (s["water_source"], s["village"])).fetchall()
            analysis = analyze_water_source([dict(r) for r in linked])
            s_dict.update(analysis)
            results.append(s_dict)

        return results
    finally:
        db.close()


@app.get("/api/admin/trends")
async def get_trends(days: int = Query(30), current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        reports = db.execute("SELECT * FROM health_reports ORDER BY created_at").fetchall()
        trend = generate_trend_data([dict(r) for r in reports], days)

        # Disease breakdown
        diseases = db.execute("""SELECT disease_suspected, COUNT(*) c FROM health_reports
                                WHERE disease_suspected IS NOT NULL AND disease_suspected != ''
                                GROUP BY disease_suspected ORDER BY c DESC LIMIT 10""").fetchall()

        return {
            "daily_cases": trend,
            "disease_breakdown": [dict(d) for d in diseases]
        }
    finally:
        db.close()


@app.get("/api/admin/export/csv")
async def export_csv(current_user: dict = Depends(require_admin)):
    db = get_db()
    try:
        reports = db.execute("""SELECT hr.*, u.full_name as worker_name
                               FROM health_reports hr
                               LEFT JOIN users u ON hr.worker_id=u.id
                               ORDER BY hr.created_at DESC""").fetchall()

        output = io.StringIO()
        writer = csv.writer(output)
        if reports:
            writer.writerow(dict(reports[0]).keys())
            for r in reports:
                writer.writerow(dict(r).values())

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=health_reports_{datetime.now().strftime('%Y%m%d')}.csv"}
        )
    finally:
        db.close()


@app.get("/api/admin/integrations/groq-status")
async def groq_status(
    probe: int = Query(0),
    current_user: dict = Depends(require_admin)
):
    """Admin-only status endpoint for Groq configuration and optional connectivity probe."""
    configured = bool(GROQ_API_KEY)
    key_tail = GROQ_API_KEY[-4:] if configured and len(GROQ_API_KEY) >= 4 else ""

    result = {
        "configured": configured,
        "model": GROQ_MODEL,
        "api_key_mask": f"***{key_tail}" if key_tail else "",
        "reachable": None,
        "probe_message": "Probe not requested"
    }

    if not probe:
        return result

    if not configured:
        result["reachable"] = False
        result["probe_message"] = "Groq API key is not configured"
        return result

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "Respond with a single word: ok"},
            {"role": "user", "content": "ping"}
        ],
        "temperature": 0,
        "max_tokens": 6
    }
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        if resp.status_code == 200:
            result["reachable"] = True
            result["probe_message"] = "Groq reachable"
        else:
            result["reachable"] = False
            result["probe_message"] = f"Groq error {resp.status_code}"
    except Exception:
        result["reachable"] = False
        result["probe_message"] = "Unable to reach Groq service"

    return result


# ═══════════════════════════════════════════
# WORKER ROUTES
# ═══════════════════════════════════════════
@app.post("/api/worker/reports")
async def submit_report(
    patient_name: str = Form(...),
    patient_age: int = Form(None),
    patient_gender: str = Form(""),
    village: str = Form(...),
    district: str = Form(...),
    symptoms: str = Form(...),
    disease_suspected: str = Form(""),
    water_source: str = Form(""),
    water_source_type: str = Form(""),
    severity: str = Form("low"),
    notes: str = Form(""),
    photo: UploadFile = File(None),
    current_user: dict = Depends(require_worker)
):
    db = get_db()
    try:
        worker_id = int(current_user["sub"])
        photo_path = ""

        if photo and photo.filename:
            ext = photo.filename.split(".")[-1]
            fname = f"report_{worker_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            fpath = os.path.join(UPLOAD_DIR, fname)
            with open(fpath, "wb") as f:
                content = await photo.read()
                f.write(content)
            photo_path = f"/uploads/{fname}"

        # Auto-detect disease from symptoms
        if not disease_suspected:
            diseases = detect_disease(symptoms)
            if diseases:
                disease_suspected = diseases[0]["disease"]

        db.execute("""INSERT INTO health_reports
                      (worker_id, patient_name, patient_age, patient_gender, village,
                       district, symptoms, disease_suspected, water_source, water_source_type,
                       severity, notes, photo_path)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (worker_id, patient_name, patient_age, patient_gender, village,
                    district, symptoms, disease_suspected, water_source, water_source_type,
                    severity, notes, photo_path))
        db.commit()

        report_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Run fake detection
        worker_reports = db.execute("SELECT * FROM health_reports WHERE worker_id=?",
                                    (worker_id,)).fetchall()
        report = db.execute("SELECT * FROM health_reports WHERE id=?", (report_id,)).fetchone()
        fake_check = detect_fake_report(dict(report), [dict(r) for r in worker_reports])
        if fake_check["is_suspicious"]:
            db.execute("UPDATE health_reports SET is_flagged=1, flag_reason=? WHERE id=?",
                       ("; ".join(fake_check["flags"]), report_id))
            db.commit()

        # Check village risk and auto-create alert if needed
        village_reports = db.execute("""SELECT * FROM health_reports
                                       WHERE village=? AND created_at >= date('now', '-7 days')""",
                                    (village,)).fetchall()
        risk = calculate_village_risk([dict(r) for r in village_reports])

        if risk["risk_level"] == "red":
            # Auto-generate red alert
            existing_alert = db.execute("""SELECT id FROM alerts
                                          WHERE target_village=? AND alert_level='red'
                                          AND created_at >= date('now', '-1 days')""",
                                       (village,)).fetchone()
            if not existing_alert:
                db.execute("""INSERT INTO alerts (title, message, alert_level, target_village,
                             target_district, created_by)
                             VALUES (?, ?, 'red', ?, ?, ?)""",
                           (f"🚨 OUTBREAK ALERT: {village}",
                            f"AI has detected a potential outbreak in {village}. {risk['report_count']} cases in the last 7 days. Risk score: {risk['risk_score']}",
                            village, district, worker_id))
                db.commit()

                # Notify admin
                admins = db.execute("SELECT id FROM users WHERE role='admin'").fetchall()
                for a in admins:
                    db.execute("""INSERT INTO notifications (user_id, title, message, notification_type)
                                 VALUES (?, ?, ?, 'red')""",
                               (a["id"], f"🚨 RED ALERT: {village}",
                                f"Potential outbreak detected! {risk['report_count']} cases, Risk: {risk['risk_score']}"))
                db.commit()

        elif risk["risk_level"] == "yellow":
            existing_alert = db.execute("""SELECT id FROM alerts
                                          WHERE target_village=? AND alert_level IN ('yellow','red')
                                          AND created_at >= date('now', '-1 days')""",
                                       (village,)).fetchone()
            if not existing_alert:
                db.execute("""INSERT INTO alerts (title, message, alert_level, target_village,
                             target_district, created_by)
                             VALUES (?, ?, 'yellow', ?, ?, ?)""",
                           (f"⚠️ Caution: {village}",
                            f"Elevated disease reports in {village}. {risk['report_count']} cases. Monitoring situation.",
                            village, district, worker_id))
                db.commit()

        # Save prediction
        db.execute("""INSERT OR REPLACE INTO predictions (village, district, risk_level, risk_score, factors, prediction_date)
                      VALUES (?, ?, ?, ?, ?, date('now'))""",
                   (village, district, risk["risk_level"], risk["risk_score"],
                    json.dumps(risk["factors"])))
        db.commit()

        return {
            "message": "Report submitted successfully",
            "report_id": report_id,
            "risk_assessment": risk,
            "disease_detection": detect_disease(symptoms),
            "flagged": fake_check["is_suspicious"]
        }
    finally:
        db.close()


@app.post("/api/worker/reports/bulk")
async def bulk_submit(
    reports_json: str = Form(...),
    current_user: dict = Depends(require_worker)
):
    db = get_db()
    try:
        worker_id = int(current_user["sub"])
        reports = json.loads(reports_json)
        submitted = 0

        for r in reports:
            symptoms = r.get("symptoms", "")
            diseases = detect_disease(symptoms)
            disease = diseases[0]["disease"] if diseases else ""

            db.execute("""INSERT INTO health_reports
                          (worker_id, patient_name, patient_age, patient_gender, village,
                           district, symptoms, disease_suspected, water_source, severity, notes)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (worker_id, r.get("patient_name", ""), r.get("patient_age"),
                        r.get("patient_gender", ""), r.get("village", ""),
                        r.get("district", ""), symptoms, disease,
                        r.get("water_source", ""), r.get("severity", "low"),
                        r.get("notes", "")))
            submitted += 1

        db.commit()
        return {"message": f"{submitted} reports submitted successfully", "count": submitted}
    finally:
        db.close()


@app.get("/api/worker/my-reports")
async def get_my_reports(current_user: dict = Depends(require_worker)):
    db = get_db()
    try:
        worker_id = int(current_user["sub"])
        reports = db.execute("""SELECT * FROM health_reports WHERE worker_id=?
                               ORDER BY created_at DESC""", (worker_id,)).fetchall()
        return [dict(r) for r in reports]
    finally:
        db.close()


@app.put("/api/worker/reports/{report_id}")
async def edit_report(
    report_id: int,
    patient_name: str = Form(None),
    symptoms: str = Form(None),
    severity: str = Form(None),
    notes: str = Form(None),
    current_user: dict = Depends(require_worker)
):
    db = get_db()
    try:
        worker_id = int(current_user["sub"])
        report = db.execute("SELECT * FROM health_reports WHERE id=? AND worker_id=?",
                            (report_id, worker_id)).fetchone()
        if not report:
            raise HTTPException(404, "Report not found")

        # Check 24-hour window
        created = datetime.strptime(report["created_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - created > timedelta(hours=24):
            raise HTTPException(403, "Reports can only be edited within 24 hours of submission")

        updates = []
        params = []
        if patient_name:
            updates.append("patient_name=?")
            params.append(patient_name)
        if symptoms:
            updates.append("symptoms=?")
            params.append(symptoms)
        if severity:
            updates.append("severity=?")
            params.append(severity)
        if notes is not None:
            updates.append("notes=?")
            params.append(notes)
        updates.append("updated_at=?")
        params.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        params.append(report_id)

        db.execute(f"UPDATE health_reports SET {', '.join(updates)} WHERE id=?", params)
        db.commit()
        return {"message": "Report updated successfully"}
    finally:
        db.close()


# ═══════════════════════════════════════════
# PUBLIC / USER ROUTES
# ═══════════════════════════════════════════
@app.post("/api/user/symptom-report")
async def submit_symptom_report(
    village: str = Form(...),
    district: str = Form(...),
    symptoms: str = Form(...),
    duration_days: int = Form(None),
    water_source: str = Form(""),
    is_anonymous: int = Form(0),
    current_user: dict = Depends(get_current_user)
):
    db = get_db()
    try:
        user_id = int(current_user["sub"]) if not is_anonymous else None
        db.execute("""INSERT INTO symptom_reports (user_id, village, district, symptoms,
                      duration_days, water_source, is_anonymous)
                      VALUES (?, ?, ?, ?, ?, ?, ?)""",
                   (user_id, village, district, symptoms, duration_days, water_source, is_anonymous))
        db.commit()

        diseases = detect_disease(symptoms)
        tips = get_health_tips("yellow" if diseases else "green")
        return {
            "message": "Symptom report submitted. Thank you for contributing to community health!",
            "possible_diseases": diseases,
            "health_tips": tips,
            "symptom_score": calculate_symptom_score(symptoms)
        }
    finally:
        db.close()


@app.get("/api/user/risk-status")
async def get_risk_status(
    village: str = Query(...),
    district: str = Query("")
):
    db = get_db()
    try:
        reports = db.execute("""SELECT * FROM health_reports
                               WHERE village=? AND created_at >= date('now', '-7 days')""",
                             (village,)).fetchall()

        # Try to get weather data
        weather = None
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"https://api.openweathermap.org/data/2.5/weather?q={village},IN&appid={WEATHER_API_KEY}&units=metric"
                )
                if resp.status_code == 200:
                    data = resp.json()
                    weather = {
                        "temp": data["main"]["temp"],
                        "humidity": data["main"]["humidity"],
                        "rainfall": data.get("rain", {}).get("1h", 0),
                        "description": data["weather"][0]["description"]
                    }
        except:
            pass

        risk = calculate_village_risk([dict(r) for r in reports], weather)
        tips = get_health_tips(risk["risk_level"])

        return {
            **risk,
            "village": village,
            "health_tips": tips,
            "weather": weather,
            "safe_water_guide": get_safe_water_guide()
        }
    finally:
        db.close()


@app.get("/api/user/my-reports")
async def get_user_reports(current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        reports = db.execute("""SELECT * FROM symptom_reports WHERE user_id=?
                               ORDER BY created_at DESC""", (user_id,)).fetchall()
        return [dict(r) for r in reports]
    finally:
        db.close()


# ═══════════════════════════════════════════
# COMMON / PUBLIC ROUTES
# ═══════════════════════════════════════════
@app.get("/api/alerts")
async def get_public_alerts():
    db = get_db()
    try:
        alerts = db.execute("""SELECT * FROM alerts
                              ORDER BY created_at DESC LIMIT 50""").fetchall()
        return [dict(a) for a in alerts]
    finally:
        db.close()


@app.get("/api/notices")
async def get_notices():
    db = get_db()
    try:
        notices = db.execute("""SELECT n.*, u.full_name as author
                               FROM notices n LEFT JOIN users u ON n.created_by=u.id
                               ORDER BY n.created_at DESC LIMIT 50""").fetchall()
        return [dict(n) for n in notices]
    finally:
        db.close()


@app.get("/api/notifications")
async def get_notifications(current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        if not current_user or not current_user.get("sub"):
            raise HTTPException(401, "Invalid or missing authentication")
        
        user_id = int(current_user["sub"])
        notifs = db.execute("""SELECT * FROM notifications WHERE user_id=?
                              ORDER BY created_at DESC LIMIT 50""", (user_id,)).fetchall()
        unread = db.execute("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0",
                            (user_id,)).fetchone()["c"]
        return {"notifications": [dict(n) for n in notifs], "unread_count": unread}
    except Exception as e:
        print(f"Notification error: {e}")
        raise HTTPException(500, f"Error loading notifications: {str(e)}")
    finally:
        db.close()


@app.post("/api/notifications/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        db.execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user_id,))
        db.commit()
        return {"message": "All notifications marked as read"}
    finally:
        db.close()


@app.get("/api/districts")
async def get_districts():
    db = get_db()
    try:
        districts = db.execute("SELECT DISTINCT district FROM users WHERE district != '' ORDER BY district").fetchall()
        return [d["district"] for d in districts]
    finally:
        db.close()


@app.get("/api/villages")
async def get_villages(district: str = Query(None)):
    db = get_db()
    try:
        if district:
            villages = db.execute("""SELECT DISTINCT village FROM users
                                    WHERE district=? AND village != '' ORDER BY village""",
                                  (district,)).fetchall()
        else:
            villages = db.execute("SELECT DISTINCT village FROM users WHERE village != '' ORDER BY village").fetchall()
        return [v["village"] for v in villages]
    finally:
        db.close()


@app.get("/api/predictions")
async def get_predictions():
    db = get_db()
    try:
        preds = db.execute("""SELECT * FROM predictions
                             ORDER BY prediction_date DESC, risk_score DESC""").fetchall()
        return [dict(p) for p in preds]
    finally:
        db.close()


@app.get("/api/weather/{city}")
async def get_weather(city: str):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"https://api.openweathermap.org/data/2.5/weather?q={city},IN&appid={WEATHER_API_KEY}&units=metric"
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": "Weather data not available"}
    except:
        return {"error": "Weather service unavailable"}


@app.post("/api/worker/training-chat")
async def worker_training_chat(
    message: str = Form(...),
    current_user: dict = Depends(require_worker)
):
    """Worker-only training chatbot reply via Groq API."""
    if not GROQ_API_KEY:
        raise HTTPException(503, "Groq API key is not configured on server")

    msg = (message or "").strip()
    if not msg:
        raise HTTPException(400, "Message is required")

    system_prompt = (
        "You are a Worker Training Assistant for a community health monitoring dashboard. "
        "Answer only about how to use this website (submit report, bulk entry, alerts, severity, data quality). "
        "If user asks unrelated topics, politely redirect to dashboard training help. "
        "Keep answers short, practical, and friendly."
    )

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": msg}
        ],
        "temperature": 0.3,
        "max_tokens": 220
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(502, f"Groq API error ({resp.status_code})")

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise HTTPException(502, "Groq returned no response choices")

        content = (choices[0].get("message", {}) or {}).get("content", "").strip()
        if not content:
            raise HTTPException(502, "Groq returned empty response")

        return {"reply": content}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, "Unable to reach Groq service")


# ═══ DATA MANAGEMENT ENDPOINTS ═══

@app.get("/api/admin/data-stats")
async def get_data_stats(current_user: dict = Depends(require_admin)):
    """Get statistics on users and reports."""
    db = get_db()
    try:
        # Count users by role
        users = db.execute("""
            SELECT id, full_name, username, role, village FROM users ORDER BY role, created_at DESC
        """).fetchall()
        
        all_users = [dict(u) for u in users]
        total_users = len(users)
        admin_count = sum(1 for u in users if u['role'] == 'admin')
        worker_count = sum(1 for u in users if u['role'] == 'worker')
        user_count = sum(1 for u in users if u['role'] == 'user')
        
        # Count reports
        health_reports = db.execute("SELECT COUNT(*) as c FROM health_reports").fetchone()['c']
        symptom_reports = db.execute("SELECT COUNT(*) as c FROM symptom_reports").fetchone()['c']
        total_reports = health_reports + symptom_reports
        
        # Get recent reports (health + symptom combined)
        health = db.execute("""
            SELECT id, patient_name, village, 'health' as type, created_at FROM health_reports 
            ORDER BY created_at DESC LIMIT 20
        """).fetchall()
        symptom = db.execute("""
            SELECT id, NULL as patient_name, village, 'symptom' as type, created_at FROM symptom_reports 
            ORDER BY created_at DESC LIMIT 20
        """).fetchall()
        recent_reports = sorted(
            [dict(h) for h in health] + [dict(s) for s in symptom],
            key=lambda x: x['created_at'],
            reverse=True
        )[:20]
        
        return {
            "total_users": total_users,
            "admin_count": admin_count,
            "worker_count": worker_count,
            "user_count": user_count,
            "total_reports": total_reports,
            "health_reports": health_reports,
            "symptom_reports": symptom_reports,
            "all_users": all_users,
            "recent_reports": recent_reports
        }
    finally:
        db.close()


@app.delete("/api/admin/data/users/{user_id}")
async def delete_user(user_id: int, current_user: dict = Depends(require_admin)):
    """Delete a specific user (not admin)."""
    db = get_db()
    try:
        # Prevent deleting admin
        user = db.execute("SELECT role FROM users WHERE id=?", (user_id,)).fetchone()
        if not user or user['role'] == 'admin':
            raise HTTPException(400, "Cannot delete admin user")
        
        # Delete user and related data
        db.execute("DELETE FROM notifications WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM health_reports WHERE worker_id=?", (user_id,))
        db.execute("DELETE FROM symptom_reports WHERE user_id=?", (user_id,))
        db.execute("DELETE FROM users WHERE id=?", (user_id,))
        db.commit()
        
        return {"message": "User deleted successfully"}
    finally:
        db.close()


@app.delete("/api/admin/data/reports/{report_id}")
async def delete_report(report_id: int, current_user: dict = Depends(require_admin)):
    """Delete a specific report."""
    db = get_db()
    try:
        # Try both tables
        health_delete = db.execute("DELETE FROM health_reports WHERE id=?", (report_id,)).rowcount
        symptom_delete = db.execute("DELETE FROM symptom_reports WHERE id=?", (report_id,)).rowcount
        db.commit()
        
        if health_delete == 0 and symptom_delete == 0:
            raise HTTPException(404, "Report not found")
        
        return {"message": "Report deleted successfully"}
    finally:
        db.close()


@app.post("/api/admin/data/delete-all-users")
async def delete_all_non_admin_users(current_user: dict = Depends(require_admin)):
    """Delete all users except admin."""
    db = get_db()
    try:
        # Delete non-admin users and related data
        non_admin_ids = db.execute(
            "SELECT id FROM users WHERE role IN ('worker', 'user')"
        ).fetchall()
        
        for row in non_admin_ids:
            uid = row['id']
            db.execute("DELETE FROM notifications WHERE user_id=?", (uid,))
            db.execute("DELETE FROM health_reports WHERE worker_id=?", (uid,))
            db.execute("DELETE FROM symptom_reports WHERE user_id=?", (uid,))
        
        db.execute("DELETE FROM users WHERE role IN ('worker', 'user')")
        db.commit()
        
        return {"message": "All non-admin users deleted successfully"}
    finally:
        db.close()


@app.post("/api/admin/data/delete-all-reports")
async def delete_all_reports(current_user: dict = Depends(require_admin)):
    """Delete all reports from the system."""
    db = get_db()
    try:
        db.execute("DELETE FROM health_reports")
        db.execute("DELETE FROM symptom_reports")
        db.execute("DELETE FROM predictions")  # Also clear predictions
        db.commit()
        
        return {"message": "All reports deleted successfully"}
    finally:
        db.close()


@app.post("/api/admin/data/reset")
async def reset_all_data(current_user: dict = Depends(require_admin)):
    """Full system reset: delete all data except admin user."""
    db = get_db()
    try:
        # Delete all non-admin users and related data
        non_admin_ids = db.execute(
            "SELECT id FROM users WHERE role IN ('worker', 'user')"
        ).fetchall()
        
        for row in non_admin_ids:
            uid = row['id']
            db.execute("DELETE FROM notifications WHERE user_id=?", (uid,))
            db.execute("DELETE FROM health_reports WHERE worker_id=?", (uid,))
            db.execute("DELETE FROM symptom_reports WHERE user_id=?", (uid,))
        
        # Delete all reports and related data
        db.execute("DELETE FROM users WHERE role IN ('worker', 'user')")
        db.execute("DELETE FROM health_reports")
        db.execute("DELETE FROM symptom_reports")
        db.execute("DELETE FROM alerts")
        db.execute("DELETE FROM notices")
        db.execute("DELETE FROM predictions")
        db.execute("DELETE FROM water_sources")
        db.execute("DELETE FROM notifications")
        
        db.commit()
        
        return {"message": "Full system reset completed successfully"}
    finally:
        db.close()


# ═══════════════════════════════════════════
# DEVELOPER PORTAL ROUTES
# ═══════════════════════════════════════════

# Developer Login Endpoint
@app.post("/api/auth/dev-login")
async def dev_login(
    email: str = Form(...),
    password: str = Form(...),
    secret_key: str = Form(...)
):
    """Developer login with email, password, and secret key."""
    db = get_db()
    try:
        from backend.auth import track_failed_secret_attempt
        
        # Verify secret key first
        DEVELOPER_SECRET_KEY = "2026"
        if secret_key != DEVELOPER_SECRET_KEY:
            # Find the user attempting to login (could be admin trying to access)
            user_row = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
            if user_row:
                user = dict(user_row)
                # Track failed attempt only for non-developers (mainly admins)
                if user["role"] != "developer":
                    should_block = track_failed_secret_attempt(user["id"], email, user["role"])
                    if should_block:
                        app_logger.warning(f"User {email} ({user['role']}) blocked after 3 failed secret code attempts")
                        raise HTTPException(status_code=403, detail="Account has been blocked due to 3 failed secret code attempts. Contact a developer to unblock.")
                    app_logger.warning(f"Failed secret code attempt for {email} ({user['role']}) - {3 - user.get('attempt_count', 2)} attempts remaining")
            raise HTTPException(status_code=401, detail="Invalid developer secret key")
        
        # Find developer account
        dev_row = db.execute("SELECT * FROM users WHERE email=? AND role='developer'", (email,)).fetchone()
        if not dev_row or not verify_password(password, dev_row["password_hash"]):
            app_logger.warning(f"Developer login failed for {email}: Invalid credentials")
            raise HTTPException(status_code=401, detail="Invalid developer credentials")
        
        # Convert Row to dict for safe access
        dev = dict(dev_row)
        
        if not dev["is_active"]:
            app_logger.warning(f"Developer login failed for {email}: Account deactivated")
            raise HTTPException(status_code=403, detail="Developer account has been deactivated")
        
        if dev.get("is_blocked"):
            app_logger.warning(f"Developer login failed for {email}: Account blocked")
            raise HTTPException(status_code=403, detail=f"Developer account has been blocked. Reason: {dev.get('blocked_reason', 'Contact administrator')}")
        
        # Create token
        token = create_access_token({
            "sub": str(dev["id"]),
            "username": dev["username"],
            "role": dev["role"],
            "full_name": dev["full_name"],
            "email": dev["email"]
        })
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": dev["id"],
                "username": dev["username"],
                "full_name": dev["full_name"],
                "email": dev["email"],
                "role": "developer"
            }
        }
    finally:
        db.close()


# Developer Dashboard
@app.get("/api/dev/dashboard")
async def dev_dashboard(current_user: dict = Depends(require_developer)):
    """Get developer dashboard statistics."""
    db = get_db()
    try:
        total_errors = db.execute("SELECT COUNT(*) c FROM error_logs").fetchone()["c"]
        unresolved_errors = db.execute("SELECT COUNT(*) c FROM error_logs WHERE is_resolved=0").fetchone()["c"]
        total_feedback = db.execute("SELECT COUNT(*) c FROM feedback").fetchone()["c"]
        unresponded_feedback = db.execute("SELECT COUNT(*) c FROM feedback WHERE dev_response IS NULL").fetchone()["c"]
        total_users = db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        total_admins = db.execute("SELECT COUNT(*) c FROM users WHERE role='admin'").fetchone()["c"]
        total_developers = db.execute("SELECT COUNT(*) c FROM users WHERE role='developer'").fetchone()["c"]
        active_sessions = db.execute("SELECT COUNT(*) c FROM user_sessions WHERE logout_time IS NULL").fetchone()["c"]
        
        # Error severity breakdown
        severity_stats = db.execute("""
            SELECT severity, COUNT(*) as count FROM error_logs GROUP BY severity
        """).fetchall()
        
        # Feedback types breakdown
        feedback_types = db.execute("""
            SELECT feedback_type, COUNT(*) as count FROM feedback GROUP BY feedback_type
        """).fetchall()
        
        return {
            "total_errors": total_errors,
            "unresolved_errors": unresolved_errors,
            "total_feedback": total_feedback,
            "unresponded_feedback": unresponded_feedback,
            "total_users": total_users,
            "total_admins": total_admins,
            "total_developers": total_developers,
            "active_sessions": active_sessions,
            "severity_stats": {s["severity"]: s["count"] for s in severity_stats},
            "feedback_types": {f["feedback_type"]: f["count"] for f in feedback_types}
        }
    finally:
        db.close()


# Error Logs
@app.get("/api/dev/error-logs")
async def get_error_logs(
    severity: str = Query(None),
    endpoint: str = Query(None),
    is_resolved: int = Query(None),
    limit: int = Query(50),
    current_user: dict = Depends(require_developer)
):
    """Get error logs with optional filtering."""
    db = get_db()
    try:
        query = "SELECT * FROM error_logs WHERE 1=1"
        params = []
        
        if severity:
            query += " AND severity=?"
            params.append(severity)
        if endpoint:
            query += " AND endpoint=?"
            params.append(endpoint)
        if is_resolved is not None:
            query += " AND is_resolved=?"
            params.append(is_resolved)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        errors = db.execute(query, params).fetchall()
        return [dict(e) for e in errors]
    finally:
        db.close()


@app.put("/api/dev/error-logs/{error_id}")
async def mark_error_resolved(
    error_id: int,
    current_user: dict = Depends(require_developer)
):
    """Mark an error as resolved."""
    db = get_db()
    try:
        db.execute(
            "UPDATE error_logs SET is_resolved=1 WHERE id=?",
            (error_id,)
        )
        db.commit()
        return {"message": "Error marked as resolved"}
    finally:
        db.close()


# User Activity / Sessions
@app.get("/api/dev/user-activity")
async def get_user_activity(
    limit: int = Query(100),
    current_user: dict = Depends(require_developer)
):
    """Get user session activity."""
    db = get_db()
    try:
        # Get sessions with user info
        sessions = db.execute("""
            SELECT us.*, u.username, u.full_name, u.role
            FROM user_sessions us
            LEFT JOIN users u ON us.user_id = u.id
            ORDER BY us.login_time DESC
            LIMIT ?
        """, (limit,)).fetchall()
        
        # Get currently active sessions
        active_sessions = db.execute("""
            SELECT us.*, u.username, u.full_name, u.role
            FROM user_sessions us
            LEFT JOIN users u ON us.user_id = u.id
            WHERE us.logout_time IS NULL
            ORDER BY us.login_time DESC
        """).fetchall()
        
        return {
            "all_sessions": [dict(s) for s in sessions],
            "active_sessions": [dict(s) for s in active_sessions],
            "active_count": len(active_sessions)
        }
    finally:
        db.close()


# Delete User Sessions by Age
@app.post("/api/dev/delete-sessions")
async def delete_sessions(
    age_hours: int = Query(...),
    current_user: dict = Depends(require_developer)
):
    """Delete user sessions older than specified hours. Options: 24, 168 (7d), 720 (30d), or 0 (all)."""
    db = get_db()
    try:
        if age_hours == 0:
            # Delete all sessions
            result = db.execute("DELETE FROM user_sessions").rowcount
            deleted_count = result
            app_logger.warning(f"Developer {current_user.get('username')} deleted ALL user sessions ({deleted_count} sessions)")
                
        else:
            # Delete sessions older than X hours
            cutoff_time = (datetime.now() - timedelta(hours=age_hours)).strftime("%Y-%m-%d %H:%M:%S")
            result = db.execute(
                "DELETE FROM user_sessions WHERE login_time < ?",
                (cutoff_time,)
            )
            deleted_count = result.rowcount
            hours_label = f"{age_hours} hours" if age_hours < 24 else f"{age_hours//24} days"
            app_logger.warning(f"Developer {current_user.get('username')} deleted user sessions older than {hours_label} ({deleted_count} sessions)")
        
        db.commit()
        
        return {
            "message": f"Successfully deleted {deleted_count} user sessions",
            "deleted_count": deleted_count,
            "age_hours": age_hours
        }
    except Exception as e:
        app_logger.error(f"Error deleting sessions: {str(e)}")
        raise HTTPException(500, f"Error deleting sessions: {str(e)}")
    finally:
        db.close()


# Delete Single Session
@app.delete("/api/dev/session/{session_id}")
async def delete_single_session(
    session_id: int,
    current_user: dict = Depends(require_developer)
):
    """Delete a specific user session."""
    db = get_db()
    try:
        session = db.execute(
            "SELECT user_id, login_time FROM user_sessions WHERE id=?",
            (session_id,)
        ).fetchone()
        
        if not session:
            raise HTTPException(404, "Session not found")
        
        db.execute("DELETE FROM user_sessions WHERE id=?", (session_id,))
        db.commit()
        
        app_logger.info(f"Developer {current_user.get('username')} deleted session {session_id} (user_id: {session['user_id']})")
        
        return {"message": "Session deleted successfully"}
    except Exception as e:
        app_logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(500, str(e))
    finally:
        db.close()


# Feedback Management
@app.get("/api/dev/feedback")
async def get_feedback(
    feedback_type: str = Query(None),
    is_resolved: int = Query(None),
    limit: int = Query(100),
    current_user: dict = Depends(require_developer)
):
    """Get user feedback."""
    db = get_db()
    try:
        query = "SELECT f.*, u.full_name as from_user_name FROM feedback f LEFT JOIN users u ON f.from_user_id = u.id WHERE 1=1"
        params = []
        
        if feedback_type:
            query += " AND f.feedback_type=?"
            params.append(feedback_type)
        if is_resolved is not None:
            query += " AND f.is_resolved=?"
            params.append(is_resolved)
        
        query += " ORDER BY f.created_at DESC LIMIT ?"
        params.append(limit)
        
        feedback = db.execute(query, params).fetchall()
        return [dict(f) for f in feedback]
    finally:
        db.close()


@app.put("/api/dev/feedback/{feedback_id}")
async def respond_to_feedback(
    feedback_id: int,
    response: str = Form(...),
    current_user: dict = Depends(require_developer)
):
    """Add developer response to feedback."""
    db = get_db()
    try:
        db.execute(
            "UPDATE feedback SET dev_response=?, is_resolved=1 WHERE id=?",
            (response, feedback_id)
        )
        db.commit()
        return {"message": "Response added to feedback"}
    finally:
        db.close()


@app.post("/api/feedback/submit")
async def submit_feedback(
    feedback_text: str = Form(...),
    feedback_type: str = Form("general"),
    page_or_feature: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback from user."""
    db = get_db()
    try:
        db.execute(
            """INSERT INTO feedback (from_user_id, from_role, feedback_text, feedback_type, page_or_feature, created_at)
               VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (current_user["user_id"], current_user["role"], feedback_text, feedback_type, page_or_feature)
        )
        db.commit()
        app_logger.info(f"Feedback submitted by {current_user['username']} - Type: {feedback_type}")
        return {"message": "Feedback submitted successfully", "status": "success"}
    except Exception as e:
        app_logger.error(f"Error submitting feedback: {str(e)}")
        return {"message": "Error submitting feedback", "status": "error"}
    finally:
        db.close()


@app.get("/api/admin/feedback")
async def get_admin_all_feedback(current_user: dict = Depends(require_admin)):
    """Get all feedback for admin dashboard."""
    db = get_db()
    try:
        feedback = db.execute(
            """SELECT f.id, u.username, f.feedback_text, f.rating, f.feedback_type, f.page_or_feature, f.created_at
               FROM feedback f
               LEFT JOIN users u ON f.from_user_id = u.id
               ORDER BY f.created_at DESC
               LIMIT 100"""
        ).fetchall()
        
        result = [dict(f) for f in feedback]
        return {"feedback": result, "total": len(result)}
    except Exception as e:
        app_logger.error(f"Error fetching all feedback: {str(e)}")
        return {"feedback": [], "total": 0}
    finally:
        db.close()


@app.get("/api/worker/feedback")
async def get_worker_feedback(current_user: dict = Depends(get_current_user)):
    """Get feedback submitted by current worker."""
    if current_user["role"] not in ["worker", "admin"]:
        raise HTTPException(status_code=403, detail="Only workers and admins can access this")
    
    db = get_db()
    try:
        feedback = db.execute(
            """SELECT id, feedback_text, rating, feedback_type, page_or_feature, created_at
               FROM feedback
               WHERE from_user_id = ?
               ORDER BY created_at DESC""",
            (current_user["user_id"],)
        ).fetchall()
        
        result = [dict(f) for f in feedback]
        return {"feedback": result, "total": len(result)}
    except Exception as e:
        app_logger.error(f"Error fetching worker feedback: {str(e)}")
        return {"feedback": [], "total": 0}
    finally:
        db.close()


@app.get("/api/user/feedback")
async def get_user_feedback(current_user: dict = Depends(get_current_user)):
    """Get feedback submitted by current user."""
    if current_user["role"] not in ["user", "admin"]:
        raise HTTPException(status_code=403, detail="Only users and admins can access this")
    
    db = get_db()
    try:
        feedback = db.execute(
            """SELECT id, feedback_text, rating, feedback_type, page_or_feature, created_at
               FROM feedback
               WHERE from_user_id = ?
               ORDER BY created_at DESC""",
            (current_user["user_id"],)
        ).fetchall()
        
        result = [dict(f) for f in feedback]
        return {"feedback": result, "total": len(result)}
    except Exception as e:
        app_logger.error(f"Error fetching user feedback: {str(e)}")
        return {"feedback": [], "total": 0}
    finally:
        db.close()


# Notices
@app.get("/api/dev/notices")
async def get_dev_notices(
    notice_type: str = Query(None),
    limit: int = Query(50),
    current_user: dict = Depends(require_developer)
):
    """Get developer notices/broadcasts."""
    db = get_db()
    try:
        query = "SELECT dn.*, u.full_name as creator_name FROM dev_notices dn LEFT JOIN users u ON dn.created_by = u.id WHERE 1=1"
        params = []
        
        if notice_type:
            query += " AND dn.notice_type=?"
            params.append(notice_type)
        
        query += " ORDER BY dn.created_at DESC LIMIT ?"
        params.append(limit)
        
        notices = db.execute(query, params).fetchall()
        return [dict(n) for n in notices]
    finally:
        db.close()


@app.post("/api/dev/send-notice")
async def send_dev_notice(
    title: str = Form(...),
    message: str = Form(...),
    notice_type: str = Form("info"),
    target_roles: str = Form("user,worker,admin"),
    current_user: dict = Depends(require_developer)
):
    """Send a notice to specific user roles."""
    db = get_db()
    try:
        dev_id = int(current_user["sub"])
        roles = [r.strip() for r in target_roles.split(",")]
        
        # Create the notice
        db.execute("""
            INSERT INTO dev_notices (title, message, notice_type, target_roles, created_by)
            VALUES (?, ?, ?, ?, ?)
        """, (title, message, notice_type, target_roles, dev_id))
        db.commit()
        
        # Send notifications to affected users
        query = "SELECT id FROM users WHERE role IN ({})".format(
            ",".join(["?" for _ in roles])
        )
        users = db.execute(query, roles).fetchall()
        
        for u in users:
            db.execute("""
                INSERT INTO notifications (user_id, title, message, notification_type)
                VALUES (?, ?, ?, ?)
            """, (u["id"], title, message, notice_type))
        
        db.commit()
        return {"message": f"Notice sent to {len(users)} users", "recipients": len(users)}
    finally:
        db.close()


@app.delete("/api/dev/notices/{notice_id}")
async def delete_dev_notice(
    notice_id: int,
    current_user: dict = Depends(require_developer)
):
    """Delete a developer notice."""
    db = get_db()
    try:
        # Verify the notice exists and was created by this developer
        notice = db.execute(
            "SELECT created_by FROM dev_notices WHERE id=?",
            (notice_id,)
        ).fetchone()
        
        if not notice:
            raise HTTPException(404, "Notice not found")
        
        if notice["created_by"] != int(current_user["sub"]):
            raise HTTPException(403, "You can only delete your own notices")
        
        # Delete the notice
        db.execute("DELETE FROM dev_notices WHERE id=?", (notice_id,))
        db.commit()
        
        return {"message": "Notice deleted successfully"}
    finally:
        db.close()


# Admin Management
@app.get("/api/dev/admins")
async def get_admins(
    current_user: dict = Depends(require_developer)
):
    """Get list of all admins."""
    db = get_db()
    try:
        admins = db.execute("""
            SELECT id, username, email, full_name, is_active, created_at, last_login
            FROM users WHERE role='admin'
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(a) for a in admins]
    finally:
        db.close()


@app.post("/api/dev/create-admin")
async def create_admin(
    data: dict = Body(...),
    current_user: dict = Depends(require_developer)
):
    """Create a new admin account."""
    db = get_db()
    try:
        app_logger.info(f"[CreateAdmin] Received request from developer {current_user.get('email')}")
        
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        full_name = data.get('full_name')
        secret_key = data.get('secret_key')
        
        app_logger.debug(f"[CreateAdmin] Data: username={username}, email={email}, full_name={full_name}")
        
        # Validate all fields are provided
        if not all([username, email, password, full_name, secret_key]):
            msg = "All fields are required"
            app_logger.warning(f"[CreateAdmin] Validation failed: {msg}")
            raise HTTPException(400, msg)
        
        # Verify developer secret key
        if secret_key != "2026":
            msg = "Invalid secret key"
            app_logger.warning(f"[CreateAdmin] Secret key validation failed")
            raise HTTPException(401, msg)
        
        # Check if user already exists
        existing = db.execute(
            "SELECT id FROM users WHERE username=? OR email=?",
            (username, email)
        ).fetchone()
        
        if existing:
            msg = "Username or email already exists"
            app_logger.warning(f"[CreateAdmin] User already exists: {msg}")
            raise HTTPException(400, msg)
        
        # Create admin
        hashed = hash_password(password)
        db.execute("""
            INSERT INTO users (username, email, password_hash, full_name, role, is_approved, is_active)
            VALUES (?, ?, ?, ?, 'admin', 1, 1)
        """, (username, email, hashed, full_name))
        
        db.commit()
        msg = f"Admin '{full_name}' created successfully"
        app_logger.info(f"[CreateAdmin] {msg}")
        return {"message": msg}
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"[CreateAdmin] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Server error: {str(e)}")
    finally:
        db.close()


@app.post("/api/dev/deactivate-admin/{admin_id}")
async def deactivate_admin(
    admin_id: int,
    current_user: dict = Depends(require_developer)
):
    """Deactivate an admin account."""
    db = get_db()
    try:
        admin = db.execute(
            "SELECT role FROM users WHERE id=?",
            (admin_id,)
        ).fetchone()
        
        if not admin or admin["role"] != "admin":
            raise HTTPException(404, "Admin not found")
        
        db.execute(
            "UPDATE users SET is_active=0 WHERE id=?",
            (admin_id,)
        )
        db.commit()
        
        return {"message": "Admin deactivated successfully"}
    finally:
        db.close()


@app.post("/api/dev/activate-admin/{admin_id}")
async def activate_admin(
    admin_id: int,
    current_user: dict = Depends(require_developer)
):
    """Activate an admin account."""
    db = get_db()
    try:
        admin = db.execute(
            "SELECT role FROM users WHERE id=?",
            (admin_id,)
        ).fetchone()
        
        if not admin or admin["role"] != "admin":
            raise HTTPException(404, "Admin not found")
        
        db.execute(
            "UPDATE users SET is_active=1 WHERE id=?",
            (admin_id,)
        )
        db.commit()
        
        return {"message": "Admin activated successfully"}
    finally:
        db.close()


# Developer Management
@app.get("/api/dev/developers")
async def get_developers(
    current_user: dict = Depends(require_developer)
):
    """Get list of all developers."""
    db = get_db()
    try:
        developers = db.execute("""
            SELECT id, username, email, full_name, is_active, created_at
            FROM users WHERE role='developer'
            ORDER BY created_at DESC
        """).fetchall()
        return [dict(d) for d in developers]
    finally:
        db.close()


@app.post("/api/dev/create-developer")
async def create_developer(
    data: dict = Body(...),
    current_user: dict = Depends(require_developer)
):
    """Create a new developer account."""
    db = get_db()
    try:
        app_logger.info(f"[CreateDeveloper] Received request from developer {current_user.get('email')}")
        
        full_name = data.get('full_name')
        email = data.get('email')
        password = data.get('password')
        secret_key = data.get('secret_key', '2026')
        
        # Generate username from email
        username = email.split('@')[0] if email else None
        
        app_logger.debug(f"[CreateDeveloper] Data: username={username}, email={email}, full_name={full_name}")
        
        # Validate required fields
        if not all([full_name, email, password, username]):
            msg = "All fields are required"
            app_logger.warning(f"[CreateDeveloper] Validation failed: {msg}")
            raise HTTPException(400, msg)
        
        # Verify secret key
        if secret_key != "2026":
            msg = "Invalid secret key"
            app_logger.warning(f"[CreateDeveloper] Secret key validation failed")
            raise HTTPException(401, msg)
        
        # Check if user already exists
        existing = db.execute(
            "SELECT id FROM users WHERE username=? OR email=?",
            (username, email)
        ).fetchone()
        
        if existing:
            msg = "Username or email already exists"
            app_logger.warning(f"[CreateDeveloper] User already exists: {msg}")
            raise HTTPException(400, msg)
        
        # Create developer
        hashed = hash_password(password)
        db.execute("""
            INSERT INTO users (username, email, password_hash, full_name, role, is_approved, is_active)
            VALUES (?, ?, ?, ?, 'developer', 1, 1)
        """, (username, email, hashed, full_name))
        
        db.commit()
        msg = f"Developer '{full_name}' created successfully"
        app_logger.info(f"[CreateDeveloper] {msg}")
        return {"message": msg}
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"[CreateDeveloper] Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Server error: {str(e)}")
    finally:
        db.close()


@app.post("/api/dev/deactivate-developer/{dev_id}")
async def deactivate_developer(
    dev_id: int,
    current_user: dict = Depends(require_developer)
):
    """Deactivate a developer account."""
    db = get_db()
    try:
        dev = db.execute(
            "SELECT role FROM users WHERE id=?",
            (dev_id,)
        ).fetchone()
        
        if not dev or dev["role"] != "developer":
            raise HTTPException(404, "Developer not found")
        
        db.execute(
            "UPDATE users SET is_active=0 WHERE id=?",
            (dev_id,)
        )
        db.commit()
        
        return {"message": "Developer deactivated successfully"}
    finally:
        db.close()


@app.post("/api/dev/activate-developer/{dev_id}")
async def activate_developer(
    dev_id: int,
    current_user: dict = Depends(require_developer)
):
    """Activate a developer account."""
    db = get_db()
    try:
        dev = db.execute(
            "SELECT role FROM users WHERE id=?",
            (dev_id,)
        ).fetchone()
        
        if not dev or dev["role"] != "developer":
            raise HTTPException(404, "Developer not found")
        
        db.execute(
            "UPDATE users SET is_active=1 WHERE id=?",
            (dev_id,)
        )
        db.commit()
        
        return {"message": "Developer activated successfully"}
    finally:
        db.close()


# Application Logs Endpoint
@app.get("/api/dev/logs")
async def get_application_logs(
    lines: int = Query(100, ge=10, le=1000),
    current_user: dict = Depends(require_developer)
):
    """Get recent application log entries. Developer access only."""
    try:
        log_file = os.path.join(LOG_DIR, 'app.log')
        if not os.path.exists(log_file):
            return {"logs": [], "message": "No logs found yet"}
        
        # Read the last N lines from the log file
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
        
        # Get the last 'lines' entries
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Parse each log line into a structured format
        parsed_logs = []
        for line in recent_lines:
            line = line.strip()
            if line:
                parsed_logs.append({
                    "raw": line,
                    "timestamp": line.split(' - ')[0] if ' - ' in line else 'N/A'
                })
        
        app_logger.info(f"Developer {current_user.get('username')} accessed application logs")
        
        return {
            "logs": parsed_logs,
            "total_lines": len(all_lines),
            "returned_lines": len(parsed_logs),
            "log_file": log_file
        }
    except Exception as e:
        app_logger.error(f"Error reading logs: {str(e)}")
        return {"logs": [], "error": str(e)}


# Delete Logs Endpoint
@app.post("/api/dev/delete-logs")
async def delete_logs(
    secret_code: str = Form(...),
    log_type: str = Form("all"),
    current_user: dict = Depends(require_developer)
):
    """Delete application logs using secret code."""
    db = get_db()
    try:
        # Verify secret code (same as developer login)
        DEVELOPER_SECRET_KEY = "2026"
        if secret_code != DEVELOPER_SECRET_KEY:
            raise HTTPException(status_code=401, detail="Invalid secret code")
        
        deleted_count = 0
        
        if log_type == "all" or log_type == "error":
            # Clear error logs from database
            deleted = db.execute("DELETE FROM error_logs").rowcount
            deleted_count += deleted
            app_logger.info(f"Developer {current_user.get('username')} deleted {deleted} error logs")
        
        if log_type == "all" or log_type == "app":
            # Clear app log file
            log_file = os.path.join(LOG_DIR, 'app.log')
            if os.path.exists(log_file):
                open(log_file, 'w').close()  # Truncate file
                app_logger.info(f"Developer {current_user.get('username')} cleared app.log file")
        
        if log_type == "all" or log_type == "system":
            # Clear backup logs
            import glob
            backup_files = glob.glob(os.path.join(LOG_DIR, 'app.log.*'))
            for f in backup_files:
                try:
                    os.remove(f)
                    deleted_count += 1
                except Exception as e:
                    app_logger.error(f"Error deleting backup log {f}: {str(e)}")
        
        # Record log deletion in database
        db.execute("""
            INSERT INTO log_deletions (deleted_by, log_type, log_count, deletion_reason)
            VALUES (?, ?, ?, ?)
        """, (int(current_user["sub"]), log_type, deleted_count, "Manual deletion by developer"))
        db.commit()
        
        return {
            "message": f"Logs deleted successfully",
            "log_type": log_type,
            "deleted_count": deleted_count
        }
    except Exception as e:
        app_logger.error(f"Error deleting logs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting logs: {str(e)}")
    finally:
        db.close()


# Get Blocked Users
@app.get("/api/dev/blocked-users")
async def get_blocked_users(
    current_user: dict = Depends(require_developer)
):
    """Get list of blocked users and admins."""
    db = get_db()
    try:
        blocked = db.execute("""
            SELECT id, username, email, full_name, role, blocked_reason, blocked_at, blocked_by
            FROM users WHERE is_blocked=1
            ORDER BY blocked_at DESC
        """).fetchall()
        
        return [dict(b) for b in blocked]
    finally:
        db.close()


# Unblock User/Admin
@app.post("/api/dev/unblock-user/{user_id}")
async def unblock_user(
    user_id: int,
    secret_code: str = Form(...),
    current_user: dict = Depends(require_developer)
):
    """Unblock a blocked user or admin. Requires secret code."""
    db = get_db()
    try:
        # Verify secret code
        DEVELOPER_SECRET_KEY = "2026"
        if secret_code != DEVELOPER_SECRET_KEY:
            raise HTTPException(status_code=401, detail="Invalid secret code")
        
        user = db.execute(
            "SELECT id, username, role FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user["is_blocked"]:
            raise HTTPException(status_code=400, detail="User is not blocked")
        
        # Unblock user
        db.execute("""
            UPDATE users SET is_blocked=0, blocked_reason=NULL, blocked_at=NULL, blocked_by=NULL
            WHERE id=?
        """, (user_id,))
        
        # Clear failed attempts
        db.execute("DELETE FROM secret_code_attempts WHERE user_id=?", (user_id,))
        
        db.commit()
        
        app_logger.info(f"Developer {current_user.get('username')} unblocked {user['role']} {user['username']}")
        
        return {
            "message": f"User {user['username']} ({user['role']}) unblocked successfully",
            "unblocked_user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"]
            }
        }
    finally:
        db.close()


# System Health Check
@app.get("/api/dev/health-check")
async def system_health_check(
    current_user: dict = Depends(require_developer)
):
    """Check health status of all system functions."""
    db = get_db()
    health_status = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "components": {}
    }
    
    try:
        # ✅ Database Connection
        try:
            count = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
            health_status["components"]["database"] = {
                "status": "operational",
                "message": f"Connected, {count} users in database",
                "icon": "✅"
            }
        except Exception as e:
            health_status["components"]["database"] = {
                "status": "error",
                "message": f"Connection failed: {str(e)}",
                "icon": "❌"
            }
            health_status["overall_status"] = "unhealthy"
        
        # ✅ User Authentication
        try:
            token_test = create_access_token({"sub": "1", "role": "test"})
            if token_test:
                health_status["components"]["authentication"] = {
                    "status": "operational",
                    "message": "JWT token generation working",
                    "icon": "✅"
                }
        except Exception as e:
            health_status["components"]["authentication"] = {
                "status": "error",
                "message": f"Token generation failed: {str(e)}",
                "icon": "❌"
            }
        
        # ✅ File System Access
        try:
            if os.path.exists(LOG_DIR):
                log_files = len([f for f in os.listdir(LOG_DIR) if f.endswith('.log')])
                health_status["components"]["file_system"] = {
                    "status": "operational",
                    "message": f"File system accessible, {log_files} log files found",
                    "icon": "✅"
                }
            else:
                health_status["components"]["file_system"] = {
                    "status": "warning",
                    "message": "Log directory not found",
                    "icon": "⚠️"
                }
        except Exception as e:
            health_status["components"]["file_system"] = {
                "status": "error",
                "message": f"File access error: {str(e)}",
                "icon": "❌"
            }
        
        # ✅ API Endpoints - Test Critical Tables
        try:
            tables_to_check = [
                "users", "health_reports", "symptom_reports", "alerts",
                "error_logs", "feedback", "water_sources"
            ]
            accessible_tables = []
            
            for table in tables_to_check:
                try:
                    db.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
                    accessible_tables.append(table)
                except:
                    pass
            
            health_status["components"]["api_endpoints"] = {
                "status": "operational",
                "message": f"{len(accessible_tables)}/{len(tables_to_check)} database tables accessible",
                "accessible_tables": accessible_tables,
                "icon": "✅" if len(accessible_tables) >= 5 else "⚠️"
            }
        except Exception as e:
            health_status["components"]["api_endpoints"] = {
                "status": "error",
                "message": f"API test failed: {str(e)}",
                "icon": "❌"
            }
        
        # ✅ AI Engine Status
        try:
            from backend.ai_engine import calculate_village_risk
            # Just check if function is importable
            health_status["components"]["ai_engine"] = {
                "status": "operational",
                "message": "AI engine loaded successfully",
                "icon": "✅"
            }
        except Exception as e:
            health_status["components"]["ai_engine"] = {
                "status": "warning",
                "message": f"AI engine warning: {str(e)}",
                "icon": "⚠️"
            }
        
        # ✅ Data Integrity
        try:
            # Check for unresolved errors
            unresolved_errors = db.execute("SELECT COUNT(*) as c FROM error_logs WHERE is_resolved=0").fetchone()["c"]
            # Check for blocked users
            blocked_users = db.execute("SELECT COUNT(*) as c FROM users WHERE is_blocked=1").fetchone()["c"]
            
            status_msg = f"Unresolved errors: {unresolved_errors}, Blocked users: {blocked_users}"
            status_type = "warning" if unresolved_errors > 5 or blocked_users > 0 else "operational"
            icon = "⚠️" if status_type == "warning" else "✅"
            
            health_status["components"]["data_integrity"] = {
                "status": status_type,
                "message": status_msg,
                "unresolved_errors": unresolved_errors,
                "blocked_users": blocked_users,
                "icon": icon
            }
            
            if status_type == "warning":
                health_status["overall_status"] = "degraded"
        except Exception as e:
            health_status["components"]["data_integrity"] = {
                "status": "error",
                "message": f"Integrity check failed: {str(e)}",
                "icon": "❌"
            }
        
        # ✅ Service Dependencies
        try:
            # Check if critical functions exist
            from backend.ai_engine import detect_disease, analyze_water_source
            health_status["components"]["service_dependencies"] = {
                "status": "operational",
                "message": "All critical service dependencies available",
                "icon": "✅"
            }
        except Exception as e:
            health_status["components"]["service_dependencies"] = {
                "status": "error",
                "message": f"Dependency error: {str(e)}",
                "icon": "❌"
            }
            health_status["overall_status"] = "unhealthy"
        
        # Count status breakdown
        health_status["summary"] = {
            "total_checks": len(health_status["components"]),
            "passing": sum(1 for c in health_status["components"].values() if c["status"] == "operational"),
            "warning": sum(1 for c in health_status["components"].values() if c["status"] == "warning"),
            "error": sum(1 for c in health_status["components"].values() if c["status"] == "error")
        }
        
        app_logger.info(f"Developer {current_user.get('username')} requested health check")
        
        return health_status
    except Exception as e:
        app_logger.error(f"Health check error: {str(e)}")
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unhealthy",
            "error": str(e),
            "components": {}
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════
# USER PROFILE ENDPOINTS
# ═══════════════════════════════════════════════

# Get User Profile
@app.get("/api/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    """Get user profile with all details."""
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        
        # Get user basic info
        user = db.execute(
            "SELECT * FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Convert Row to dict for safe access
        user = dict(user)
        
        # Get profile details
        profile_row = db.execute(
            "SELECT * FROM user_profiles WHERE user_id=?",
            (user_id,)
        ).fetchone()
        
        profile = dict(profile_row) if profile_row else None
        
        # Calculate days active
        created_at = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        days_active = (datetime.now() - created_at).days
        
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "phone": user["phone"],
            "village": user["village"],
            "district": user["district"],
            "state": user["state"],
            "bio": profile.get("bio", "") if profile else "",
            "photo_path": profile.get("photo_path") if profile else None,
            "created_at": user["created_at"],
            "days_active": days_active,
            "last_login": user["last_login"],
            "is_approved": user["is_approved"],
            "is_active": user["is_active"]
        }
    finally:
        db.close()


# Update User Profile
@app.post("/api/profile/update")
async def update_profile(
    full_name: str = Form(None),
    phone: str = Form(None),
    bio: str = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Update user profile information."""
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        
        # Update user basic info
        if full_name:
            db.execute("UPDATE users SET full_name=? WHERE id=?", (full_name, user_id))
        if phone:
            db.execute("UPDATE users SET phone=? WHERE id=?", (phone, user_id))
        
        # Update or create profile record
        existing_profile = db.execute(
            "SELECT id FROM user_profiles WHERE user_id=?",
            (user_id,)
        ).fetchone()
        
        if existing_profile:
            db.execute(
                "UPDATE user_profiles SET bio=?, profile_updated_at=? WHERE user_id=?",
                (bio or "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
            )
        else:
            db.execute(
                "INSERT INTO user_profiles (user_id, bio) VALUES (?, ?)",
                (user_id, bio or "")
            )
        
        db.commit()
        app_logger.info(f"User {current_user.get('username')} updated profile")
        
        return {"message": "Profile updated successfully"}
    except Exception as e:
        app_logger.error(f"Error updating profile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# Upload Profile Photo
@app.post("/api/profile/upload-photo")
async def upload_photo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload profile photo."""
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        username = current_user.get("username")
        
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(UPLOAD_DIR, 'profiles')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = file.filename.split('.')[-1]
        filename = f"profile_{user_id}_{int(time.time())}.{file_extension}"
        file_path = os.path.join(upload_dir, filename)
        
        # Save file
        with open(file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        # Store path in database (relative to /uploads mount point)
        relative_path = f"profiles/{filename}"
        
        # Update or create profile record
        existing_profile = db.execute(
            "SELECT id FROM user_profiles WHERE user_id=?",
            (user_id,)
        ).fetchone()
        
        if existing_profile:
            db.execute(
                "UPDATE user_profiles SET photo_path=?, profile_updated_at=? WHERE user_id=?",
                (relative_path, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id)
            )
        else:
            db.execute(
                "INSERT INTO user_profiles (user_id, photo_path) VALUES (?, ?)",
                (user_id, relative_path)
            )
        
        db.commit()
        app_logger.info(f"User {username} uploaded profile photo")
        
        return {
            "message": "Photo uploaded successfully",
            "photo_path": relative_path,
            "filename": filename
        }
    except Exception as e:
        app_logger.error(f"Error uploading photo: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# Change Password
@app.post("/api/profile/change-password")
async def change_password(
    old_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Change user password."""
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        
        # Validate new password
        if new_password != confirm_password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        if len(new_password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Get user and verify old password
        user = db.execute(
            "SELECT password_hash FROM users WHERE id=?",
            (user_id,)
        ).fetchone()
        
        if not user or not verify_password(old_password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        
        # Update password
        hashed_password = hash_password(new_password)
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (hashed_password, user_id))
        db.commit()
        
        app_logger.info(f"User {current_user.get('username')} changed password")
        
        return {"message": "Password changed successfully"}
    except HTTPException:
        raise
    except Exception as e:
        app_logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ═══════════════════════════════════════════════
# WORKER-ADMIN MESSAGING ENDPOINTS
# ═══════════════════════════════════════════════

# Worker sends message to admin
@app.post("/api/worker/send-message")
async def send_message_to_admin(
    message_text: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Worker sends a message to admin."""
    db = get_db()
    try:
        # Only workers can send messages
        if current_user.get("role") != "worker":
            raise HTTPException(status_code=403, detail="Only workers can send messages to admin")
        
        worker_id = int(current_user["sub"])
        
        # Get first available admin
        admin = db.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
        if not admin:
            raise HTTPException(status_code=404, detail="No admin available")
        
        admin_id = admin["id"]
        
        # Save message
        db.execute(
            """INSERT INTO worker_messages (worker_id, admin_id, message_text)
               VALUES (?, ?, ?)""",
            (worker_id, admin_id, message_text)
        )
        db.commit()
        
        app_logger.info(f"Worker {current_user.get('username')} sent message to admin")
        
        return {"message": "Message sent successfully"}
    finally:
        db.close()


# Get messages for current user
@app.get("/api/messages")
async def get_messages(current_user: dict = Depends(get_current_user)):
    """Get messages for current user."""
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        user_role = current_user.get("role")
        
        if user_role == "worker":
            # Get messages sent by this worker
            messages = db.execute(
                """SELECT * FROM worker_messages 
                   WHERE worker_id=?
                   ORDER BY created_at DESC""",
                (user_id,)
            ).fetchall()
        elif user_role == "admin":
            # Get all messages received by this admin
            messages = db.execute(
                """SELECT wm.*, u.full_name, u.email, u.phone, u.village, u.district
                   FROM worker_messages wm
                   JOIN users u ON wm.worker_id = u.id
                   WHERE wm.admin_id=?
                   ORDER BY wm.created_at DESC""",
                (user_id,)
            ).fetchall()
        else:
            messages = []
        
        return [dict(m) for m in messages]
    finally:
        db.close()


# Admin replies to worker message
@app.post("/api/message/{message_id}/reply")
async def reply_to_message(
    message_id: int,
    reply_text: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Admin replies to a worker message."""
    db = get_db()
    try:
        # Only admins can reply
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Only admins can reply to messages")
        
        admin_id = int(current_user["sub"])
        
        # Verify message exists and belongs to this admin
        message = db.execute(
            "SELECT admin_id FROM worker_messages WHERE id=?",
            (message_id,)
        ).fetchone()
        
        if not message:
            raise HTTPException(status_code=404, detail="Message not found")
        
        if message["admin_id"] != admin_id:
            raise HTTPException(status_code=403, detail="You can only reply to your messages")
        
        # Update message with reply
        db.execute(
            """UPDATE worker_messages 
               SET reply_text=?, replied_at=? 
               WHERE id=?""",
            (reply_text, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message_id)
        )
        db.commit()
        
        app_logger.info(f"Admin {current_user.get('username')} replied to message {message_id}")
        
        return {"message": "Reply sent successfully"}
    finally:
        db.close()


# Mark message as read
@app.post("/api/message/{message_id}/read")
async def mark_message_read(
    message_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Mark message as read."""
    db = get_db()
    try:
        user_id = int(current_user["sub"])
        
        # Only admin can mark as read
        message = db.execute(
            "SELECT admin_id FROM worker_messages WHERE id=?",
            (message_id,)
        ).fetchone()
        
        if message and message["admin_id"] == user_id:
            db.execute(
                """UPDATE worker_messages 
                   SET is_read=1, read_at=? 
                   WHERE id=?""",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message_id)
            )
            db.commit()
        
        return {"message": "Message marked as read"}
    finally:
        db.close()


# Delete/Clear chat between admin and worker
@app.delete("/api/message/clear-chat/{worker_id}")
async def clear_chat(
    worker_id: int,
    current_user: dict = Depends(get_current_user)
):
    """Admin can clear entire conversation with a worker."""
    db = get_db()
    try:
        # Only admins can clear chats
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Only admins can clear chats")
        
        admin_id = int(current_user["sub"])
        
        # Delete all messages between this admin and worker
        db.execute(
            """DELETE FROM worker_messages 
               WHERE worker_id=? AND admin_id=?""",
            (worker_id, admin_id)
        )
        db.commit()
        
        app_logger.info(f"Admin {current_user.get('username')} cleared chat with worker {worker_id}")
        
        return {"message": "Chat cleared successfully"}
    finally:
        db.close()


# Users List with Role Filter
@app.get("/api/users")
async def get_users(
    role: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Get users list, optionally filtered by role."""
    db = get_db()
    try:
        if role:
            users = db.execute("""
                SELECT id, username, email, full_name, role, village, district, is_active, created_at
                FROM users WHERE role=? ORDER BY created_at DESC
            """, (role,)).fetchall()
        else:
            users = db.execute("""
                SELECT id, username, email, full_name, role, village, district, is_active, created_at
                FROM users ORDER BY created_at DESC
            """).fetchall()
        
        return [dict(u) for u in users]
    finally:
        db.close()


# ─── Serve Frontend ───
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if full_path == "" or full_path == "/":
        full_path = "index.html"
    file_path = os.path.join(FRONTEND_DIR, full_path)
    if os.path.isfile(file_path):
        # Handle binary files (videos, images, etc.)
        if file_path.endswith((".mp4", ".webm", ".ogg", ".png", ".jpg", ".jpeg", ".gif", ".ico")):
            return FileResponse(path=file_path)
        
        # Handle text files
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            content_type = "text/html"
            if file_path.endswith(".css"):
                content_type = "text/css"
            elif file_path.endswith(".js"):
                content_type = "application/javascript"
            return HTMLResponse(content=content, media_type=content_type)
        except UnicodeDecodeError:
            # If text decode fails, serve as binary
            return FileResponse(path=file_path)
    
    # Default to index.html for SPA
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Health Monitor - Setup Required</h1>", status_code=200)
