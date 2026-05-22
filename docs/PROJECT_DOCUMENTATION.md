# WexaAI — Complete Project Documentation

## Overview

**WexaAI** is a production-ready, multi-tenant SaaS analytics and reporting platform. Organizations use it to ingest events from multiple sources, visualize metrics through customizable dashboards, configure threshold-based alerts, and generate scheduled reports. The architecture follows a clean monorepo layout with a FastAPI backend and a Next.js frontend, backed by PostgreSQL and Redis, all orchestrated via Docker Compose.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.12, SQLAlchemy 2.0 (async), Alembic, Pydantic v2 |
| Task Queue | Celery + Redis |
| Database | PostgreSQL 16 |
| Cache / Broker | Redis 7 |
| Frontend | Next.js 16 (App Router), React 19, TypeScript |
| State Management | Zustand |
| Data Fetching | TanStack Query |
| Charts | Recharts |
| Styling | Tailwind CSS |
| Infrastructure | Docker, docker-compose |
| CI/CD | GitHub Actions |

---

## Repository Structure

```
WexaAI/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app factory & middleware
│   │   ├── models.py                # SQLAlchemy ORM models
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── services.py              # Business logic layer
│   │   ├── repositories.py          # Generic repository pattern (DB access)
│   │   ├── graphql.py               # Strawberry GraphQL schema (optional)
│   │   ├── seed.py                  # Demo data seeding
│   │   ├── core/
│   │   │   ├── config.py            # Settings loaded from env vars
│   │   │   ├── database.py          # AsyncSession setup, engine
│   │   │   ├── security.py          # JWT, bcrypt, HMAC key handling
│   │   │   ├── permissions.py       # Role enum (OWNER/ADMIN/ANALYST/VIEWER)
│   │   │   ├── exceptions.py        # Custom error classes
│   │   │   └── logging.py           # Structured JSON logging (structlog)
│   │   ├── api/
│   │   │   ├── deps.py              # FastAPI dependencies (auth, rate limiting)
│   │   │   └── v1/
│   │   │       ├── router.py        # Aggregates all routers
│   │   │       └── routes/
│   │   │           ├── auth.py
│   │   │           ├── api_keys.py
│   │   │           ├── ingestion.py
│   │   │           ├── dashboards.py
│   │   │           ├── alerts.py
│   │   │           ├── reports.py
│   │   │           ├── admin.py
│   │   │           ├── realtime.py  # WebSocket endpoints
│   │   │           └── health.py
│   │   └── tasks/
│   │       ├── celery_app.py        # Celery + Beat config
│   │       └── jobs.py              # Async background tasks
│   ├── alembic/                     # Database migration scripts
│   └── tests/                       # Unit tests (security, permissions)
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # Overview/dashboard page
│   │   ├── ingestion/page.tsx       # Event ingestion page
│   │   ├── alerts/page.tsx          # Alerts management page
│   │   ├── reports/page.tsx         # Reports page
│   │   └── settings/page.tsx        # Org settings page
│   ├── components/
│   │   ├── app-shell.tsx            # Main layout (sidebar + header)
│   │   ├── metric-card.tsx          # KPI card component
│   │   ├── event-table.tsx          # Recent events table
│   │   ├── event-volume-chart.tsx   # Area chart (hourly events)
│   │   ├── source-charts.tsx        # Pie + Bar charts (source mix)
│   │   └── status-pill.tsx          # Status badge (triggered/active/etc.)
│   └── lib/
│       ├── api.ts                   # apiFetch wrapper + WebSocket URL builder
│       ├── store.ts                 # Zustand global state
│       ├── types.ts                 # TypeScript type definitions
│       └── mock-data.ts             # Demo data for all pages
├── docs/                            # Project documentation
├── docker-compose.yml
└── README.md
```

---

## Backend Architecture

### Entry Point — `app/main.py`

