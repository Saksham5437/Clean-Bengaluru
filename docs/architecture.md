# Clean Bengaluru architecture

The repository is deliberately split into deployable concerns:

- `frontend/`: React + Vite public experience and future municipal console.
- `backend/`: FastAPI API, validation, authentication, AI orchestration, and storage adapters.
- `database/`: MySQL schema, migrations, indexes, and demo seed data.
- `datasets/`: external references and locally collected/processed training data. Dataset files do not live inside application source code.
- `infra/`: environment and deployment manifests.
- `scripts/`: repeatable setup and maintenance utilities.

The frontend currently runs against demo dashboard data for public showcase metrics, while authenticated user and admin portals use the API. The API exposes health, hotspots, resident report intake, keyed bus-camera signal ingestion, authentication, evidence delivery, status updates, and report event history. When `MYSQL_DATABASE_URL` is configured, accounts, sessions, reports, and lifecycle events are stored in MySQL; development may fall back to an in-memory store, but `ENVIRONMENT=production` refuses to boot without MySQL.
