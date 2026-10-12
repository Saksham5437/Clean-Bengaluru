from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Literal
import hashlib, hmac, os, secrets
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, text

try:
    import sys
    from dotenv import load_dotenv
    if "pytest" not in sys.modules:
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Clean Bengaluru API", version="1.0.0")
origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if item.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH"], allow_headers=["*"])

MYSQL_DATABASE_URL = os.getenv("MYSQL_DATABASE_URL", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
CAMERA_INGEST_KEY = os.getenv("CAMERA_INGEST_KEY", "")
if ENVIRONMENT == "production" and not MYSQL_DATABASE_URL:
    raise RuntimeError("MYSQL_DATABASE_URL is required when ENVIRONMENT=production")
if ENVIRONMENT == "production" and CAMERA_INGEST_KEY and len(CAMERA_INGEST_KEY) < 32:
    raise RuntimeError("CAMERA_INGEST_KEY must be at least 32 characters in production")
engine = create_engine(MYSQL_DATABASE_URL, pool_pre_ping=True, pool_recycle=1800) if MYSQL_DATABASE_URL else None
memory_users: dict[str, dict] = {}
memory_sessions: dict[str, dict] = {}
memory_reports: dict[str, dict] = {}
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "storage" / "uploads"
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
IMAGE_SIGNATURES = {"image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",), "image/webp": (b"RIFF", b"WEBP")}

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"

def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        check = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=int(n), r=int(r), p=int(p))
        return scheme == "scrypt" and hmac.compare_digest(check.hex(), digest_hex)
    except (ValueError, TypeError):
        return False

def public_user(user: dict) -> dict:
    return {"id": str(user["id"]), "full_name": user["full_name"], "email": user["email"], "role": user["role"]}

def public_report(report: dict) -> dict:
    result = {key: (str(value) if key in {"id", "user_id"} and value is not None else value) for key, value in report.items()}
    if result.get("evidence_url"):
        result["evidence_url"] = f"/api/v1/reports/{result['case_id']}/evidence"
    return result

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=24)
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class StatusRequest(BaseModel):
    status: Literal["submitted", "assigned", "in_progress", "resolved", "rejected"]

class CameraSignal(BaseModel):
    route_id: str = Field(min_length=2, max_length=80)
    location: str = Field(min_length=3, max_length=240)
    category: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    density_score: int = Field(ge=0, le=100)
    severity: Literal["low", "moderate", "high", "critical"]

def create_session(user: dict) -> dict:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    if engine:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO sessions (id, user_id, expires_at) VALUES (:token, :user_id, :expires_at)"), {"token": token, "user_id": user["id"], "expires_at": expires})
    else:
        memory_sessions[token] = {"user_id": user["id"], "expires_at": expires, "user": user}
    return {"access_token": token, "token_type": "bearer", "expires_at": expires, "user": public_user(user)}

def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication is required")
    token = authorization.split(" ", 1)[1].strip()
    if engine:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT u.id, u.full_name, u.email, u.phone, u.role FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.id = :token AND s.expires_at > UTC_TIMESTAMP() AND u.is_active = TRUE"), {"token": token}).mappings().first()
            user = dict(row) if row else None
    else:
        session = memory_sessions.get(token)
        user = session.get("user") if session and session["expires_at"] > datetime.now(timezone.utc) else None
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user

def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required")
    return user

@app.get("/health")
def health():
    return {"status": "ok", "service": "clean-bengaluru-api", "database": "mysql" if engine else "development_memory_store"}

@app.get("/ready")
def ready():
    if engine:
        try:
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            raise HTTPException(status_code=503, detail="Database is not ready")
    return {"status": "ready", "service": "clean-bengaluru-api", "database": "mysql" if engine else "development_memory_store"}

@app.post("/api/v1/auth/register", status_code=201)
def register(payload: RegisterRequest):
    email = str(payload.email).lower().strip()
    user = {"id": str(uuid4()), "full_name": payload.full_name.strip(), "email": email, "phone": payload.phone, "password_hash": hash_password(payload.password), "role": "user"}
    if engine:
        try:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO users (id, full_name, email, phone, password_hash, role) VALUES (:id, :full_name, :email, :phone, :password_hash, 'user')"), user)
        except Exception as exc:
            if "Duplicate" in str(exc) or "duplicate" in str(exc):
                raise HTTPException(status_code=409, detail="An account with this email already exists")
            raise HTTPException(status_code=503, detail="Database is unavailable")
    else:
        if email in memory_users:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        memory_users[email] = user
    return create_session(user)

def find_user(email: str) -> dict | None:
    if engine:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT id, full_name, email, phone, password_hash, role FROM users WHERE email = :email AND is_active = TRUE"), {"email": email}).mappings().first()
            return dict(row) if row else None
    return memory_users.get(email)

@app.post("/api/v1/auth/login")
def login(payload: LoginRequest):
    user = find_user(str(payload.email).lower().strip())
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return create_session(user)

