"""Seed comprehensive resident candidates and reports with real evidence images.

This script populates MySQL clean_bengaluru database with:
- Realistic resident candidates (citizens) across Bengaluru wards
- Civic waste reports with verified evidence photos saved to storage/uploads
- Realistic lifecycle events in report_events for each case
"""
from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
import secrets
import urllib.request
from uuid import uuid4
import os

from dotenv import load_dotenv
import pymysql

# Load project environment
PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DB_URL = os.getenv("MYSQL_DATABASE_URL", "mysql+pymysql://root:Sakre5437@127.0.0.1:3306/clean_bengaluru")
# Parse standard pymysql parameters
import re
match = re.match(r"mysql\+pymysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)", DB_URL)
if not match:
    raise ValueError(f"Could not parse DB_URL: {DB_URL}")
db_user, db_pass, db_host, db_port, db_name = match.groups()

UPLOAD_DIR = PROJECT_ROOT / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
    return f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"

CANDIDATES = [
    {"name": "Saksham Kulkarni", "email": "saksham@example.com", "phone": "+91 98765 54421"},
    {"name": "Rishikesh V Reddy", "email": "rishikesh.reddy@example.com", "phone": "+91 91876 54008"},
    {"name": "N Shreyas Adithya", "email": "shreyas.adithya@example.com", "phone": "+91 90123 45572"},
    {"name": "Ananya Rao", "email": "ananya.rao@example.com", "phone": "+91 98450 12345"},
    {"name": "Deepak Sundaram", "email": "deepak.sundaram@example.com", "phone": "+91 97401 98765"},
    {"name": "Pooja Hegde", "email": "pooja.hegde@example.com", "phone": "+91 99002 33445"},
    {"name": "Arjun Nair", "email": "arjun.nair@example.com", "phone": "+91 96118 77654"},
    {"name": "Kavitha Murthy", "email": "kavitha.murthy@example.com", "phone": "+91 94480 88990"},
    {"name": "Siddharth Rao", "email": "siddharth.rao@example.com", "phone": "+91 98860 11223"},
]

DEFAULT_PASSWORD = "Resident@CleanBlr2026"

