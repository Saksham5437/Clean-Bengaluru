# Clean Bengaluru — Release Foundation 0.1.0

## Included

- Premium public Bengaluru cleanliness showcase dashboard.
- Resident registration, login, report submission, private evidence access and report history.
- Admin login, protected complaint queue, sender details, evidence view, status controls and response timeline.
- MySQL schema for users, sessions, reports and lifecycle events.
- Keyed bus-camera signal ingestion through `X-Camera-Key`.
- Scrypt password hashing, expiring bearer sessions, session revocation, role checks and upload validation.
- Liveness/readiness probes, Docker Compose services, Nginx security headers and environment-required deployment secrets.
- Repeatable release checks in `scripts/verify_release.ps1` and MySQL stack checks in `scripts/verify_mysql_stack.ps1`.

## Verification completed

- Backend test suite: 10 passing tests.
- Frontend production build: successful after clean `npm ci`.
- npm audit: no vulnerabilities reported for the locked dependency set.
- Docker Compose manifest: valid with `.env.example`.
- Browser smoke checks: public dashboard, resident registration, report submission, report detail timeline and sign-out.
- Production guard: refuses to boot without `MYSQL_DATABASE_URL`.

## Required deployment gate

Before launch, copy `.env.example` to a deployment-only `.env`, replace every placeholder, start Docker Desktop, and run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/verify_mysql_stack.ps1
```

The final gate passes only when `/ready` reports `database: mysql`. The current development environment does not have an available Docker daemon, so that live MySQL-backed check remains an environment setup step rather than a code defect.