@app.post("/api/v1/auth/admin-login")
def admin_login(payload: LoginRequest):
    user = find_user(str(payload.email).lower().strip())
    if not user or user["role"] != "admin" or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Administrator email or password is incorrect")
    return create_session(user)

@app.post("/api/v1/auth/logout")
def logout(authorization: str | None = Header(default=None), user: dict = Depends(current_user)):
    token = authorization.split(" ", 1)[1].strip()
    if engine:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM sessions WHERE id = :token"), {"token": token})
    else:
        memory_sessions.pop(token, None)
    return {"ok": True}

@app.get("/api/v1/me")
def me(user: dict = Depends(current_user)):
    return {"user": public_user(user)}

@app.post("/api/v1/ingest/camera", status_code=201)
def ingest_camera_signal(payload: CameraSignal, camera_key: str | None = Header(default=None, alias="X-Camera-Key")):
    configured_key = CAMERA_INGEST_KEY
    if not configured_key:
        raise HTTPException(status_code=503, detail="Camera ingestion is not configured")
    if not camera_key or not hmac.compare_digest(camera_key, configured_key):
        raise HTTPException(status_code=401, detail="Invalid camera credential")
    now = datetime.now(timezone.utc)
    report = {"id": str(uuid4()), "case_id": f"CB-CAM-{now.year}-{secrets.token_hex(3).upper()}", "user_id": None, "source": "bus_camera", "category": payload.category, "description": f"Route {payload.route_id}: {payload.description or 'Camera-detected roadside waste signal'}", "location_label": payload.location.strip(), "latitude": payload.latitude, "longitude": payload.longitude, "evidence_url": None, "density_score": payload.density_score, "severity": payload.severity, "status": "submitted", "created_at": now, "updated_at": now, "sender_name": f"Camera route {payload.route_id}", "sender_email": None}
    if engine:
        try:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO reports (id, case_id, source, category, description, location_label, latitude, longitude, density_score, severity, status) VALUES (:id, :case_id, :source, :category, :description, :location_label, :latitude, :longitude, :density_score, :severity, :status)"), report)
                conn.execute(text("INSERT INTO report_events (report_id, previous_status, new_status, note) VALUES (:report_id, NULL, 'submitted', :note)"), {"report_id": report["id"], "note": f"Camera signal received from route {payload.route_id}"})
        except Exception:
            raise HTTPException(status_code=503, detail="Camera signal storage is temporarily unavailable")
    else:
        report["events"] = [{"previous_status": None, "new_status": "submitted", "note": f"Camera signal received from route {payload.route_id}", "created_at": now}]
        memory_reports[report["case_id"]] = report
    return {"case_id": report["case_id"], "source": report["source"], "status": report["status"], "received_at": now}

@app.get("/api/v1/hotspots")
def hotspots():
    return {"items": [{"name": "Hosur Road underpass", "area": "Adugodi", "score": 82, "severity": "critical"}, {"name": "Outer Ring Road", "area": "Bellandur", "score": 68, "severity": "high"}, {"name": "8th Main, Koramangala", "area": "Koramangala", "score": 41, "severity": "moderate"}]}

