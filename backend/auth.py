"""
Authentication module - JWT token based auth with hashlib password hashing.
"""
import hashlib
import secrets
import time
import sqlite3
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

SECRET_KEY = "health-monitor-secret-key-2024-northeast-india"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

security = HTTPBearer()


def get_db_for_auth():
    """Get database connection for auth operations."""
    import os
    DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "health_monitor.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def track_failed_secret_attempt(user_id: int, email: str, role: str) -> bool:
    """Track failed secret code attempt and block if 3 attempts. Returns True if user should be blocked."""
    db = get_db_for_auth()
    try:
        # Check existing attempts
        attempt = db.execute(
            "SELECT * FROM secret_code_attempts WHERE user_id=?",
            (user_id,)
        ).fetchone()
        
        if attempt:
            new_count = attempt['attempt_count'] + 1
            if new_count >= 3:
                # Block the user
                db.execute(
                    "UPDATE secret_code_attempts SET attempt_count=?, blocked=1, blocked_at=? WHERE user_id=?",
                    (new_count, datetime.utcnow(), user_id)
                )
                # Also block in users table
                db.execute(
                    "UPDATE users SET is_blocked=1, blocked_reason=?, blocked_at=? WHERE id=?",
                    (f"Blocked after {new_count} failed secret code attempts", datetime.utcnow(), user_id)
                )
                db.commit()
                return True
            else:
                # Update attempt count
                db.execute(
                    "UPDATE secret_code_attempts SET attempt_count=?, last_attempt=? WHERE user_id=?",
                    (new_count, datetime.utcnow(), user_id)
                )
                db.commit()
                return False
        else:
            # First attempt
            db.execute(
                "INSERT INTO secret_code_attempts (user_id, user_email, user_role, attempt_count) VALUES (?, ?, ?, 1)",
                (user_id, email, role)
            )
            db.commit()
            return False
    finally:
        db.close()


def generate_verification_code() -> str:
    """Generate 4-digit code based on current time (changes every 30 seconds)."""
    now = int(time.time())
    block = now // 30  # 30-second blocks
    seed = block * 9973  # Prime number for better distribution
    code = abs(seed) % 10000
    return str(code).zfill(4)


def verify_verification_code(provided_code: str) -> bool:
    """Verify if provided code matches ONLY the current code. Code expires after 30 seconds."""
    current = generate_verification_code()
    return provided_code == current


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with a random salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash."""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
        check_hash = hashlib.sha256((salt + plain_password).encode()).hexdigest()
        return check_hash == stored_hash
    except (ValueError, AttributeError):
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials"
        )
    
    try:
        token = credentials.credentials
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing token in Authorization header"
            )
        payload = decode_token(token)
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )


async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_worker(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "worker":
        raise HTTPException(status_code=403, detail="Worker access required")
    return current_user


async def require_developer(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "developer":
        raise HTTPException(status_code=403, detail="Developer access required")
    return current_user
