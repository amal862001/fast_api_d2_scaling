# NYC 311 API Platform — Project Tracker
**Project:** Gov-Tech SaaS Platform on NYC 311 Complaint Data  
**Client:** NYC DoITT (Department of Information Technology & Telecommunications)  
**Stack:** FastAPI · PostgreSQL · SQLAlchemy · Alembic · JWT  
**Timeline:** 5-Day Capstone  

---

## Day 1 — Foundation, Data Pipeline & Auth ✅

### 1. Data Extraction
- [x] Pulled 500,000 rows from NYC 311 Socrata API using Python
- [x] Saved raw data to `nyc_311_requests.csv`
- [x] Used pagination with chunk size of 50,000 rows per request

### 2. Data Exploration
- [x] Loaded CSV into pandas dataframe with `low_memory=False`
- [x] Selected 16 relevant columns from the full dataset
- [x] Checked row count — 500,000 rows confirmed
- [x] Identified nullable vs non-nullable columns
- [x] Ran null count analysis across all 16 columns
- [x] Checked for invalid ZIP codes (`'N/A'`, `'00000'`, empty strings)
- [x] Checked borough unique values — found 6 including `'Unspecified'`
- [x] Checked date range of `created_date` — 2020 to 2024

### 3. Data Cleaning
- [x] Replaced `'Unspecified'` borough → `NaN`
- [x] Replaced empty string borough → `NaN`
- [x] Normalized borough to UPPERCASE
- [x] Dropped 5,937 rows with NULL borough
- [x] Coerced `created_date`, `closed_date`, `resolution_action_updated_date` → `datetime64[us]`
- [x] Coerced `latitude`, `longitude` → `float64`
- [x] Fixed `incident_zip` from `float64` back to clean 5-digit string
- [x] Normalized `city` casing using `.str.title()`
- [x] Final clean row count: **494,063 rows**

### 4. Data Quality Findings
- [x] Documented all findings in `data_notes.md`

| Column | Null Count | Percentage |
|---|---|---|
| `closed_date` | 4,872 | 0.99% |
| `descriptor` | 7,009 | 1.42% |
| `location_type` | 132,541 | 26.83% |
| `incident_zip` | 8,924 | 1.81% |
| `city` | 26,356 | 5.33% |
| `resolution_description` | 50,161 | 10.15% |
| `latitude` | 11,442 | 2.32% |
| `longitude` | 11,442 | 2.32% |
| `resolution_action_updated_date` | 3,047 | 0.62% |

### 5. Database Setup
- [x] Created PostgreSQL database `nyc_311`
- [x] Created `nyc_311_service_requests` table manually with SQL
- [x] Applied `autoincrement` on `unique_key` column
- [x] Bulk inserted 494,063 rows via SQLAlchemy in chunks of 10,000
- [x] Verified row count in PostgreSQL

### 6. Project Structure
- [x] Scaffolded FastAPI project with organized folders

```
nyc311/
├── main.py
├── config.py
├── database.py
├── dependencies.py
├── models/
│   ├── user.py
│   └── complaint.py
├── routers/
│   ├── auth.py
│   └── complaints.py
├── schemas/
│   ├── auth_schema.py
│   └── complaint_schema.py
├── services/
│   └── auth_service.py
├── migrations/
├── etl/
│   ├── extract.py
│   └── seed_users.py
└── .env
```

### 7. Configuration
- [x] Created `.env` file with database credentials and secret key
- [x] Configured `pydantic-settings` with `SettingsConfigDict`
- [x] Added `.env` to `.gitignore`

**Config fields:**
```
DATABASE_URL
SECRET_KEY
SOCRATA_API_URL
DB_USER
DB_PASSWORD
DB_NAME
DB_HOST
DB_PORT
```

### 8. FastAPI App Factory
- [x] Built `main.py` with FastAPI lifespan context
- [x] DB engine initialized on startup with `SELECT 1` health check
- [x] Engine disposed cleanly on shutdown
- [x] Registered auth and complaints routers
- [x] Added health check endpoint `GET /`

### 9. Database Migration — Alembic
- [x] Initialized Alembic with `alembic init migrations`
- [x] Configured `alembic.ini` with PostgreSQL URL
- [x] Updated `migrations/env.py` with `Base.metadata`
- [x] Added `include_object` to prevent Alembic from dropping `nyc_311_service_requests`
- [x] Generated migration — `create platform_users table`
- [x] Ran `alembic upgrade head` — table created successfully

### 10. Platform Users
- [x] Created `PlatformUser` model with fields:
  - `id`, `email`, `hashed_password`, `full_name`, `agency_code`, `role`, `created_at`