@app.post("/api/v1/reports", status_code=201)
async def create_report(location: str = Form(..., min_length=3, max_length=240), category: str = Form(..., min_length=2, max_length=80), description: str | None = Form(default=None, max_length=1000), latitude: float | None = Form(default=None, ge=-90, le=90), longitude: float | None = Form(default=None, ge=-180, le=180), photo: UploadFile | None = File(default=None), user: dict = Depends(current_user)):
    location = location.strip()
    category = category.strip()
    if len(location) < 3 or len(category) < 2:
        raise HTTPException(status_code=422, detail="Location and category cannot be blank")
    evidence_url = None
    if photo and photo.filename:
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail="Only JPG, PNG, and WebP images are accepted")
        content = await photo.read(MAX_UPLOAD_BYTES + 1)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Image must be 10 MB or smaller")
        if photo.content_type == "image/webp":
            valid_signature = len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
        else:
            valid_signature = any(content.startswith(signature) for signature in IMAGE_SIGNATURES[photo.content_type])
        if not valid_signature:
            raise HTTPException(status_code=415, detail="The uploaded file is not a valid image")
        safe_name = f"{uuid4().hex}{ALLOWED_IMAGE_TYPES[photo.content_type]}"
        (UPLOAD_ROOT / safe_name).write_bytes(content)
        evidence_url = f"/uploads/{safe_name}"
    report = {"id": str(uuid4()), "case_id": f"CB-{datetime.now(timezone.utc).year}-{secrets.token_hex(3).upper()}", "user_id": user["id"], "source": "citizen", "category": category, "description": description, "location_label": location.strip(), "latitude": latitude, "longitude": longitude, "evidence_url": evidence_url, "density_score": None, "severity": None, "status": "submitted", "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc), "sender_name": user["full_name"], "sender_email": user["email"]}
    private_evidence_url = f"/api/v1/reports/{report['case_id']}/evidence" if evidence_url else None
    if engine:
        try:
            with engine.begin() as conn:
                conn.execute(text("INSERT INTO reports (id, case_id, user_id, source, category, description, location_label, latitude, longitude, evidence_url, status) VALUES (:id, :case_id, :user_id, :source, :category, :description, :location_label, :latitude, :longitude, :evidence_url, :status)"), report)
                conn.execute(text("INSERT INTO report_events (report_id, previous_status, new_status, note) VALUES (:report_id, NULL, 'submitted', 'Resident report submitted')"), {"report_id": report["id"]})
        except Exception:
            if evidence_url:
                (UPLOAD_ROOT / Path(evidence_url).name).unlink(missing_ok=True)
            raise HTTPException(status_code=503, detail="Report storage is temporarily unavailable")
    else:
        report["events"] = [{"previous_status": None, "new_status": "submitted", "note": "Resident report submitted", "created_at": report["created_at"]}]
        memory_reports[report["case_id"]] = report
    return {"case_id": report["case_id"], "status": report["status"], "received_at": report["created_at"], "evidence_url": private_evidence_url}

@app.get("/api/v1/reports/{case_id}/evidence")
def report_evidence(case_id: str, user: dict = Depends(current_user)):
    if engine:
        with engine.begin() as conn:
            row = conn.execute(text("SELECT evidence_url, user_id FROM reports WHERE case_id = :case_id"), {"case_id": case_id}).mappings().first()
            report = dict(row) if row else None
    else:
        report = memory_reports.get(case_id)
    if not report or not report.get("evidence_url"):
        raise HTTPException(status_code=404, detail="Evidence not found")
    if user["role"] != "admin" and str(report.get("user_id")) != str(user["id"]):
        raise HTTPException(status_code=403, detail="You cannot view this evidence")
    filename = Path(report["evidence_url"]).name
    file_path = UPLOAD_ROOT / filename
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file is unavailable")
    return FileResponse(file_path)

def report_rows(user: dict | None = None) -> list[dict]:
    if engine:
        query = "SELECT r.*, u.full_name AS sender_name, u.email AS sender_email, u.phone AS sender_phone FROM reports r LEFT JOIN users u ON u.id = r.user_id"
        params = {}
        if user and user["role"] != "admin":
            query += " WHERE r.user_id = :user_id"
            params["user_id"] = user["id"]
        query += " ORDER BY r.created_at DESC"
        with engine.begin() as conn:
            return [dict(row) for row in conn.execute(text(query), params).mappings().all()]
    rows = list(memory_reports.values())
    if user and user["role"] != "admin":
        rows = [row for row in rows if row["user_id"] == user["id"]]
    return sorted(rows, key=lambda item: item["created_at"], reverse=True)

@app.get("/api/v1/reports")
def reports(user: dict = Depends(admin_user)):
    return {"items": [public_report(row) for row in report_rows(user)]}

@app.get("/api/v1/reports/mine")
def my_reports(user: dict = Depends(current_user)):
    return {"items": [public_report(row) for row in report_rows(user)]}

@app.get("/api/v1/reports/{case_id}")
def report_detail(case_id: str, user: dict = Depends(current_user)):
    rows = report_rows(user)
    report = next((item for item in rows if item["case_id"] == case_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if engine:
        with engine.begin() as conn:
            events = [dict(row) for row in conn.execute(text("SELECT previous_status, new_status, note, created_at FROM report_events WHERE report_id = :report_id ORDER BY created_at ASC, id ASC"), {"report_id": report["id"]}).mappings().all()]
    else:
        events = report.get("events", [])
    return {"report": public_report(report), "events": events}

@app.patch("/api/v1/reports/{case_id}/status")
def update_report_status(case_id: str, payload: StatusRequest, user: dict = Depends(admin_user)):
    if engine:
        with engine.begin() as conn:
            current = conn.execute(text("SELECT id, status FROM reports WHERE case_id = :case_id"), {"case_id": case_id}).mappings().first()
            if not current:
                raise HTTPException(status_code=404, detail="Report not found")
            conn.execute(text("UPDATE reports SET status = :status WHERE case_id = :case_id"), {"status": payload.status, "case_id": case_id})
            conn.execute(text("INSERT INTO report_events (report_id, previous_status, new_status, actor_user_id, note) VALUES (:report_id, :previous_status, :new_status, :actor_user_id, :note)"), {"report_id": current["id"], "previous_status": current["status"], "new_status": payload.status, "actor_user_id": user["id"], "note": f"Status changed by {user['full_name']}"})
    elif case_id in memory_reports:
        previous = memory_reports[case_id]["status"]
        memory_reports[case_id]["status"] = payload.status
        memory_reports[case_id].setdefault("events", []).append({"previous_status": previous, "new_status": payload.status, "note": f"Status changed by {user['full_name']}", "created_at": datetime.now(timezone.utc)})
    else:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"case_id": case_id, "status": payload.status, "updated_by": public_user(user)}
