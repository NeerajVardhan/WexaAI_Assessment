# WexaAI Analytics Platform — Architecture & Component Reference

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [Technology Stack](#2-technology-stack)
3. [System Architecture](#3-system-architecture)
4. [Backend — Core Concepts](#4-backend--core-concepts)
   - 4.1 [Multi-tenancy Model](#41-multi-tenancy-model)
   - 4.2 [Authentication & Security](#42-authentication--security)
   - 4.3 [Role-Based Access Control](#43-role-based-access-control)
   - 4.4 [Data Models](#44-data-models)
5. [Backend — Feature Modules](#5-backend--feature-modules)
   - 5.1 [Event Ingestion](#51-event-ingestion)
   - 5.2 [Dashboards & Queries](#52-dashboards--queries)
   - 5.3 [Alert Rules](#53-alert-rules)
   - 5.4 [Scheduled Reports](#54-scheduled-reports)
   - 5.5 [Real-time WebSocket Streams](#55-real-time-websocket-streams)
6. [Background Task System](#6-background-task-system)
7. [API Design](#7-api-design)
8. [Database Migrations](#8-database-migrations)
9. [Frontend Architecture](#9-frontend-architecture)
   - 9.1 [Application Shell & Navigation](#91-application-shell--navigation)
   - 9.2 [State Management](#92-state-management)
   - 9.3 [Data Fetching Layer](#93-data-fetching-layer)
   - 9.4 [Pages](#94-pages)
   - 9.5 [Shared Components](#95-shared-components)
10. [Data Flow — End to End](#10-data-flow--end-to-end)

---

## 1. Platform Overview

WexaAI Analytics is a **multi-tenant, real-time analytics platform**. It allows organisations to:

- **Ingest** arbitrary events from any source via REST API, batch upload, CSV, or webhook
- **Visualise** ingested data through live dashboards with area, bar, and pie charts
- **Alert** on metric thresholds (event count, unique users, error rate) with email and webhook notifications
- **Report** on a recurring cron schedule, generating PDF or CSV artifacts emailed to recipients
- **Collaborate** across a team using role-based access control

The platform exposes a documented REST API (Swagger UI at `/docs`, ReDoc at `/redoc`) and a GraphQL endpoint alongside a Next.js web interface.

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| **Backend framework** | FastAPI (async, Python 3.13) |
| **ORM** | SQLAlchemy 2.0 (async) with `asyncpg` driver |
| **Database** | PostgreSQL |
| **Migrations** | Alembic |
| **Task queue** | Celery with Redis broker + Celery Beat scheduler |
| **Real-time** | FastAPI WebSockets |
| **Auth tokens** | JWT (HS256) via `python-jose` + bcrypt password hashing |
| **API validation** | Pydantic v2 + pydantic-settings |
| **Rate limiting** | `slowapi` |
| **Email** | `aiosmtplib` + Jinja2 templates |
| **PDF generation** | `fpdf2` |
| **HTTP client** | `httpx` (for outbound webhooks) |
| **GraphQL** | Strawberry |
| **Observability** | OpenTelemetry (optional), structlog |
| **Frontend framework** | Next.js 16 (App Router, TypeScript) |
| **Styling** | Tailwind CSS |
| **Server state** | TanStack Query (React Query) |
| **Client state** | Zustand with `persist` middleware |
| **Charts** | Recharts |
| **Icons** | Lucide React |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (port 3000)                   │
│   Next.js App Router  ·  Zustand  ·  React Query        │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP/WS  (port 8001)
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI Application                     │
│  /api/v1/auth      /api/v1/ingest    /api/v1/dashboards │
│  /api/v1/alerts    /api/v1/reports   /api/v1/admin      │
│  /api/v1/ws/*      /artifacts (static)   /docs          │
└────────┬──────────────────────────────────┬─────────────┘
         │ asyncpg                           │ Redis
┌────────▼───────────┐           ┌──────────▼──────────────┐
│    PostgreSQL       │           │   Celery Workers         │
│  (all persistent   │           │  + Celery Beat           │
│   data)            │           │  (background tasks)      │
└────────────────────┘           └─────────────────────────┘
```

The frontend communicates with the backend exclusively through versioned REST endpoints (`/api/v1/...`) and two WebSocket paths. The backend holds a single PostgreSQL database; all tables are organisation-scoped. Celery workers run alongside the API server, consuming tasks from a Redis queue (falls back to in-memory for local development).

---

## 4. Backend — Core Concepts

### 4.1 Multi-tenancy Model

Every resource in the database carries an `organization_id` foreign key. All service layer queries include `WHERE organization_id = :org_id` so that tenants are strictly isolated at the data layer — not just at the API layer.

The `Organization` table stores the tenant's name, a unique URL slug, a configurable `retention_days` value, and a `feature_flags` JSON column for per-tenant feature gates.

### 4.2 Authentication & Security

**JWT access tokens** are short-lived (15 minutes by default). They encode `sub` (user ID), `org` (organisation ID), and `role`. They are verified on every protected request via the `current_user` dependency in `app/api/deps.py`.

**Refresh tokens** are long-lived (30 days) and stored as a bcrypt hash in the `refresh_tokens` table. The raw token is sent to the browser as an HTTP-only cookie. On expiry, the client calls `POST /auth/refresh` to receive a new access token without re-entering credentials.

**API keys** are used for machine-to-machine event ingestion. The raw key (prefix `wx_live_…`) is shown to the user once. Only an HMAC-SHA256 hash (keyed on the application `SECRET_KEY`) is persisted in the `api_keys` table. Incoming `X-Api-Key` headers are hashed and compared with constant-time equality.

**Password hashing** uses bcrypt via `passlib`.

```
Login flow
──────────
User → POST /auth/login
     → verify password (bcrypt)
     → issue short-lived access_token (JWT, 15 min)
     → set refresh_token cookie (HTTP-only, 30 days)
     → client stores access_token in Zustand + localStorage

Token refresh
─────────────
POST /auth/refresh  (cookie sent automatically)
  → validate refresh_token hash in DB
  → issue new access_token
```

### 4.3 Role-Based Access Control

Four roles are defined in `app/core/permissions.py`, ordered by privilege:

| Role | Level | Capabilities |
|---|---|---|
| `owner` | 4 | All actions including admin endpoints |
| `admin` | 3 | All actions except some owner-only admin |
| `analyst` | 2 | Read + write dashboards, alerts, reports |
| `viewer` | 1 | Read-only access |

The `require_role(Role.X)` dependency factory is used on routes that need a minimum role. It calls `assert_role()` which compares the integer level from `ROLE_ORDER` and raises `PermissionDenied` if the user's role is insufficient.

### 4.4 Data Models

All models live in `app/models.py` and inherit from `TimestampMixin` (which adds `created_at` / `updated_at`) and SQLAlchemy's declarative `Base`.

**Core entities and their relationships:**

```
Organization
  ├── User (1:many)          — team members with roles
  ├── Invite (1:many)        — pending invitations
  ├── ApiKey (1:many)        — ingestion credentials
  ├── Event (1:many)         — raw event records
  ├── DataSource (1:many)    — named event sources
  ├── Dashboard (1:many)     — visualisation containers
  │     └── Widget (1:many)  — individual chart panels
  ├── SavedQuery (1:many)    — reusable metric queries
  ├── AlertRule (1:many)     — threshold alert definitions
  │     └── AlertEvent (1:many) — evaluation history
  ├── Notification (1:many)  — in-app notification inbox
  ├── ReportSchedule (1:many)— cron-triggered report jobs
  │     └── ReportRun (1:many)  — execution history + artifact URL
  ├── WebhookSubscription    — outbound event webhooks
  └── WebhookDelivery        — delivery attempt log
```

**Event model (central entity):**

```python
class Event:
    id                # UUID primary key
    organization_id   # tenant isolation
    event_type        # e.g. "page_view", "click", "error"
    user_external_id  # caller's user identifier (optional)
    occurred_at       # event timestamp (indexed)
    received_at       # server receipt timestamp
    properties        # JSON blob of arbitrary key-value pairs
    processed         # boolean flag set by Celery worker
    source_id         # optional FK to DataSource
    api_key_id        # which key was used to ingest
```

A composite index on `(organization_id, event_type, occurred_at)` ensures efficient time-range queries scoped per tenant.

---

## 5. Backend — Feature Modules

The service layer (`app/services.py`) contains one class per domain. Route handlers in `app/api/v1/routes/` are thin — they validate input via Pydantic schemas, call a service method, and return the serialised result.

### 5.1 Event Ingestion

**Routes:** `app/api/v1/routes/ingestion.py`  
**Service:** `IngestionService`

Four ingestion paths are supported:

| Endpoint | Auth | Use case |
|---|---|---|
| `POST /ingest/event` | API key | Single event, real-time |
| `POST /ingest/batch` | API key | Array of events, bulk |
| `POST /ingest/csv` | API key | CSV file upload |
| `POST /ingest/webhook/{source}` | API key | Webhook receiver |

All paths normalise the incoming data into `Event` rows. After committing, the service dispatches a `process_events` Celery task to mark records as processed asynchronously and broadcasts a `event.ingested` WebSocket message to connected clients.

Rate limiting is applied at the route level via `slowapi` — by default 200 requests per minute per API key.

### 5.2 Dashboards & Queries

**Routes:** `app/api/v1/routes/dashboards.py`  
**Service:** `DashboardService`

A `Dashboard` is a named container owned by an organisation. It holds a list of `Widget` records (each with type, time_range, and layout position). Dashboards can be public (shareable via a token) or team-only.

**Live metric endpoints** (used by the overview page):

- `GET /dashboards/metrics` — returns `events_today`, `active_users`, `error_rate_pct`, and day-over-day percentage changes
- `GET /dashboards/sources` — returns event share by source, used for pie and bar charts
- `GET /dashboards/queries/run?hours=24` — returns hourly time-series data for the area chart, using PostgreSQL's `date_trunc('hour', occurred_at)` aggregation

**Templates** — three pre-built dashboard templates can be instantiated via `POST /dashboards/templates/{key}`:
- `web_analytics` — page views, event types, source mix
- `sales` — revenue, funnel, signups
- `devops` — errors, latency, system health

### 5.3 Alert Rules

**Routes:** `app/api/v1/routes/alerts.py`  
**Service:** `AlertService`

An `AlertRule` defines a threshold condition evaluated against a metric over a sliding time window.

**Configurable fields:**

| Field | Description |
|---|---|
| `metric` | What to measure: `event_count`, `unique_users`, or `error_rate` |
| `event_type` | Optional filter — only count events of this type |
| `operator` | Comparison: `>`, `>=`, `<`, `<=`, `==` |
| `threshold` | Numeric value to compare against |
| `window_seconds` | How far back to look (minimum 60s) |
| `channels` | Notification delivery: `in_app`, `email`, `webhook` |
| `email_recipients` | List of email addresses |
| `webhook_url` | URL to POST the alert payload to |

**Evaluation logic (`AlertService.evaluate`):**

1. Compute `window_start = now - window_seconds`
2. Run the appropriate SQL aggregate query filtered to the window and optional event type:
   - `event_count` → `COUNT(*)`
   - `unique_users` → `COUNT(DISTINCT user_external_id)`
   - `error_rate` → `(error events / total events) × 100`
3. Apply the comparison operator against the threshold
4. Set rule status to `triggered` or `resolved`
5. Create an `AlertEvent` record for history
6. If triggered, fan out notifications: in-app `Notification` row, async email via `aiosmtplib`, or HTTP POST via `httpx` to the webhook URL

Rules can be **muted** for a specified number of minutes (stored as `muted_until` timestamp). Muted rules are skipped by the Celery Beat evaluator.

### 5.4 Scheduled Reports

**Routes:** `app/api/v1/routes/reports.py`  
**Service:** `ReportService`

A `ReportSchedule` defines a named, recurring report job with a cron expression, output format, and recipient list.

**Run flow (`ReportService.run_now`):**

1. Create a `ReportRun` record with status `running`
2. Query the database for summary metrics: total events, unique users, events in last 24h
3. Generate the artifact file:
   - **PDF** — uses `fpdf2` to render a formatted table of metrics, saved to `report_artifacts/`
   - **CSV** — writes a two-column `Metric,Value` file to `report_artifacts/`
4. Store the full artifact URL (`http://host/artifacts/{filename}`) on the `ReportRun` record
5. If `recipients` is non-empty, send the artifact URL via `aiosmtplib`
6. Update `ReportRun.status` to `completed` (or `failed` on error)

Generated files are served as static files by FastAPI at the `/artifacts/` path, making the download link in the UI directly accessible from the browser.

### 5.5 Real-time WebSocket Streams

**Routes:** `app/api/v1/routes/realtime.py`

Two WebSocket endpoints are exposed:

| Path | Purpose |
|---|---|
| `/api/v1/ws/events/{org_id}` | Broadcasts `event.ingested` when new events arrive |
| `/api/v1/ws/notifications/{org_id}` | Broadcasts alert trigger notifications |

The frontend `useWebSocket` hook connects to the appropriate path on mount, automatically reconnects every 3 seconds on disconnect, and invalidates the relevant React Query cache when a message arrives — keeping all live data current without full-page refreshes.

---

## 6. Background Task System

**Files:** `app/tasks/celery_app.py`, `app/tasks/jobs.py`

Celery workers run independently of the API server. Celery Beat (the built-in scheduler) triggers periodic jobs defined in `celery_app.py`.

| Task | Schedule | Purpose |
|---|---|---|
| `process_events` | On demand (triggered by ingestion) | Marks newly ingested events as `processed` |
| `evaluate_due_alerts` | Every 60 seconds | Evaluates all non-muted alert rules across all orgs |
| `run_scheduled_reports` | Every 60 minutes | Runs all active report schedules |
| `dispatch_pending_webhooks` | Every 30 seconds | Retries pending outbound webhook deliveries |
| `apply_retention` | Daily | Deletes events older than each org's `retention_days` setting |

**Reliability features:**
- All tasks use `bind=True` to access retry context
- Exponential backoff (`retry_backoff=True`) on `process_events` and `dispatch_pending_webhooks`
- Webhook delivery tracks attempts (up to 5); moves to `dead` status after exhausting retries
- `task_acks_late = True` and `task_reject_on_worker_lost = True` prevent silent task loss
- `worker_prefetch_multiplier = 1` ensures fair task distribution

---

## 7. API Design

The API follows REST conventions under `/api/v1/`. All request and response bodies are JSON. Pydantic v2 schemas in `app/schemas.py` define validation rules and serialisation.

**Authentication headers:**
- Protected endpoints: `Authorization: Bearer <access_token>`
- Ingestion endpoints: `X-Api-Key: wx_live_<token>`

**Error response shape** (registered via `register_exception_handlers`):
```json
{
  "error": {
    "code": "authentication_failed",
    "message": "Invalid bearer token"
  }
}
```

**Interactive documentation** is available at:
- Swagger UI: `http://localhost:8001/docs`
- ReDoc: `http://localhost:8001/redoc`

The Swagger UI is configured with `persistAuthorization: true` so a token entered once persists across page reloads during a session.

A **GraphQL endpoint** is available at `/graphql` (enabled by `ENABLE_GRAPHQL=true`), implemented with Strawberry and mirroring the REST data model.

---

## 8. Database Migrations

Alembic manages schema evolution through versioned migration scripts in `backend/alembic/versions/`.

| Migration | Change |
|---|---|
| `0001_initial` | Creates all tables via `Base.metadata.create_all` |
| `0002_alert_rule_channels` | Adds `email_recipients` and `webhook_url` to `alert_rules` (idempotent `ADD COLUMN IF NOT EXISTS`) |
| `0003_report_dashboard_nullable` | Makes `report_schedules.dashboard_id` nullable |
| `0004_alert_rule_metric` | Adds `metric` (default `event_count`) and `event_type` columns to `alert_rules` |

All migrations are applied with `alembic upgrade head` before starting the server.

---

## 9. Frontend Architecture

The frontend is a Next.js 16 application using the App Router. All pages are client components (`"use client"`) with data fetched at runtime via React Query rather than at build time.

### 9.1 Application Shell & Navigation

`components/app-shell.tsx` renders the persistent layout: a fixed left sidebar (hidden on mobile) with navigation links, a sticky top header with a search bar and quick-access icon buttons (overview, API keys), and a `<main>` content area. Every page is wrapped in `<AppShell>`.

### 9.2 State Management

**`lib/store.ts`** — Zustand store, persisted to `localStorage` under the key `wexa-auth`:

```typescript
{
  accessToken: string | undefined   // JWT, set after login
  organizationId: string            // current org ID
  setAccessToken(token)
  setOrganizationId(id)
  clear()                           // called on logout
}
```

All pages read `accessToken` from this store and redirect to `/login` if it is absent.

**`components/providers.tsx`** — wraps the application in a `QueryClientProvider` with shared defaults (`staleTime: 30s`, `retry: 2`).

### 9.3 Data Fetching Layer

`lib/api.ts` exports one typed function per backend endpoint. All functions call `apiFetch<T>`, which:
1. Attaches `Authorization: Bearer <token>` or `X-Api-Key` headers
2. Throws a descriptive `Error` on non-2xx responses (error `detail` from the JSON body is included)
3. Returns the parsed JSON typed as `T`

`lib/types.ts` defines TypeScript types for all API shapes (mirroring Pydantic schemas).

`hooks/useWebSocket.ts` manages a single WebSocket connection per path. It stores the socket in a `useRef`, sets `connected` state on open/close, and schedules a reconnect via `setTimeout` on disconnect. The `onMessage` callback is kept in a ref to avoid stale closures.

### 9.4 Pages

| Page | Route | Key behaviour |
|---|---|---|
| **Login** | `/login` | JWT login form, stores token in Zustand, redirects to `/` |
| **Signup** | `/signup` | Creates org + owner user, logs in immediately |
| **Overview** | `/` | Live metric cards, event volume area chart, source charts, live event table |
| **Ingestion** | `/ingestion` | API key management (create/revoke), CSV upload, recent events |
| **Alerts** | `/alerts` | Alert rule CRUD with metric/operator/threshold/channel config, evaluate/mute actions |
| **Reports** | `/reports` | Report schedule CRUD, run-now trigger, expandable run history with download link |
| **Settings** | `/settings` | Account info, role reference, links to API docs |

All data-fetching pages use `useQuery` with a `refetchInterval` (30–60s) so data stays fresh without user interaction. Mutations use `useMutation` with `onSuccess` calling `qc.invalidateQueries` to refresh the relevant list.

### 9.5 Shared Components

| Component | Purpose |
|---|---|
| `MetricCard` | Displays a single KPI value with a labelled percentage change and colour tone |
| `EventVolumeChart` | Full-width area chart of hourly event counts (24h), with fullscreen toggle |
| `SourceMixChart` | Donut pie chart of traffic share by source, with legend |
| `TopSourcesChart` | Horizontal bar chart of top sources, colour-coded |
| `EventTable` | Live event stream table with WebSocket-driven updates and connection indicator |
| `StatusPill` | Colour-coded badge for alert status (`active`, `triggered`, `resolved`, `muted`) |
| `AppShell` | Full-page layout wrapper with sidebar, header, navigation |

---

## 10. Data Flow — End to End

The following traces a single event from ingestion to dashboard display:

```
1. SDK / Client
   POST /api/v1/ingest/event
   Headers: X-Api-Key: wx_live_...
   Body: { event_type, user_external_id, properties }

2. Backend — Ingestion route
   ├── Validate API key (HMAC hash lookup)
   ├── Create Event row in PostgreSQL
   ├── Dispatch process_events Celery task
   └── Broadcast "event.ingested" via WebSocket

3. Celery Worker
   └── Mark event as processed = true

4. Frontend — EventTable (useWebSocket)
   ├── Receives "event.ingested" message
   └── Calls qc.invalidateQueries(["live-events"])
       → React Query re-fetches GET /ingest/events
       → Table re-renders with new row

5. Frontend — Overview metrics (60s polling)
   GET /api/v1/dashboards/metrics
   → events_today increments
   → MetricCard re-renders with updated count

6. Celery Beat — evaluate_due_alerts (every 60s)
   ├── For each AlertRule:
   │   ├── COUNT events in window matching metric/event_type
   │   ├── Compare against threshold
   │   ├── If triggered → create AlertEvent, send email/webhook
   │   └── Update rule.status
```

This same event is also captured by the daily `apply_retention` task, which deletes it when its `occurred_at` is older than the organisation's configured retention period.