- [x] Seeded 10 agency staff accounts

| Agency | Email | Role |
|---|---|---|
| NYPD | james@nypd.nyc.gov | staff |
| DOT | maria@dot.nyc.gov | staff |
| DSNY | david@dsny.nyc.gov | staff |
| DEP | sarah@dep.nyc.gov | staff |
| HPD | michael@hpd.nyc.gov | staff |
| FDNY | emily@fdny.nyc.gov | staff |
| DOB | robert@dob.nyc.gov | staff |
| DHS | lisa@dhs.nyc.gov | staff |
| DPR | kevin@dpr.nyc.gov | staff |
| DOITT | admin@doitt.nyc.gov | admin |

**Default password for all seeded users:** `Password123!`

### 11. JWT Authentication
- [x] Built `auth_service.py` with:
  - `hash_password()` — bcrypt hashing
  - `verify_password()` — bcrypt verification
  - `create_access_token()` — JWT creation
  - `decode_access_token()` — JWT decoding
  - `get_user_by_email()` — DB query
  - `get_user_by_id()` — DB query
  - `create_user()` — register with email uniqueness check
  - `authenticate_user()` — login verification
- [x] JWT payload structure:
```json
{
  "sub": "user_id",
  "agency_code": "NYPD",
  "role": "staff",
  "exp": 1735689600
}
```
- [x] Token expiry: 30 minutes
- [x] Algorithm: HS256

### 12. Auth Endpoints
- [x] `POST /auth/register` — create account with hashed password
- [x] `POST /auth/login` — verify credentials, return JWT (OAuth2PasswordRequestForm)
- [x] `GET /auth/me` — get current logged in user (protected)

### 13. Dependencies
- [x] Built `get_current_user` dependency using `OAuth2PasswordBearer`
- [x] Extracts and validates JWT on every protected request
- [x] Returns `PlatformUser` object to route handlers
- [x] Built `get_db` session dependency in `database.py`

### 14. Complaints CRUD
- [x] Created `Complaint` SQLAlchemy model mapped to `nyc_311_service_requests`
- [x] Built complaint schemas — `ComplaintResponse`, `ComplaintCreate`, `ComplaintUpdate`
- [x] `GET /complaints` — list complaints with filters (agency, borough, status, date range, pagination)
- [x] `GET /complaints/{unique_key}` — get single complaint
- [x] `POST /complaints` — create new complaint (auto fills agency, status, created_date)
- [x] `PATCH /complaints/{unique_key}` — update status and resolution

### 15. Agency Filter
- [x] All complaint queries filtered by `current_user.agency_code`
- [x] NYPD user → only sees NYPD complaints
- [x] DOT user → only sees DOT complaints
- [x] Tested and verified in Swagger UI ✅

---

## API Endpoints Summary

| Method | URL | Purpose | Protected |
|---|---|---|---|
| GET | `/` | Health check | ❌ |
| POST | `/auth/register` | Create account | ❌ |
| POST | `/auth/login` | Login, get JWT | ❌ |
| GET | `/auth/me` | Get current user | ✅ |
| GET | `/complaints` | List complaints (agency filtered) | ✅ |
| GET | `/complaints/{unique_key}` | Get single complaint | ✅ |
| POST | `/complaints` | Create complaint | ✅ |
| PATCH | `/complaints/{unique_key}` | Update complaint | ✅ |

---

## Packages Installed

```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
pydantic-settings
pydantic[email]
pandas
requests
alembic
passlib[bcrypt]
bcrypt==4.0.1
python-jose[cryptography]
email-validator
```

---

## Known Issues & Decisions

| Issue | Decision |
|---|---|
| `bcrypt` version incompatibility with `passlib` | Downgraded to `bcrypt==4.0.1` |
| `nyc_311_service_requests` created manually | Added `include_object` to Alembic to prevent accidental drops |
| `location_type` has 26.83% nulls | Kept as nullable — too high to drop |
| `latitude` null rate lower than expected (2.32% vs ~15%) | Documented in `data_notes.md` |
| ZIP codes auto-converted to `float64` by pandas | Fixed back to clean 5-digit string |

---

## Day 2 — Async DB Layer, Business Logic & Docker 🔄

### 1. Async Engine Setup
- [x] Installed `asyncpg` and `sqlalchemy[asyncio]`
- [x] Updated `database.py` with `create_async_engine`
- [x] Configured connection pool: `pool_size=5`, `max_overflow=10`
- [x] Updated `DATABASE_URL` in `.env` to use `postgresql+asyncpg://`
- [x] Updated `main.py` lifespan to use `async with engine.connect()`
- [x] Updated `get_db()` to `async def` with `AsyncSession`