Creates the FastAPI application, registers CORS middleware, mounts all API routers under `/api/v1`, and optionally enables the GraphQL endpoint (`/graphql`) and OpenTelemetry instrumentation based on environment flags.

---

### Database Models — `app/models.py`

Every model includes an `organization_id` foreign key for strict tenant isolation. All queries in the service layer are scoped to the calling user's organization.

| Model | Purpose | Key Fields |
|---|---|---|
| `Organization` | Root tenant entity | `name`, `slug` (unique), `retention_days`, `feature_flags` (JSONB) |
| `User` | Team member | `organization_id`, `email`, `role`, `is_active`, `last_login_at` |
| `Invite` | Team onboarding token | `organization_id`, `email`, `role`, `token_hash`, `expires_at`, `accepted_at` |
| `RefreshToken` | Session persistence | `user_id`, `token_hash`, `expires_at`, `revoked_at` |
| `ApiKey` | Programmatic ingestion auth | `organization_id`, `name`, `prefix`, `key_hash`, `scopes`, `last_used_at`, `revoked_at` |
| `DataSource` | Tracks event origins | `organization_id`, `name`, `type` (e.g., "api"), `config` |
| `Event` | Core data record | `organization_id`, `event_type`, `user_external_id`, `occurred_at`, `received_at`, `properties` (JSONB), `processed` |
| `SavedQuery` | Reusable analytics query | `organization_id`, `metric`, `event_type`, `aggregation`, `time_bucket`, `filters` |
| `Dashboard` | Visualization container | `organization_id`, `owner_id`, `visibility` (team/public), `public_token`, `auto_refresh_seconds` |
| `Widget` | Chart on a dashboard | `organization_id`, `dashboard_id`, `saved_query_id`, `title`, `type` (line/bar/pie/kpi/table), `layout`, `options` |
| `AlertRule` | Threshold monitor | `organization_id`, `saved_query_id`, `operator`, `threshold`, `window_seconds`, `channels`, `status`, `muted_until` |
| `AlertEvent` | Alert fire history | `organization_id`, `alert_rule_id`, `status`, `value`, `message` |
| `Notification` | In-app / email / webhook message | `organization_id`, `user_id`, `channel`, `title`, `body`, `delivered_at` |
| `ReportSchedule` | Cron-triggered export | `organization_id`, `dashboard_id`, `cron`, `recipients`, `format` (pdf/png), `is_active` |
| `ReportRun` | Execution record | `organization_id`, `schedule_id`, `status`, `artifact_url`, `error`, `started_at`, `completed_at` |
| `WebhookDelivery` | Outbound webhook tracking | `organization_id`, `target_url`, `event_type`, `payload`, `status`, `attempts`, `next_attempt_at` |

**Indexing:** The `Event` table has compound indexes on `(organization_id, event_type, occurred_at)` and `(organization_id, received_at)` to accelerate analytics queries.

---

### Core Utilities — `app/core/`

**`config.py`** — Pydantic `Settings` class that reads all configuration from environment variables (`DATABASE_URL`, `SECRET_KEY`, `CELERY_BROKER_URL`, etc.).

**`database.py`** — Creates an async SQLAlchemy engine using the AsyncPG driver. Provides `AsyncSession` as a FastAPI dependency with `pre_ping` pool health checks.

**`security.py`** — Three responsibilities:
- **JWT**: `create_access_token()` generates HS256 tokens with 15-minute expiry (`sub` = user_id, `org` = org_id, `role`).
- **Passwords**: bcrypt hashing via `passlib`.
- **API Keys**: HMAC-SHA256 hashing; only the prefix is stored in plaintext for UI display.

**`permissions.py`** — Defines a `Role` enum with hierarchy: `OWNER > ADMIN > ANALYST > VIEWER`. Used by the `require_role(minimum)` dependency.

**`exceptions.py`** — Custom exception classes that map to HTTP error responses.

**`logging.py`** — Structured JSON logging via `structlog` for observability and log aggregation.

---

### API Dependencies — `app/api/deps.py`

