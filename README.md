# Clean Bengaluru

An AI-assisted civic cleanliness platform for Bengaluru. Residents can report roadside waste, bus-mounted cameras can send verified signals, and ward teams can prioritize response using density and severity data.

---

## Repository layout

```text
clean-bengaluru/
├── frontend/   # React 19 + Vite public web app
├── backend/    # FastAPI service (Dual-mode: Memory & MySQL)
├── database/   # MySQL migrations and seed datasets
├── datasets/   # External, raw, and processed datasets
├── docs/       # Architecture and production documentation
├── infra/      # Docker Compose & Nginx configuration
├── scripts/    # Seed and verification utilities
└── storage/    # Uploaded evidence photo storage
```

---

## Quick Start (Clone & Run in 2 minutes)

The platform is designed to work immediately after cloning on any system. You can run it in **Instant Development Mode** (without installing MySQL or Docker) or in **Full MySQL Mode**.

### 1. Prerequisites
- **Node.js**: v18+ (tested on Node 20 / 22 / 24)
- **Python**: v3.10+ (tested on Python 3.12 / 3.14)

---

### 2. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```
The web app will be available at **`http://localhost:5173`**.

---

### 3. Run the Backend API

**On Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**On macOS / Linux (Bash):**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
The API will be available at **`http://localhost:8000`** (Swagger docs at **`http://localhost:8000/docs`**).

> [!NOTE]
> **No MySQL installed?** The backend automatically starts in **Development Memory Store Mode**. All authentication, reporting, and dashboard features work immediately without setting up a database!

---

## Full MySQL Persistence (Optional)

If you have MySQL 8.0+ running locally or in Docker:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env      # macOS/Linux
   Copy-Item .env.example .env  # Windows PowerShell
   ```
2. Set your MySQL connection string in `.env`:
   ```ini
   MYSQL_DATABASE_URL=mysql+pymysql://<user>:<password>@127.0.0.1:3306/clean_bengaluru
   ```
3. Initialize the database schema and sample data:
   ```bash
   # Run the MySQL schema migration
   # (or execute database/mysql/001_auth_and_reports.sql in MySQL Workbench / CLI)

   # Populate candidate residents and sample reports with evidence photos:
   python scripts/seed_candidates_and_reports.py
   ```

---

## Running with Docker Compose

To run the entire production-shaped stack (MySQL 8.4, FastAPI, Nginx Web) in Docker:

```bash
cp .env.example .env
# Edit .env with your deployment values
docker compose --env-file .env -f infra/docker-compose.yml up --build
```
Access the application through the Nginx reverse proxy at **`http://localhost:8080`**.

---

## Ready-to-Use Accounts

When using seeded sample data or local test environments:

| Role | Email | Password | Access |
|---|---|---|---|
| **Resident Portal** | `saksham@example.com` | `StrongPassword123!` | Report creation, timeline tracking |
| **Candidate Resident** | `ananya.rao@example.com` | `Resident@CleanBlr2026` | Resident report view & submission |
| **Ward Operations (Admin)** | `admin@cleanbengaluru.in` | `Admin@CleanBlr2026` | Complaint triage, assignments, status updates |

*(New residents can also register freely on the portal).*

---

## API surface

- `POST /api/v1/auth/register` - create a resident account
- `POST /api/v1/auth/login` - resident login
- `POST /api/v1/auth/admin-login` - administrator login
- `POST /api/v1/auth/logout` - revoke the current session
- `GET /health` and `GET /ready` - liveness and database-readiness probes
- `POST /api/v1/reports` - authenticated report creation with photo evidence
- `GET /api/v1/reports/mine` - authenticated resident report history
- `GET /api/v1/reports` - administrator complaint queue
- `GET /api/v1/reports/{case_id}` - authenticated report details and lifecycle events
- `GET /api/v1/reports/{case_id}/evidence` - secured report image evidence delivery
- `PATCH /api/v1/reports/{case_id}/status` - administrator status progression
- `POST /api/v1/ingest/camera` - keyed bus-camera signal ingestion (`X-Camera-Key`)