**Async vs Sync:**

| Day 1 | Day 2 |
|---|---|
| `create_engine` | `create_async_engine` |
| `sessionmaker` | `async_sessionmaker` |
| `Session` | `AsyncSession` |
| `psycopg2` driver | `asyncpg` driver |
| Blocking queries | Non-blocking queries |

### 2. Complaint Model Update
- [x] Added string length limits to all `String` columns
- [x] Added composite index on `(agency, borough, created_date)`
- [x] Created index manually in PostgreSQL (table already existed)

```sql
CREATE INDEX IF NOT EXISTS idx_agency_borough_date
ON nyc_311_service_requests (agency, borough, created_date);
```

### 3. Query Performance — EXPLAIN ANALYZE Results

**Query tested:**
```sql
EXPLAIN ANALYZE
SELECT * FROM nyc_311_service_requests
WHERE agency = 'NYPD'
AND borough = 'BROOKLYN'
AND created_date >= '2024-01-01';
```

**Results:**

| Metric | Before Index | After Index |
|---|---|---|
| Scan type | Sequential Scan | Bitmap Index Scan |
| Execution time | ~3000ms | **1.444ms** |
| Speed improvement | | **~2000x faster** ✅ |

**EXPLAIN ANALYZE output:**
```
Bitmap Heap Scan on nyc_311_service_requests
  Recheck Cond: (agency = 'NYPD' AND borough = 'BROOKLYN' AND created_date >= '2024-01-01')
  Buffers: shared read=3
  → Bitmap Index Scan on idx_agency_borough_date
    Index Searches: 1
Planning Time: 3.037 ms
Execution Time: 1.444 ms ✅
```

**Confirmed indexes on `nyc_311_service_requests`:**

| Index | Purpose |
|---|---|
| `nyc_311_service_requests_pkey` | Primary key on `unique_key` |
| `idx_agency_borough_date` | Composite index for agency queries |

---

## Updated Packages

```
asyncpg
sqlalchemy[asyncio]
```

---

### 3. Repository Pattern
- [x] Created `repositories/complaint_repository.py` with `ComplaintRepository` class
- [x] Implemented `get_by_id(unique_key, agency_code)` — returns single complaint or None
- [x] Implemented `list_paginated(agency_code, borough, complaint_type, status, start_date, end_date, page, limit)`
- [x] Implemented `list_by_agency(agency_code, limit)`
- [x] Implemented `create(agency_code, complaint_type, borough, ...)` — auto sets status/created_date
- [x] Added `get_complaint_repo` dependency to `dependencies.py`
- [x] Changed `scalar_one_or_none()` → `scalars().first()` to handle duplicate keys from bulk insert

**Day 1 vs Day 2 pattern:**

| Day 1 | Day 2 |
|---|---|
| SQL queries inside routes | SQL queries inside repository |
| Sync `db.query()` | Async `await db.execute(select())` |
| Hard to test | Easy to mock and test |
| Mixed concerns | Clean separation of concerns |

### 4. Pydantic Validators
- [x] Added `BoroughEnum` — `MANHATTAN`, `BROOKLYN`, `QUEENS`, `BRONX`, `STATEN ISLAND`
- [x] Added `normalize_borough` validator — handles any casing, maps `THE BRONX` → `BRONX`, `SI` → `STATEN ISLAND`
- [x] Added `normalize_zip` validator — returns `None` for `N/A`, `00000`, empty, non 5-digit values
- [x] Both validators use `mode="before"` — run before Pydantic type checks
- [x] Created `ComplaintSummary` schema (8 fields — list view)
- [x] Created `ComplaintDetail` schema (16 fields — full record)

### 5. Updated Routes
- [x] All routes converted to `async def`
- [x] All routes use repository instead of direct DB queries
- [x] `GET /complaints` — pagination via `page` param instead of `offset`
- [x] `PATCH /complaints/{id}/status` — renamed and improved
- [x] `auth_service.py` fully converted to async
- [x] `routers/auth.py` fully converted to async

### 6. Analytics Endpoints
- [x] Added `get_complaint_types()` to repository — distinct types per agency
- [x] Added `get_borough_stats()` to repository — count/open/closed per borough
- [x] Created `routers/analytics.py`
- [x] `GET /complaint-types` — returns all distinct complaint types for agency
- [x] `GET /boroughs/stats` — returns breakdown by borough with open/closed counts
- [x] Registered analytics router in `main.py`

