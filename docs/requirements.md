# Requirements

Source: `C:\Users\345982\Downloads\AI_Engineer_Assessment_.pdf`

## Project Brief

Build a production-ready real-time analytics and reporting SaaS platform. Organizations must be able to ingest data from multiple sources, visualize metrics through customizable dashboards, configure alerts, and generate scheduled reports.

## Must-Have Components

1. Authentication and multi-tenancy
   - Email/password signup and signin.
   - Organization creation during signup.
   - JWT access tokens and refresh-token cookie flow.
   - Owner, Admin, Analyst, Viewer role hierarchy.
   - Permission guards on API endpoints.
   - Organization-level data isolation at the query layer.
   - Invite-based team onboarding.

2. Data ingestion
   - Single-event and batch REST ingestion.
   - CSV uploads.
   - Webhook receiver endpoints.
   - Pydantic validation for event schemas.
   - Async processing through Celery and Redis.
   - API key generation, rotation, and revocation.
   - Rate-limit-ready API key and organization context.

3. Dashboards and widgets
   - Custom dashboards.
   - Widget types for line, bar, pie, KPI, and table views.
   - Saved queries.
   - Configurable time ranges.
   - Team and public sharing modes.
   - Configurable auto-refresh.

## Should-Have Components

1. Alerts and notifications
   - Threshold-based alert rules.
   - Scheduled alert evaluation.
   - In-app, email, and webhook notification channels.
   - Alert history.
   - Mute/snooze support.
   - Active, triggered, resolved, and muted statuses.

2. Scheduled reports
   - Daily, weekly, and monthly dashboard report schedules.
   - PDF/PNG artifact metadata.
   - Email recipients.
   - Background report run support.
   - Report history and archive.

3. Real-time features
   - WebSocket live dashboard/event updates.
   - Real-time alert notification channel.
   - Live event stream viewer.
   - Connection state and reconnect-ready client architecture.

## Technical Specifications

- Frontend: Next.js 14 App Router, React 18, TypeScript.
- State: Zustand or Redux Toolkit.
- Styling: Tailwind CSS or Shadcn/UI.
- Charts: Recharts, Chart.js, or D3.js.
- Data fetching: TanStack Query.
- Backend: FastAPI preferred, Python 3.11+, type hints.
- Database: PostgreSQL with SQLAlchemy 2.0 async.
- Migrations: Alembic.
- Task queue: Celery + Redis, with Celery Beat.
- Caching/rate limiting: Redis-ready.
- Validation: Pydantic v2.
- Testing: pytest, pytest-asyncio, httpx.

## Architecture Expectations

- Clean layered architecture: routers, services, repositories, models.
- Dependency injection through FastAPI dependencies.
- Async endpoints and async database access.
- Centralized error handling and structured error responses.
- Structured logging.
- ORM-backed SQL injection prevention.
- Database indexes for time-series queries.
- Background processing with retry/backoff extension points.
- Health checks and observability hooks.

## Deliverables

- Clean GitHub repository structure.
- README with setup instructions, architecture overview, and environment variables.
- Deployable demo structure for frontend, backend, workers, Postgres, and Redis.

## Bonus Components

- GraphQL API alongside REST.
- OpenTelemetry instrumentation.
- Custom SQL query sandbox with query-plan output.
- Data retention policy support.
- Webhook delivery retry system and delivery logs.
- CI/CD pipeline.
- Load testing with Locust.
- Feature flags for gradual rollouts.