FastAPI injectable dependencies used across all routes:

| Dependency | Purpose |
|---|---|
| `current_user()` | Decodes Bearer JWT, loads the active `User` from DB |
| `require_role(minimum)` | Asserts `user.role >= minimum`; returns 403 otherwise |
| `current_api_key()` | Extracts and validates `X-API-Key` header against hashed keys in DB |
| `rate_limited_api_key()` | In-memory token bucket: 600 requests/minute per API key |

---

### Services Layer — `app/services.py`

All business logic lives here. Routes call services; services call the ORM.

**`AuthService`**
- `signup(org_name, email, password)` — Creates `Organization` + owner `User`, issues refresh token
- `login(email, password)` — Validates credentials, updates `last_login_at`, returns token pair
- `refresh(token)` — Validates refresh token hash, returns new access token
- `create_invite(org_id, email, role)` — Generates 7-day invite token (hashed)
- `accept_invite(token, name, password)` — Creates `User` with invite's role, marks invite accepted
- `access_token_for(user)` — Generates JWT

**`ApiKeyService`**
- `create(org_id, name, scopes)` — Generates key, stores HMAC hash + prefix, returns raw key once
- `list(org_id)` — List all org keys
- `revoke(org_id, key_id)` — Marks key revoked
- `rotate(org_id, key_id)` — Revokes old key, creates new key with same config
- `authenticate(raw_key)` — Hash lookup to load and validate a key

**`IngestionService`**
- `ingest_one(org_id, event_in)` — Creates a single `Event` record
- `ingest_batch(org_id, events)` — Bulk creates event records
- `ingest_csv(org_id, file)` — Parses uploaded CSV, maps columns to event fields
- `list_recent(org_id, limit)` — Returns last N events
- `mark_processed(event_ids)` — Bulk-flips `processed=True` (called post-Celery task)

**`DashboardService`**
- `create_dashboard(org_id, user_id, data)` — Creates `Dashboard`, optionally sets public token
- `list_dashboards(org_id)` — Lists all org dashboards
- `get_by_public_token(token)` — Unauthenticated access to shared dashboards
- `add_widget(org_id, dashboard_id, data)` — Creates `Widget` linked to a `SavedQuery`
- `create_saved_query(org_id, data)` — Saves a reusable analytics query definition
- `list_saved_queries(org_id)` — Lists all saved queries
- `run_query(org_id, query_id)` — Executes query: `COUNT(Event)`, `MIN/MAX(occurred_at)` grouped by org; returns `{series: [{bucket, value}]}`

**`AlertService`**
- `create(org_id, data)` — Creates `AlertRule`
- `list(org_id)` — Lists all alert rules
- `evaluate(org_id, rule_id)` — Counts events in `window_seconds`, compares against `threshold` using `operator`; creates `AlertEvent`; if triggered and `"in_app"` in channels, creates `Notification`
- `mute(org_id, rule_id, minutes)` — Sets `status="muted"` and `muted_until = now + minutes`
- `history(org_id, rule_id)` — Returns past `AlertEvent` records

**`ReportService`**
- `create(org_id, data)` — Creates `ReportSchedule`
- `list(org_id)` — Lists schedules
- `run_now(org_id, schedule_id)` — Creates `ReportRun` with `artifact_url` pointing to `/reports/{id}/{date}.{format}`; updates `last_run_at`
- `runs(org_id, schedule_id)` — Returns execution history

**`AdminService`**
- `update_feature_flags(org_id, flags)` — Merges flag dict into `org.feature_flags`
- `update_retention(org_id, days)` — Sets `org.retention_days`
- `run_sql_sandbox(org_id, sql)` — Executes user-submitted SQL with safety guards: SELECT-only parser check, must include `:organization_id` binding, returns EXPLAIN + results
- `list_webhook_deliveries(org_id)` — Lists delivery records
- `create_webhook_delivery(org_id, data)` — Schedules outbound webhook
- `retry_delivery(org_id, delivery_id)` — Resets status + increments attempt counter