### 7. Background Audit Logging
- [x] Created `models/audit_log.py` — `AuditLog` model with `user_id`, `agency_code`, `endpoint`, `query_params` (JSON), `result_count`, `timestamp`
- [x] Created `services/audit_service.py` — `write_audit_log()` with try/except so logging never breaks main request
- [x] Added `BackgroundTasks` to `GET /complaints` route
- [x] Fixed datetime timezone mismatch — using `datetime.now().replace(tzinfo=None)` throughout
- [x] Ran Alembic migration — `create audit_logs table`

### 8. Global Exception Handler
- [x] Created `exceptions.py` with `register_exception_handlers(app)`
- [x] `RequestValidationError` handler — returns validation details + `request_id` + `timestamp`
- [x] `SQLAlchemyError` handler — hides DB details, returns clean error message
- [x] `Exception` catch-all handler — returns `error`, `request_id`, `timestamp`
- [x] Every error response includes `uuid4()` request ID for traceability
- [x] Registered in `main.py`

### 9. Docker
- [x] Created multi-stage `Dockerfile` — builder + runtime stages
- [x] Created `docker-compose.yml` — `app` + `db` services
- [x] PostgreSQL health check — app waits until DB is ready before starting
- [x] Created `startup.sh` — runs `alembic upgrade head` then starts uvicorn
- [x] Created `.dockerignore` — excludes venv, pycache, CSV files, .env
- [x] Fixed `DATABASE_URL` — `localhost` → `db` for Docker networking
- [x] `uploads/` volume mounted for file persistence across restarts
- [x] Verified full stack running in Docker ✅

### 10. File Upload Endpoints
- [x] Created `models/attachment.py` — `Attachment` model
- [x] Ran Alembic migration — `create complaint_attachments table`
- [x] Created `routers/attachments.py`
- [x] `POST /complaints/{id}/attachments` — upload JPEG, PNG, or PDF (max 5MB)
- [x] `GET /complaints/{id}/attachments` — list all attachments for complaint
- [x] `GET /attachments/{id}/download` — stream file back with `FileResponse`
- [x] UUID filename generation — prevents collisions on disk
- [x] Agency-scoped — users can only access attachments for their own agency
- [x] Fixed session bug — using `repo.db` consistently instead of separate `db` injection
- [x] Verified rows appear in `complaint_attachments` table in Docker PostgreSQL ✅

---

## API Endpoints — Day 2 Complete

| Method | URL | Purpose | Protected |
|---|---|---|---|
| GET | `/` | Health check | ❌ |
| POST | `/auth/register` | Create account | ❌ |
| POST | `/auth/login` | Login, get JWT | ❌ |
| GET | `/auth/me` | Get current user | ✅ |
| GET | `/complaints` | List complaints (paginated, filtered) | ✅ |
| GET | `/complaints/{id}` | Get single complaint | ✅ |
| POST | `/complaints` | Create complaint | ✅ |
| PATCH | `/complaints/{id}/status` | Update status + resolution | ✅ |
| GET | `/complaint-types` | Distinct complaint types | ✅ |
| GET | `/boroughs/stats` | Borough breakdown | ✅ |
| POST | `/complaints/{id}/attachments` | Upload file | ✅ |
| GET | `/complaints/{id}/attachments` | List attachments | ✅ |
| GET | `/attachments/{id}/download` | Download file | ✅ |

## Updated Project Structure

```
nyc311/
├── main.py
├── config.py
├── database.py
├── dependencies.py
├── exceptions.py
├── startup.sh
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── models/
│   ├── user.py
│   ├── complaint.py
│   ├── audit_log.py
│   └── attachment.py
├── repositories/
│   └── complaint_repository.py
├── routers/
│   ├── auth.py
│   ├── complaints.py
│   ├── analytics.py
│   └── attachments.py
├── schemas/
│   ├── auth_schema.py
│   └── complaint_schema.py
├── services/
│   ├── auth_service.py
│   └── audit_service.py
├── migrations/
├── uploads/
└── etl/
    ├── extract.py
    └── seed_users.py
```

## Updated Packages

```
asyncpg
sqlalchemy[asyncio]
```

## Known Issues & Decisions — Day 2

| Issue | Decision |
|---|---|
| Duplicate `unique_key` values from bulk insert | Changed `scalar_one_or_none()` → `scalars().first()` |
| `TIMESTAMP WITHOUT TIME ZONE` mismatch | Using `datetime.now().replace(tzinfo=None)` throughout |
| Docker `localhost` vs `db` hostname | Updated `.env` DATABASE_URL to use `db` for Docker |
| Two separate `db` sessions in attachment route | Unified to use `repo.db` consistently |
| Duplicate Operation ID warning in Swagger | Minor warning — does not affect functionality |

---

