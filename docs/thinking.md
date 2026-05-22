# Implementation Notes

This file records the implementation approach and tradeoffs. It is a concise engineering rationale, not private scratch reasoning.

## Build Order

1. Required backend foundation
   - Created the FastAPI app, configuration, database session, SQLAlchemy models, auth/security helpers, exception handling, and route structure.
   - Implemented the must-have modules first: authentication, organization isolation, role guards, API keys, event ingestion, saved queries, dashboards, and widgets.

2. Required frontend foundation
   - Built the Next.js App Router project around the actual analytics workspace as the first screen.
   - Added dashboard, ingestion, alert, report, and settings views with compact SaaS-style layouts.

3. Should-have modules
   - Added alert rules, alert evaluation, alert history, mute support, notification records, report schedules, report runs, and WebSocket endpoints.
   - Added Celery worker and beat tasks for event processing, alert evaluation, scheduled report generation, and retention checks.

4. Optional modules
   - Added GraphQL, OpenTelemetry toggle, SQL sandbox endpoint, data retention settings, webhook delivery logs/retry endpoints, feature flag controls, CI workflow, and Locust load test.

## Architecture Choices

- Monorepo structure keeps the assessment easy to review while separating frontend and backend concerns.
- FastAPI dependencies hold the auth, role, and API key guards so permissions are enforced at route boundaries.
- Services own business workflows and keep route handlers thin.
- SQLAlchemy models use explicit `organization_id` columns and indexed time-series fields to support tenant isolation and analytics queries.
- The SQL sandbox requires callers to bind `:organization_id` so custom queries cannot casually omit tenant context.
- Celery tasks are isolated under `backend/app/tasks` so the API can enqueue heavy or scheduled work without coupling endpoint logic to workers.
- The frontend uses a dashboard-first interface because the assessment describes an operational analytics product, not a marketing website.
- The frontend is on Next.js 16 and React 19 to clear current Next.js and ESLint audit advisories while still satisfying the assessment's Next.js 14+/React 18+ requirement.

## Completion Notes

- Must-have components are implemented as working code paths.
- Should-have components are implemented with practical API and UI coverage.
- Bonus components are included as extension-ready surfaces.
- Production deployments should replace local secrets, wire real SMTP/webhook providers, and configure managed Postgres/Redis.
