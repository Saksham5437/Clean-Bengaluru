# Clean Bengaluru

An AI-assisted civic cleanliness platform for Bengaluru. Residents can report roadside waste, bus-mounted cameras can send verified signals, and ward teams can prioritize response using density and severity data.

## Repository layout

```text
clean-bengaluru/
├── frontend/   # React/Vite public web app
├── backend/    # FastAPI service
├── database/   # MySQL migrations and seeds
├── datasets/   # External, raw, and processed datasets
├── docs/       # Architecture and product documentation
├── infra/      # Deployment configuration
└── scripts/    # Repeatable utility scripts
```

Release handoff details are in `docs/release-notes.md`.

## Run the frontend

```powershell
cd frontend
npm install
npm run dev
```

## Run the API

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The dashboard includes clearly labelled showcase data, while authentication and report persistence are implemented behind the separated backend and database layers. AI inference, object storage, and municipal integrations remain deployment integrations rather than hard-coded credentials.

## Authentication and MySQL

The common dashboard is public. User and admin portals are protected by separate login screens. New users are created through `POST /api/v1/auth/register`; passwords are hashed with scrypt before storage. Apply `database/mysql/001_auth_and_reports.sql`, set `MYSQL_DATABASE_URL`, and start the MySQL service from `infra/docker-compose.yml` to persist accounts and sessions. For bus-camera gateways, set a long random `CAMERA_INGEST_KEY` in the deployment secret manager and send it as `X-Camera-Key`.

## Run the production-shaped stack

```powershell
Copy-Item .env.example .env
# Edit .env and replace every placeholder with deployment values.
docker compose --env-file .env -f infra/docker-compose.yml up --build
```

Compose intentionally refuses to start when required deployment variables are missing.

## API surface

- `POST /api/v1/auth/register` - create a resident account
- `POST /api/v1/auth/login` - resident login
- `POST /api/v1/auth/admin-login` - administrator login
- `POST /api/v1/auth/logout` - revoke the current session
- `GET /health` and `GET /ready` - liveness and database-readiness probes
- `POST /api/v1/reports` - authenticated report creation with optional evidence
- `GET /api/v1/reports/mine` - authenticated resident report history
- `GET /api/v1/reports` - administrator complaint queue
- `GET /api/v1/reports/{case_id}` - authenticated report details and lifecycle events
- `PATCH /api/v1/reports/{case_id}/status` - administrator status update
- `POST /api/v1/ingest/camera` - keyed bus-camera signal ingestion (`X-Camera-Key`)
