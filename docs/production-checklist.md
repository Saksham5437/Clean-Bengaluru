# Production release checklist

## Required before launch

- Start MySQL 8+, apply `database/mysql/001_auth_and_reports.sql`, and set `MYSQL_DATABASE_URL`.
- Set `CORS_ORIGINS` to the exact production frontend origin.
- Create the first administrator with `scripts/create_admin.py`.
- Move evidence storage from local disk to private object storage with signed URLs.
- Put the API behind HTTPS and a reverse proxy with request-size limits.
- Preserve the security headers in `infra/nginx.conf` and serve the production origin over HTTPS.
- Use `/health` for liveness and `/ready` for MySQL-backed readiness; the API container healthcheck uses `/ready`.
- Add a managed email/SMS provider only after its credentials are stored in the deployment secret manager.
- Run a privacy review for camera footage, faces, number plates, retention, and ward access.
- The production startup check already refuses to boot without MySQL when `ENVIRONMENT=production`; keep that setting enabled in deployment.
- Set a high-entropy `CAMERA_INGEST_KEY` before connecting any bus-mounted camera gateway.
- Copy `.env.example` to a deployment-only `.env`, replace every placeholder, and pass it with `docker compose --env-file .env`; Compose intentionally refuses to start when required secrets are missing.

## Included in this release foundation

- Separate React frontend, FastAPI backend, MySQL schema, dataset workspace, and infrastructure folders.
- Scrypt password hashing, bearer sessions with expiry, role checks, upload type and size validation, CORS configuration, and audit-ready status transitions.
- User-owned report retrieval and admin report queue/status endpoints.
- Keyed camera-signal ingestion and `report_events` status history for traceable complaint lifecycle updates.

## Repeatable verification

From the repository root, run `powershell -ExecutionPolicy Bypass -File scripts/verify_release.ps1`. This runs the backend tests, creates the frontend production bundle, and validates the Compose manifest without deleting or resetting any data. Once Docker is available, start the stack separately and verify `/ready` against the configured MySQL service.

With a deployment `.env` configured, run `powershell -ExecutionPolicy Bypass -File scripts/verify_mysql_stack.ps1`. It starts the stack, waits for the API to report `database: mysql`, and prints the service state if readiness fails.