---

### API Routes — `app/api/v1/routes/`

**`auth.py`** — `/api/v1/auth/`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/signup` | None | Register org + owner user, get token pair |
| POST | `/login` | None | Email/password login |
| POST | `/refresh` | Cookie | Refresh access token using HTTP-only cookie |
| POST | `/logout` | Bearer | Revoke refresh token |
| GET | `/me` | Bearer | Get current user profile |
| POST | `/invites` | ADMIN+ | Create team invite |
| POST | `/invites/accept` | None | Accept invite, create user account |

**`api_keys.py`** — `/api/v1/api-keys/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | Bearer | List org API keys |
| POST | `/` | ADMIN+ | Create new API key (raw key returned once) |
| POST | `/{id}/revoke` | ADMIN+ | Revoke a key |
| POST | `/{id}/rotate` | ADMIN+ | Replace key with a new one |

**`ingestion.py`** — `/api/v1/ingest/`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/event` | API Key + Rate Limit | Ingest a single event |
| POST | `/batch` | API Key + Rate Limit | Ingest array of events |
| POST | `/csv` | API Key + Rate Limit | Upload CSV file of events |
| POST | `/webhook/{source}` | API Key + Rate Limit | Generic webhook receiver |
| GET | `/events` | Bearer | List last 100 events |

**`dashboards.py`** — `/api/v1/dashboards/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | Bearer | List dashboards |
| POST | `/` | ANALYST+ | Create dashboard |
| GET | `/public/{token}` | None | Public dashboard by share token |
| GET | `/{id}` | Bearer | Get single dashboard |
| POST | `/{id}/widgets` | ANALYST+ | Add widget to dashboard |
| GET | `/queries/saved` | Bearer | List saved queries |
| POST | `/queries/saved` | ANALYST+ | Create saved query |
| GET | `/queries/run` | Bearer | Execute a saved query, get series data |