REPORT_DATA = [
    {
        "case_id": "CB-2026-01482",
        "candidate_idx": 0,
        "source": "citizen",
        "category": "roadside_garbage",
        "description": "Continuous accumulation of black garbage bags along the pedestrian sidewalk near the corner tree.",
        "location": "8th Main, Koramangala 4th Block",
        "lat": 12.9352, "lng": 77.6245,
        "density_score": 41,
        "severity": "moderate",
        "status": "assigned",
        "img_url": "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 25,
        "events": [
            ("submitted", "Resident report submitted with photo evidence", 25),
            ("assigned", "Assigned to Ward 151 health inspector team for morning clearance", 15)
        ]
    },
    {
        "case_id": "CB-2026-01477",
        "candidate_idx": 1,
        "source": "bus_camera",
        "category": "illegal_dumping",
        "description": "Automated vision trigger: large debris pile discarded near service road stormwater drain.",
        "location": "Outer Ring Road, Bellandur Service Road",
        "lat": 12.9304, "lng": 77.6784,
        "density_score": 68,
        "severity": "high",
        "status": "submitted",
        "img_url": "https://images.unsplash.com/photo-1605600659908-0ef719419d41?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 45,
        "events": [
            ("submitted", "Bus-camera vision trigger received from Route 500D (confidence 92%)", 45)
        ]
    },
    {
        "case_id": "CB-2026-01465",
        "candidate_idx": 2,
        "source": "citizen",
        "category": "overflowing_bin",
        "description": "Community bin overflowing onto roadway causing foul smell and stray cattle gathering.",
        "location": "Hosur Road Underpass, Adugodi",
        "lat": 12.9417, "lng": 77.6101,
        "density_score": 82,
        "severity": "critical",
        "status": "in_progress",
        "img_url": "https://images.unsplash.com/photo-1530587191325-3db32d826c18?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 90,
        "events": [
            ("submitted", "Resident report submitted with photo evidence", 90),
            ("assigned", "Ward supervisor notified for emergency compactor dispatch", 75),
            ("in_progress", "Compactor truck KA-01-EA-4921 deployed to site", 30)
        ]
    },
    {
        "case_id": "CB-2026-01490",
        "candidate_idx": 3,
        "source": "citizen",
        "category": "construction_waste",
        "description": "Cement bags and plaster debris dumped on footpath blocking elderly pedestrian access.",
        "location": "100 Feet Road, Indiranagar",
        "lat": 12.9719, "lng": 77.6412,
        "density_score": 55,
        "severity": "moderate",
        "status": "assigned",
        "img_url": "https://images.unsplash.com/photo-1590496793929-36417d3117de?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 120,
        "events": [
            ("submitted", "Resident report submitted", 120),
            ("assigned", "Routed to East Zone civil works enforcement squad", 60)
        ]
    },
    {
        "case_id": "CB-2026-01495",
        "candidate_idx": 4,
        "source": "citizen",
        "category": "roadside_garbage",
        "description": "Piles of mixed municipal solid waste scattered after overnight storm near park gate.",
        "location": "27th Main, HSR Layout Sector 2",
        "lat": 12.9116, "lng": 77.6533,
        "density_score": 74,
        "severity": "high",
        "status": "in_progress",
        "img_url": "https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 180,
        "events": [
            ("submitted", "Resident report submitted", 180),
            ("assigned", "Assigned to HSR Sector 2 pourakarmika marshals", 140),
            ("in_progress", "Morning cleanup beat team on site with mini-tipper", 40)
        ]
    },
    {
        "case_id": "CB-2026-01502",
        "candidate_idx": 5,
        "source": "citizen",
        "category": "overflowing_bin",
        "description": "Commercial market wet waste bin overflowing onto vendor lane causing severe health hazard.",
        "location": "8th Cross, Malleshwaram Market",
        "lat": 13.0031, "lng": 77.5694,
        "density_score": 88,
        "severity": "critical",
        "status": "submitted",
        "img_url": "https://images.unsplash.com/photo-1528190336454-13cd56b45b5a?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 50,
        "events": [
            ("submitted", "High-priority commercial zone report received", 50)
        ]
    },
    {
        "case_id": "CB-CAM-2026-00314",
        "candidate_idx": None,
        "source": "bus_camera",
        "category": "illegal_dumping",
        "description": "Bus camera route 335E flagged construction slag dumped opposite tech park entrance.",
        "location": "ITPL Main Road, Whitefield",
        "lat": 12.9856, "lng": 77.7289,
        "density_score": 79,
        "severity": "high",
        "status": "assigned",
        "img_url": "https://images.unsplash.com/photo-1618477461853-cf6ed80faba5?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 210,
        "events": [
            ("submitted", "Camera telemetry from BMTC route 335E recorded", 210),
            ("assigned", "Forwarded to Mahadevapura ward sanitary inspector", 110)
        ]
    },
    {
        "case_id": "CB-2026-01518",
        "candidate_idx": 6,
        "source": "citizen",
        "category": "roadside_garbage",
        "description": "Dry leaves and discarded packaging piled up near public library compound wall.",
        "location": "11th Main, Jayanagar 4th Block",
        "lat": 12.9250, "lng": 77.5838,
        "density_score": 38,
        "severity": "moderate",
        "status": "resolved",
        "img_url": "https://images.unsplash.com/photo-1503596476-1c12a8ba09a9?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 360,
        "events": [
            ("submitted", "Resident report received", 360),
            ("assigned", "Assigned to South Zone Ward 168 team", 300),
            ("in_progress", "Sweeping and segregated collection started", 180),
            ("resolved", "Footpath fully cleared and sanitized", 60)
        ]
    },
    {
        "case_id": "CB-2026-01524",
        "candidate_idx": 7,
        "source": "citizen",
        "category": "construction_waste",
        "description": "Unattended road cutting debris left on roadside following cable trenching works.",
        "location": "Kaikondrahalli, Sarjapur Road",
        "lat": 12.9145, "lng": 77.6811,
        "density_score": 62,
        "severity": "high",
        "status": "assigned",
        "img_url": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 150,
        "events": [
            ("submitted", "Resident complaint submitted with geolocated photo", 150),
            ("assigned", "Issued notice to road infrastructure maintenance contractor", 95)
        ]
    },
    {
        "case_id": "CB-2026-01530",
        "candidate_idx": 8,
        "source": "citizen",
        "category": "overflowing_bin",
        "description": "Public park perimeter dustbin overflowing with plastic beverage cups and food containers.",
        "location": "BTM Layout 2nd Stage, Outer Ring Road Junction",
        "lat": 12.9166, "lng": 77.6101,
        "density_score": 71,
        "severity": "high",
        "status": "submitted",
        "img_url": "https://images.unsplash.com/photo-1526951521990-620dc14c214b?auto=format&fit=crop&w=800&q=80",
        "minutes_ago": 35,
        "events": [
            ("submitted", "Resident report received", 35)
        ]
    }
]

