import io
from uuid import uuid4

from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)

def user_payload(email=None):
    return {"full_name": "Test Resident", "email": email or f"resident-{uuid4().hex[:8]}@example.com", "phone": "+919800000000", "password": "StrongPass123!"}

def register_user():
    response = client.post("/api/v1/auth/register", json=user_payload())
    assert response.status_code == 201
    return response.json()

def test_health_reports_development_database_mode():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_readiness_reports_development_store_when_database_is_not_configured():
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

def test_registration_login_and_password_is_not_returned():
    payload = user_payload()
    registered = client.post("/api/v1/auth/register", json=payload)
    assert registered.status_code == 201
    assert "password" not in registered.text
    login = client.post("/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "user"
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/me", headers=headers).status_code == 401

def test_invalid_credentials_and_protected_route_are_rejected():
    assert client.get("/api/v1/reports/mine").status_code == 401
    payload = user_payload()
    client.post("/api/v1/auth/register", json=payload)
    assert client.post("/api/v1/auth/login", json={"email": payload["email"], "password": "wrong-password"}).status_code == 401

def test_authenticated_user_can_create_and_read_own_report():
    auth = register_user()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    created = client.post("/api/v1/reports", headers=headers, data={"location": "Bellandur service road", "category": "illegal_dumping", "description": "Test evidence"}, files={"photo": ("evidence.jpg", io.BytesIO(b"\xff\xd8\xff\xe0test-jpeg"), "image/jpeg")})
    assert created.status_code == 201
    assert created.json()["case_id"].startswith("CB-")
    assert created.json()["evidence_url"].startswith("/api/v1/reports/")
    evidence = client.get(created.json()["evidence_url"], headers=headers)
    assert evidence.status_code == 200
    mine = client.get("/api/v1/reports/mine", headers=headers)
    assert mine.status_code == 200
    assert any(item["case_id"] == created.json()["case_id"] for item in mine.json()["items"])

def test_invalid_file_type_is_rejected():
    auth = register_user()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    response = client.post("/api/v1/reports", headers=headers, data={"location": "Koramangala", "category": "roadside_garbage"}, files={"photo": ("payload.exe", io.BytesIO(b"not-an-image"), "application/octet-stream")})
    assert response.status_code == 415

def test_fake_image_with_image_content_type_is_rejected():
    auth = register_user()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    response = client.post("/api/v1/reports", headers=headers, data={"location": "Indiranagar", "category": "roadside_garbage"}, files={"photo": ("payload.jpg", io.BytesIO(b"not-an-image"), "image/jpeg")})
    assert response.status_code == 415

def test_report_coordinates_and_blank_fields_are_validated():
    auth = register_user()
    headers = {"Authorization": f"Bearer {auth['access_token']}"}
    invalid_coordinates = client.post("/api/v1/reports", headers=headers, data={"location": "Bellandur", "category": "dumping", "latitude": "91", "longitude": "77"})
    assert invalid_coordinates.status_code == 422
    blank_location = client.post("/api/v1/reports", headers=headers, data={"location": "   ", "category": "dumping"})
    assert blank_location.status_code == 422

def test_admin_can_update_report_status_and_user_cannot():
    resident = register_user()
    resident_headers = {"Authorization": f"Bearer {resident['access_token']}"}
    created = client.post("/api/v1/reports", headers=resident_headers, data={"location": "Adugodi", "category": "overflowing_bin"})
    case_id = created.json()["case_id"]
    assert client.patch(f"/api/v1/reports/{case_id}/status", headers=resident_headers, json={"status": "resolved"}).status_code == 403
    admin = {"id": str(uuid4()), "full_name": "Ward Admin", "email": f"admin-{uuid4().hex[:8]}@example.com", "phone": None, "password_hash": main.hash_password("AdminStrongPass123!"), "role": "admin"}
    main.memory_users[admin["email"]] = admin
    login = client.post("/api/v1/auth/admin-login", json={"email": admin["email"], "password": "AdminStrongPass123!"})
    assert login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    updated = client.patch(f"/api/v1/reports/{case_id}/status", headers=admin_headers, json={"status": "resolved"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "resolved"
    detail = client.get(f"/api/v1/reports/{case_id}", headers=admin_headers)
    assert detail.status_code == 200
    assert [event["new_status"] for event in detail.json()["events"]] == ["submitted", "resolved"]

def test_camera_ingestion_requires_key_and_creates_traceable_report(monkeypatch):
    monkeypatch.setattr(main, "CAMERA_INGEST_KEY", "camera-test-secret")
    payload = {"route_id": "201R", "location": "Outer Ring Road, Bellandur", "category": "roadside_garbage", "density_score": 76, "severity": "high"}
    assert client.post("/api/v1/ingest/camera", json=payload).status_code == 401
    created = client.post("/api/v1/ingest/camera", headers={"X-Camera-Key": "camera-test-secret"}, json=payload)
    assert created.status_code == 201
    case_id = created.json()["case_id"]
    admin = {"id": str(uuid4()), "full_name": "Camera Admin", "email": f"camera-admin-{uuid4().hex[:8]}@example.com", "phone": None, "password_hash": main.hash_password("AdminStrongPass123!"), "role": "admin"}
    main.memory_users[admin["email"]] = admin
    login = client.post("/api/v1/auth/admin-login", json={"email": admin["email"], "password": "AdminStrongPass123!"})
    detail = client.get(f"/api/v1/reports/{case_id}", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert detail.status_code == 200
    assert detail.json()["report"]["source"] == "bus_camera"
    assert detail.json()["events"][0]["new_status"] == "submitted"