**`alerts.py`** — `/api/v1/alerts/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | Bearer | List alert rules |
| POST | `/` | ANALYST+ | Create alert rule |
| POST | `/{id}/evaluate` | ANALYST+ | Manually trigger evaluation |
| POST | `/{id}/mute` | ANALYST+ | Mute alert for N minutes |
| GET | `/{id}/history` | Bearer | Alert event history |

**`reports.py`** — `/api/v1/reports/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/` | Bearer | List report schedules |
| POST | `/` | ANALYST+ | Create report schedule |
| POST | `/{id}/run` | ANALYST+ | Trigger report immediately |
| GET | `/{id}/runs` | Bearer | Execution history |

**`admin.py`** — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| PUT | `/feature-flags` | ADMIN+ | Toggle org feature flags |
| PUT | `/retention` | OWNER | Set data retention (days) |
| POST | `/sql-sandbox` | ADMIN+ | Run SELECT query in sandbox |
| GET | `/webhook-deliveries` | ADMIN+ | List outbound webhooks |
| POST | `/webhook-deliveries` | ADMIN+ | Create webhook delivery |
| POST | `/webhook-deliveries/{id}/retry` | ADMIN+ | Retry failed delivery |

**`realtime.py`** — `/api/v1/ws/`

| Protocol | Path | Purpose |
|---|---|---|
| WebSocket | `/events/{organization_id}` | Streams newly ingested events to connected clients |
| WebSocket | `/notifications/{organization_id}` | Streams in-app notifications in real time |

**`health.py`** — `GET /api/v1/health` — Returns `{status, app, environment}` — used by Docker healthchecks.

---

### Background Jobs — `app/tasks/`

**`celery_app.py`** — Configures Celery with Redis as the broker and result backend. Registers Celery Beat periodic schedule:
- `evaluate_due_alerts` — every **60 seconds**
- `run_scheduled_reports` — every **300 seconds**

**`jobs.py`** — Task implementations:

| Task | Trigger | What it does |
|---|---|---|
| `process_events(event_ids)` | On ingest | Marks events `processed=True` |
| `evaluate_due_alerts()` | Every 60s | Loops all non-muted alert rules, calls `AlertService.evaluate()` |
| `run_scheduled_reports()` | Every 300s | Loops active report schedules, calls `ReportService.run_now()` |
| `apply_retention()` | Scheduled stub | Placeholder for deleting events older than `org.retention_days` |

---

## Frontend Architecture

### Pages — `frontend/app/`

**`page.tsx` — Overview**
Executive dashboard. Displays: 4 KPI metric cards, an hourly event volume area chart, a source breakdown (pie + bar charts), and a live recent events table. Uses mock data from `lib/mock-data.ts`.

**`ingestion/page.tsx` — Ingestion**
Demonstrates the three ingestion methods (REST API, batch, CSV upload). Shows API key management table with create/revoke/rotate actions, and displays recent ingested events.

**`alerts/page.tsx` — Alerts**
Table of alert rules showing name, condition (operator + threshold), notification channels, and status (triggered/active/resolved/muted). Includes manual evaluation button and channel health status panel.

**`reports/page.tsx` — Reports**
Grid of report schedules showing name, cron expression, recipients list, format, and last run time. Includes run-now and archive/deactivate actions.

**`settings/page.tsx` — Settings**
Three sections: Role hierarchy explanation (OWNER → ADMIN → ANALYST → VIEWER), tenant guard panel (org ID, retention policy), and feature flag toggle switches.

---

### Components — `frontend/components/`

**`AppShell`** — Root layout wrapper. Left sidebar with navigation links to all pages. Top header with search input, notification bell, and action buttons. Wraps all page content.

**`MetricCard`** — Renders a single KPI. Props: `label`, `value`, `change` (% delta), `tone` (good/warning/danger/neutral). Shows an up/down arrow with appropriate color coding.

**`EventTable`** — Tabular display of recent events. Columns: `event_type`, `user_external_id`, `properties` (formatted JSON), `received_at` (relative time). Handles empty states.

**`EventVolumeChart`** — Recharts `AreaChart` showing hourly event counts as a time series. Responsive container with gradient fill, tooltip, and axis labels.

**`SourceCharts`** — Two charts side by side: a `PieChart` showing the event source mix (API / CSV / Webhook) and a `BarChart` showing conversion funnel metrics.

**`StatusPill`** — Small inline badge. Variants: `triggered` (red), `active` (green), `resolved` (gray), `muted` (amber). Used in alert and report tables.

---

### State Management — `lib/store.ts`

Zustand store with minimal global state:

```typescript
type AppState = {
  accessToken?: string;
  organizationId: string;
  setAccessToken: (token?: string) => void;
  setOrganizationId: (id: string) => void;
};
```

The access token is kept in memory (not localStorage) and passed as a Bearer header on every API call.

---

### API Layer — `lib/api.ts`

**`apiFetch<T>(path, token?, init?)`**
- Prepends `NEXT_PUBLIC_API_URL` to the path
- Sets `Content-Type: application/json`
- Adds `Authorization: Bearer {token}` when a token is present
- Sets `credentials: "include"` so the refresh token cookie is sent automatically
- Throws a typed error on any non-2xx response

**`websocketUrl(path)`**
- Prepends `NEXT_PUBLIC_WS_URL` to construct WebSocket connection URLs

---

### Type Definitions — `lib/types.ts`

```typescript
type RoleName = "owner" | "admin" | "analyst" | "viewer"
type MetricPoint = { bucket: string; value: number }
type EventRecord = { id, event_type, user_external_id?, received_at, properties: Record<string, unknown> }
type AlertRule = { id, name, status, threshold, operator, channels, last_evaluated_at? }
type ReportSchedule = { id, name, cron, format, recipients, is_active, last_run_at? }
type ApiKey = { id, name, prefix, scopes, revoked_at?, last_used_at? }
```

---

### Styling — Tailwind Config

Custom design tokens defined in `tailwind.config.ts`:

| Token | Value | Usage |
|---|---|---|
| `ink` | `#18212f` | Primary text / backgrounds |
| `muted` | `#64748b` | Secondary text |
| `accent` | `#0f766e` (teal) | Primary actions, active states |
| `warning` | `#b45309` (amber) | Muted alerts, caution states |
| `danger` | `#b91c1c` (red) | Triggered alerts, errors |
| `shadow-soft` | `0 8px 20px rgba(15,23,42,0.06)` | Card elevation |

