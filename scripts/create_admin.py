"""Create one controlled administrator account in MySQL.

Usage:
  MYSQL_DATABASE_URL=mysql+pymysql://... python scripts/create_admin.py
The password is requested interactively and is never written to the repository.
"""
import getpass
import hashlib
import secrets
import os
from uuid import uuid4
from sqlalchemy import create_engine, text

url = os.getenv("MYSQL_DATABASE_URL")
if not url:
    raise SystemExit("MYSQL_DATABASE_URL is required")
email = input("Admin email: ").strip().lower()
name = input("Admin full name: ").strip()
password = getpass.getpass("Admin password (12+ characters): ")
if len(password) < 12:
    raise SystemExit("Use an admin password with at least 12 characters")
salt = secrets.token_bytes(16)
digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
password_hash = f"scrypt$16384$8$1${salt.hex()}${digest.hex()}"
engine = create_engine(url)
with engine.begin() as conn:
    conn.execute(text("INSERT INTO users (id, full_name, email, password_hash, role) VALUES (:id, :name, :email, :password_hash, 'admin')"), {"id": str(uuid4()), "name": name, "email": email, "password_hash": password_hash})
print(f"Created administrator: {email}")
