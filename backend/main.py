"""
Main FastAPI application.
Smart Community Health Monitoring & Early Warning System
"""
import os
import json
import shutil
import csv
import io
import httpx
from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import get_db, init_db
from backend.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin, require_worker
)
from backend.ai_engine import (
    calculate_village_risk, detect_disease, detect_fake_report,
    analyze_water_source, generate_trend_data, get_health_tips,
    get_safe_water_guide, calculate_symptom_score
)

app = FastAPI(title="Health Monitor API", version="1.0.0")


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
    init_db()
    # Set default admin password if not set yet
    db = get_db()
    admin = db.execute("SELECT * FROM users WHERE username='admin'").fetchone()
    if admin and admin["password_hash"] == "NEEDS_SETUP":
        hashed = hash_password("admin123")
        db.execute("UPDATE users SET password_hash=? WHERE username='admin'", (hashed,))
        db.commit()
    db.close()


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
            raise HTTPException(400, "Username or email already exists")

        is_approved = 1 if role == "user" else 0
        db.execute("""INSERT INTO users (username, email, password_hash, full_name, role,
                      phone, village, district, is_approved)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (username, email, hash_password(password), full_name,
                    role, phone, village, district, is_approved))
        db.commit()

        msg = "Registration successful!" if role == "user" else "Registration submitted. Awaiting admin approval."
        return {"message": msg, "role": role, "is_approved": is_approved}
    finally:
        db.close()


@app.post("/api/auth/login")
async def login(
    username: str = Form(...),
    password: str = Form(...)
):
    db = get_db()
    try:
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if not user or not verify_password(password, user["password_hash"]):
            raise HTTPException(401, "Invalid credentials")
        if not user["is_approved"]:
            raise HTTPException(403, "Account pending approval. Please wait for admin to approve.")
        if not user["is_active"]:
            raise HTTPException(403, "Account has been deactivated")

        db.execute("UPDATE users SET last_login=? WHERE id=?",
                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user["id"]))
        db.commit()

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
        user_id = int(current_user["sub"])
        notifs = db.execute("""SELECT * FROM notifications WHERE user_id=?
                              ORDER BY created_at DESC LIMIT 50""", (user_id,)).fetchall()
        unread = db.execute("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0",
                            (user_id,)).fetchone()["c"]
        return {"notifications": [dict(n) for n in notifs], "unread_count": unread}
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
