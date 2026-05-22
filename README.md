# WexaAI Analytics Platform

Production-style SaaS analytics and reporting platform for the AI Engineer assessment. The project is structured as a monorepo with a FastAPI backend, a Next.js frontend, async data access, tenant-aware authorization, event ingestion, dashboards, alerts, reports, and real-time APIs.

## Project Layout

- `backend/` - FastAPI API, SQLAlchemy models, services, Celery tasks, Alembic migrations, tests.
- `frontend/` - Next.js 16 App Router UI with dashboard, ingestion, alerts, and reports views.
- `docs/requirements.md` - Extracted assessment requirements grouped by priority.
- `docs/thinking.md` - Implementation approach, architecture choices, and completion notes.
- `docker-compose.yml` - Local Postgres, Redis, backend, Celery worker/beat, and frontend stack.

## Quick Start

1. Copy environment files:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

2. Start infrastructure and apps:

```bash
docker compose up --build
```

3. Open the app:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Backend Local Development

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Run tests:

```bash
pytest
```

## Frontend Local Development

```bash
cd frontend
npm install
npm run dev
```

Run quality checks:

```bash
npm run lint
npm run typecheck
```

## Demo Credentials

Seed scripts create a demo organization and owner account:

- Email: `owner@wexa.local`
- Password: `ChangeMe123!`

## Core Capabilities

- Email/password signup and signin with organization creation.
- JWT access tokens and HTTP-only refresh token cookie support.
- Role hierarchy and permission guards for Owner, Admin, Analyst, and Viewer.
- Tenant-scoped database access through dependency-injected services.
- API key generation, rotation, revocation, and authenticated ingestion.
- Single event, batch event, CSV upload, and webhook ingestion endpoints.
- Async processing hooks through Celery and Redis.
- Dashboards, widgets, saved queries, dashboard sharing, and auto-refresh configuration.
- Threshold alerts with scheduled evaluation, history, mute/snooze, and in-app/email/webhook channels.
- Scheduled report definitions, report runs, generated snapshot metadata, and archive endpoints.
- WebSocket live event and notification channels.

## Optional/Bonus Coverage

The repository includes optional foundations for GraphQL, OpenTelemetry, webhook delivery retries, retention policies, feature flags, CI, and load testing. See `docs/thinking.md` for the exact implemented surface and extension points.