def download_image(url: str, filename: str) -> bool:
    target_path = UPLOAD_DIR / filename
    if target_path.exists() and target_path.stat().st_size > 1000:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            if len(data) > 500 and data.startswith(b"\xff\xd8\xff"):
                target_path.write_bytes(data)
                return True
    except Exception as e:
        print(f"Warning: failed to download {url}: {e}")
    return False

def seed():
    conn = pymysql.connect(
        host=db_host,
        port=int(db_port),
        user=db_user,
        password=db_pass,
        database=db_name,
        autocommit=True
    )
    cursor = conn.cursor()

    print(f"Connected to MySQL {db_name} on {db_host}:{db_port}")

    # 1. Seed candidate users
    candidate_user_ids = []
    p_hash = hash_password(DEFAULT_PASSWORD)
    
    for c in CANDIDATES:
        cursor.execute("SELECT id FROM users WHERE email = %s", (c["email"],))
        row = cursor.fetchone()
        if row:
            candidate_id = row[0]
            # Update user details if needed
            cursor.execute(
                "UPDATE users SET full_name = %s, phone = %s, is_active = TRUE WHERE id = %s",
                (c["name"], c["phone"], candidate_id)
            )
            print(f"Candidate exists: {c['name']} ({c['email']})")
        else:
            candidate_id = str(uuid4())
            cursor.execute(
                "INSERT INTO users (id, full_name, email, phone, password_hash, role, is_active) VALUES (%s, %s, %s, %s, %s, 'user', TRUE)",
                (candidate_id, c["name"], c["email"], c["phone"], p_hash)
            )
            print(f"Created candidate: {c['name']} ({c['email']})")
        candidate_user_ids.append(candidate_id)

    # 2. Seed Reports and Events
    now = datetime.now(timezone.utc)

    for rep in REPORT_DATA:
        # Determine image filename
        img_filename = f"{rep['case_id'].lower().replace('-', '_')}_evidence.jpg"
        download_success = download_image(rep["img_url"], img_filename)
        evidence_path = f"/uploads/{img_filename}" if download_success else None

        user_id = candidate_user_ids[rep["candidate_idx"]] if rep["candidate_idx"] is not None else None
        created_time = now - timedelta(minutes=rep["minutes_ago"])

        cursor.execute("SELECT id FROM reports WHERE case_id = %s", (rep["case_id"],))
        existing_report = cursor.fetchone()

        if existing_report:
            report_id = existing_report[0]
            cursor.execute(
                """UPDATE reports 
                   SET user_id = %s, source = %s, category = %s, description = %s, location_label = %s,
                       latitude = %s, longitude = %s, evidence_url = %s, density_score = %s,
                       severity = %s, status = %s, updated_at = %s
                   WHERE id = %s""",
                (
                    user_id, rep["source"], rep["category"], rep["description"], rep["location"],
                    rep["lat"], rep["lng"], evidence_path, rep["density_score"],
                    rep["severity"], rep["status"], now, report_id
                )
            )
            print(f"Updated report: {rep['case_id']}")
        else:
            report_id = str(uuid4())
            cursor.execute(
                """INSERT INTO reports 
                   (id, case_id, user_id, source, category, description, location_label, latitude, longitude,
                    evidence_url, density_score, severity, status, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    report_id, rep["case_id"], user_id, rep["source"], rep["category"], rep["description"],
                    rep["location"], rep["lat"], rep["lng"], evidence_path, rep["density_score"],
                    rep["severity"], rep["status"], created_time, created_time
                )
            )
            print(f"Inserted report: {rep['case_id']} ({rep['location']})")

        # Clear and insert report events
        cursor.execute("DELETE FROM report_events WHERE report_id = %s", (report_id,))
        prev_st = None
        for ev_status, ev_note, ev_mins in rep["events"]:
            ev_time = now - timedelta(minutes=ev_mins)
            cursor.execute(
                """INSERT INTO report_events (report_id, previous_status, new_status, note, created_at)
                   VALUES (%s, %s, %s, %s, %s)""",
                (report_id, prev_st, ev_status, ev_note, ev_time)
            )
            prev_st = ev_status

    cursor.close()
    conn.close()
    print("Seed complete! All candidate profiles and reports with evidence images have been created.")

if __name__ == "__main__":
    seed()
