# HealthGuard NE - Smart Community Health Monitoring System

**Smart Community Health Monitoring and Early Warning System for Water-Borne Diseases in Rural Northeast India**

![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green)
![SQLite](https://img.shields.io/badge/Database-SQLite-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Quick Navigation

- [Overview](#overview) | [Features](#features) | [Quick Start](#quick-start)
- [Tech Stack](#technology-stack) | [Structure](#project-structure) | [API Docs](#api-documentation)
- [Database](#database-schema) | [Security](#authentication--security) | [Developer Portal](#developer-portal)
- **Detailed Docs**: See [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for in-depth technical information

---

## Overview

HealthGuard NE is an intelligent health monitoring system designed to track and predict water-borne disease outbreaks in rural communities across Northeast India.

**Key Capabilities**:
- Real-time risk assessment based on symptom reports
- Early warning alerts for potential outbreaks
- Multi-role dashboards (admin, worker, user, developer)
- AI-powered disease detection and analysis
- Comprehensive logging and activity tracking
- Session management and system monitoring

---

## ✨ Key Features

### For Community Members
- 📝 Submit symptom reports
- ⚠️ View village-level disease risk and trends
- 💧 Access water purification guides
- 💡 Receive health tips
- 🔔 Get alerts and notifications

### For Health Workers
- 🏥 Submit single/bulk reports
- 📊 View performance metrics
- 🎓 Access training chatbot
- 📋 Edit submitted reports
- 💬 Provide feedback

### For Administrators  
- 👥 Manage users (approve, delete, deactivate)
- 📊 View analytics and trends
- 🚨 Create and broadcast alerts
- 📢 Send notices to users
- 📈 Export reports to CSV
- ⚙️ Configure system settings

### For Developers (NEW - March 2026)
- 🔍 Monitor system errors and exceptions
- 👥 Track user activity and sessions
- 📝 View application logs with color-coding
- 💬 Manage user feedback
- 📢 Broadcast notices to specific roles
- 🗑️ Delete old sessions (24hr/7d/30d/all)
- ✅ Manage admin/developer accounts

---

## 🛠 Technology Stack

### Backend
- **FastAPI** (0.104.1) - Async web framework
- **Python 3.12** - Programming language
- **SQLite 3** - Database with WAL mode
- **JOSE** - JWT token handling
- **Uvicorn** - ASGI server

### Frontend
- **Vanilla JavaScript** - No framework
- **HTML5 & CSS3** - Markup and styling
- **Chart.js** - Data visualization
- **localStorage** - Client-side storage

### AI/ML
- scikit-learn, LightGBM, XGBoost, Pandas, NumPy

### Infrastructure
- Python logging with file rotation (10MB, 10 backups)
- CORS middleware for cross-origin requests

---

## 3. Project Structure

```
Health_wath_ne/
├── backend/
│   ├── main.py              # FastAPI (1600+ lines, 45+ endpoints)
│   ├── auth.py              # Authentication
│   ├── database.py          # SQLite schema
│   ├── ai_engine.py         # Risk scoring
│   └── uploads/             # User files
├── frontend/
│   ├── index.html           # Main page
│   ├── css/style.css        # Styling
│   └── js/
│       ├── utils.js         # API helpers
│       ├── auth.js          # Login/register
│       ├── app.js           # Main app
│       ├── admin.js         # Admin dashboard
│       ├── worker.js        # Worker dashboard
│       ├── user.js          # User dashboard
│       └── developer.js     # Developer portal (NEW)
├── logs/
│   ├── README.md            # Logging docs
│   └── app.log              # App log (auto-created)
├── run.py                   # Server startup
├── requirements.txt         # Dependencies
├── health_monitor.db        # Database (auto-created)
└── PROJECT_DOCUMENTATION.md # Technical docs
```

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.12+
- pip package manager
- Modern web browser

### Installation

1. **Clone the repository**
   ```bash
   cd Health_wath_ne
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python run.py
   ```

4. **Access the application**
   - Open browser: `http://127.0.0.1:8000`
   - Database auto-initializes on first run
   - Default accounts created (see below)

### Default Accounts (Change in Production!)

| Role | Email | Password | Secret Key |
|------|-------|----------|-----------|
| Admin | admin@health.gov.in | admin123 | 8951 |
| Developer | bhuvan330bhuvi@gmail.com | Bhuvan#2004 | 2026 |
| Developer | naikprashant837@gmail.com | Prashant#2004 | 2026 |

---

## 👥 User Roles & Access

### 1. Community Member
- **Access**: Immediate after registration
- **Features**: Report symptoms, view risk, get alerts
- **Endpoints**: `/api/user/*, /api/alerts, /api/notices`

### 2. Health Worker
- **Access**: After admin approval
- **Features**: Submit reports, view metrics, use chatbot
- **Endpoints**: `/api/worker/*, /api/alerts`

### 3. Administrator
- **Access**: Secret key (8951) verification required
- **Features**: Manage users, create alerts, view analytics
- **Endpoints**: `/api/admin/*, /api/auth/verify-secret-key`

### 4. Developer
- **Access**: Secret key (2026) required for login
- **Features**: Monitor errors, track activity, manage sessions
- **Endpoints**: `/api/dev/*, /api/auth/dev-login`

---

## 📡 API Documentation

### Authentication (4 endpoints)
```
POST /api/auth/register          # Register new user
POST /api/auth/login             # Login with verification code
POST /api/auth/dev-login         # Developer login
POST /api/auth/verify-secret-key # Verify admin/dev secret
```

### User Features
```
POST /api/user/symptom-report    # Submit symptoms
GET  /api/user/risk-status       # Get village risk
GET  /api/user/my-reports        # Get personal reports
```

### Worker Features
```
POST /api/worker/reports         # Submit report
POST /api/worker/reports/bulk    # Bulk upload
GET  /api/worker/my-reports      # Get worker reports
```

### Admin Features
```
GET  /api/admin/dashboard        # System overview
GET  /api/admin/reports          # All reports
POST /api/admin/alerts           # Create alert
POST /api/admin/notices          # Send notice
DELETE /api/admin/users/{id}     # Remove user
```

### Developer Features (NEW)
```
GET  /api/dev/dashboard          # Statistics
GET  /api/dev/error-logs         # Error logs
GET  /api/dev/user-activity      # Sessions
POST /api/dev/delete-sessions    # Delete sessions by age
GET  /api/dev/logs               # Application logs
GET  /api/dev/feedback           # User feedback
POST /api/dev/send-notice        # Broadcast notice
```

### Public Access (5 endpoints)
```
GET  /api/alerts                 # Health alerts
GET  /api/notices                # Public notices
GET  /api/districts              # All districts
GET  /api/villages               # Villages by district
GET  /api/weather/{city}         # Weather info
```

**Total**: 45+ fully functional endpoints

For complete API documentation, see [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)

---

## 🔐 Authentication & Security

### Password Security
- **Algorithm**: SHA-256 with random salt
- **Format**: `salt$hash_value`
- **Verification**: On every login

### JWT Tokens
- **Duration**: 24 hours from issuance
- **Payload**: user_id, username, role, name, village, district
- **Storage**: localStorage (frontend)
- **Refresh**: Fresh token on every API request

### Verification Codes (30-Second TOTP)
- **Duration**: 30 seconds per code block
- **Algorithm**: `(block * 9973) % 10000`
- **Security**: Code changes every 30 seconds, no replay

### Secret Keys
- **Admin**: 8951 (required after login)
- **Developer**: 2026 (required for login)
- **Purpose**: Additional authentication layer

---

## 🔧 Developer Portal

### 8 Feature Menu

1. **📊 Dashboard** - System statistics and overview
2. **🔴 Error Logs** - View and filter system errors
3. **👥 User Activity** - Monitor sessions, delete by age
4. **💬 Feedback** - Review and respond to feedback
5. **📢 Send Notice** - Broadcast to specific roles
6. **📝 App Logs** - View application logs (color-coded)
7. **⚙️ Manage Admins** - Create/manage admin accounts
8. **⚙️ Manage Developers** - Create/manage dev accounts

### Session Management
- View active sessions with login time, duration, IP
- Delete sessions by age:
  - Last 24 hours
  - Last 7 days
  - Last 30 days
  - All sessions
- Individual session deletion
- Safety confirmations on all deletions

---

## 📊 Database Structure

### Main Tables
- **users** - User accounts (admin, worker, user, developer)
- **health_reports** - Worker-submitted reports
- **symptom_reports** - Public symptom reports
- **user_sessions** - Session and activity tracking
- **error_logs** - System error logs
- **feedback** - User feedback and suggestions
- **dev_notices** - Developer broadcast notices
- **alerts, notifications, notices** - System messages

### Entity Relationships
```
users ──┬──> health_reports (worker_id)
        ├──> symptom_reports (user_id)
        ├──> user_sessions (user_id)
        ├──> error_logs
        ├──> feedback (from_user_id)
        └──> dev_notices (created_by)
```

---

## 📝 Logging System

### Features
- **File**: logs/app.log (auto-created)
- **Rotation**: 10MB per file, 10 backup files
- **Format**: `YYYY-MM-DD HH:MM:SS - logger_name - LEVEL - [file:line] - message`
- **Levels**: INFO (🔵), WARNING (🟡), ERROR (🔴), DEBUG (🟣)

### What Gets Logged
- User registration and authentication events
- Report submissions and alerts
- Session management and deletions
- System startup/shutdown
- All errors and exceptions
- Developer activity

### Access Methods
- **Developer Portal**: Click "📝 App Logs" in menu
- **API**: `GET /api/dev/logs?lines=100`
- **File**: logs/app.log (direct access)

See [logs/README.md](logs/README.md) for detailed logging documentation

---

## 🐛 Troubleshooting

### Database Not Found
```bash
# Database auto-creates on first run
# If issues, delete and restart:
rm health_monitor.db
python run.py
```

### Port Already in Use
```bash
# Linux/macOS:
lsof -i :8000
kill -9 <PID>

# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Login/Verification Code Issues
- System time must be synchronized (code is time-based)
- Code changes every 30 seconds
- Clear browser localStorage if stuck: F12 → Applications → Clear
- Try incognito mode

### Unicode/Console Errors
- Already fixed for Windows compatibility
- Logging uses UTF-8 encoding
- Console output uses ASCII-safe text

### Session/Token Errors
- Clear localStorage
- Login again to refresh token
- Check system clock synchronization

---

## ✅ Deployment Checklist

- [ ] Change default admin/developer passwords
- [ ] Update secret keys (8951, 2026)
- [ ] Configure CORS for production domain
- [ ] Set up SSL/HTTPS certificate
- [ ] Create automated database backups
- [ ] Review and update error messages
- [ ] Test all user roles thoroughly
- [ ] Set up monitoring/alerting
- [ ] Document deployment process
- [ ] Review security configuration

---

## 📚 Documentation

- **[PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)** - Complete technical reference (15+ sections)
- **[logs/README.md](logs/README.md)** - Logging system details
- **[requirements.txt](requirements.txt)** - Python dependencies with versions

---

## 🔗 Quick Reference

| Item | Value |
|------|-------|
| **Server URL** | http://127.0.0.1:8000 |
| **Database** | health_monitor.db (SQLite) |
| **Logs** | logs/app.log |
| **Admin Secret** | 8951 |
| **Developer Secret** | 2026 |
| **Default Port** | 8000 |
| **API Endpoints** | 45+ |
| **User Roles** | 4 (admin, worker, user, dev) |

---

## 📱 System Requirements

**Minimum**:
- CPU: 2 cores | RAM: 2GB | Storage: 1GB
- Python 3.12+ | Modern web browser

**Recommended**:
- CPU: 4+ cores | RAM: 8GB | Storage: 50GB
- Linux/macOS server deployment

---

## 📄 Version & Status

**Version**: 1.0.0  
**Last Updated**: March 27, 2026  
**Status**: Production Ready ✅

---

## 📞 Support

1. Check [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for detailed information
2. Review [logs/README.md](logs/README.md) for logging documentation
3. Check logs/app.log for error messages
4. See Troubleshooting section above

---

**Built with ❤️ for Smart Community Health Monitoring in Rural Northeast India**