---

## Infrastructure & Deployment

### Docker Compose Services

| Service | Image | Port | Purpose |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Celery broker + result backend |
| `backend` | Custom (Python 3.12) | 8000 | FastAPI + Uvicorn |
| `worker` | Same as backend | — | Celery task worker |
| `beat` | Same as backend | — | Celery Beat periodic scheduler |
| `frontend` | Custom (Node 22-alpine) | 3000 | Next.js production server |

The backend container runs `alembic upgrade head` before starting Uvicorn, ensuring migrations are always applied on startup.

### Environment Variables

**Backend (`.env`):**

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | AsyncPG connection string |
| `SECRET_KEY` | JWT signing secret (min 16 chars) |
| `CELERY_BROKER_URL` | Redis URL for task queue |
| `CELERY_RESULT_BACKEND` | Redis URL for task results |
| `REDIS_URL` | Cache / session store |
| `SMTP_FROM` | Sender address for report emails |
| `WEBHOOK_TIMEOUT_SECONDS` | Default: 8 |
| `ENABLE_GRAPHQL` | Toggle Strawberry GraphQL endpoint |
| `ENABLE_OTEL` | Toggle OpenTelemetry tracing |

**Frontend (`.env`):**

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL (e.g., `http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | WebSocket base URL (e.g., `ws://localhost:8000`) |

---

### CI/CD — GitHub Actions

Triggered on every push to `main` and on all pull requests.

**Backend job:**
1. Set up Python 3.12
2. Install `requirements-dev.txt`
3. Lint with `ruff check app tests`
4. Run `pytest`

**Frontend job:**
1. Set up Node 22 (with npm cache)
2. `npm install`
3. Type-check: `npm run typecheck`
4. Build: `npm run build`

---

## End-to-End Workflows

### 1. User Signup & Authentication

```
Client → POST /auth/signup
  → AuthService.signup()
    → Create Organization (slug from name)
    → Create User (role=OWNER, bcrypt password)
    → Create RefreshToken (HMAC hash, 30d expiry)
    → Returns: { access_token (JWT, 15m), Set-Cookie: refresh_token (HTTP-only, 30d) }

Subsequent requests:
  → Authorization: Bearer {access_token}
  → deps.current_user() decodes JWT → loads User from DB
```

### 2. Event Ingestion

```
SDK / Webhook → POST /ingest/event
  → deps.rate_limited_api_key() checks 600 req/min bucket
  → IngestionService.ingest_one()
    → INSERT INTO events (org_id, event_type, properties, received_at, processed=false)
  → Response: 202 EventRead
  → Celery task queued → process_events([event.id])
    → UPDATE events SET processed=true WHERE id IN (...)
  → WebSocket manager broadcasts event to /ws/events/{org_id}
```

### 3. Dashboard & Query Execution

```
User → POST /dashboards → creates Dashboard record
User → POST /queries/saved → creates SavedQuery (metric, event_type, aggregation, filters)
User → POST /dashboards/{id}/widgets → creates Widget linked to SavedQuery

Frontend chart renders → GET /queries/run?query_id={id}
  → DashboardService.run_query()
    → SELECT COUNT(*), MIN(occurred_at), MAX(occurred_at)
      FROM events WHERE organization_id = :org_id AND event_type = :type
    → Returns: { series: [{ bucket, value }, ...] }
```

### 4. Alert Evaluation (Automated)

```
Every 60 seconds:
  Celery Beat → evaluate_due_alerts task
    → Fetch all AlertRules WHERE status != 'muted'
    → For each rule:
        AlertService.evaluate()
          → COUNT(events) in last window_seconds
          → Compare value {operator} threshold
          → INSERT AlertEvent (status: triggered | resolved, value)
          → If triggered AND 'in_app' in channels:
              INSERT Notification (user_id, channel='in_app', title, body)
              WebSocket broadcast → /ws/notifications/{org_id}
```

### 5. Scheduled Report Generation

```
Every 300 seconds:
  Celery Beat → run_scheduled_reports task
    → Fetch ReportSchedules WHERE is_active = true
    → For each schedule:
        ReportService.run_now()
          → INSERT ReportRun (status='completed', artifact_url, started_at, completed_at)
          → UPDATE ReportSchedule SET last_run_at = now()
```

### 6. Team Onboarding via Invites

```
Admin → POST /auth/invites (email, role)
  → AuthService.create_invite()
    → INSERT Invite (token_hash, expires_at = now+7d)
  → Invite token sent to email (SMTP stub)

New user → POST /auth/invites/accept (token, name, password)
  → AuthService.accept_invite()
    → Validate token_hash + expiry
    → INSERT User (role from invite)
    → Mark invite accepted_at = now()
    → Return TokenPair
```

---

## Security Design

| Concern | Implementation |
|---|---|
| Password storage | bcrypt via `passlib` |
| Access tokens | JWT HS256, 15-minute TTL |
| Refresh tokens | HMAC-SHA256 hash stored; sent as HTTP-only, Secure, SameSite=Lax cookie |
| API keys | Full key HMAC-SHA256 hashed at rest; only prefix stored plaintext |
| Rate limiting | In-memory token bucket, 600 req/min per API key |
| Tenant isolation | Every DB query filtered by `organization_id` |
| SQL sandbox | SELECT-only enforcement; must bind `:organization_id`; runs EXPLAIN |
| Role enforcement | `require_role(minimum)` dependency on every sensitive route |
| CORS | Configured in `main.py` per `config.ALLOWED_ORIGINS` |

---

## Optional / Bonus Features

- **GraphQL API** — Strawberry schema with a `platform_summary` query; toggle via `ENABLE_GRAPHQL`
- **OpenTelemetry** — Instrumentation hooks; toggle via `ENABLE_OTEL`
- **SQL Sandbox** — ADMIN-only, safe ad-hoc analytics against the org's own data
- **Webhook Delivery Tracking** — Full audit trail with retry logic
- **Data Retention Policy** — Per-org `retention_days`; background stub ready for cleanup logic
- **Feature Flags** — Per-org JSONB dict for gradual feature rollouts
- **Load Testing** — `locustfile.py` skeleton included

---

## Demo Credentials

After running `alembic upgrade head` (which also seeds demo data):

| Field | Value |
|---|---|
| Email | `owner@wexa.local` |
| Password | `ChangeMe123!` |

---

## Key File Reference

| Responsibility | File |
|---|---|
| App bootstrap & middleware | `backend/app/main.py` |
| ORM models & indexes | `backend/app/models.py` |
| All business logic | `backend/app/services.py` |
| Auth, JWT, hashing | `backend/app/core/security.py` |
| Role enforcement | `backend/app/core/permissions.py` |
| FastAPI dependencies | `backend/app/api/deps.py` |
| All API routes | `backend/app/api/v1/routes/` |
| Background tasks | `backend/app/tasks/jobs.py` |
| Celery config + beat | `backend/app/tasks/celery_app.py` |
| DB migrations | `backend/alembic/` |
| Frontend layout | `frontend/components/app-shell.tsx` |
| Frontend charts | `frontend/components/event-volume-chart.tsx`, `source-charts.tsx` |
| Frontend global state | `frontend/lib/store.ts` |
| Frontend API client | `frontend/lib/api.ts` |
| Docker orchestration | `docker-compose.yml` |
