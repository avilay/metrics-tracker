# Metrics Tracker - Implementation Plan

## Context

Build a mobile-friendly web app for tracking personal metrics over time, inspired by Apple Health. Uses NiceGUI (Python framework on Vue.js/Quasar/Tailwind/FastAPI) with SQLite storage. Multi-user with Firebase auth (anonymous + Google sign-in) since it will be hosted on the public internet. Anonymous users identified by long-lived browser session; users who want multi-device access sign in with Google. Design UX for all metric types holistically; implement one type at a time as vertical slices. Multi-metric overlay analysis is deferred.

---

## Target Project Structure

```
metrics-tracker/
├── main.py                        # Entry point: init_db() + ui.run()
├── app/
│   ├── auth.py                    # Firebase auth middleware + token verification
│   ├── database.py                # SQLite connection, schema DDL
│   ├── models.py                  # Dataclasses: User, MetricDefinition, Entry
│   ├── analytics.py               # Time bucketing + aggregation (numpy)
│   ├── pages/
│   │   ├── login.py               # @ui.page('/login') - Google sign-in option
│   │   ├── dashboard.py           # @ui.page('/')
│   │   ├── add_metric.py          # @ui.page('/metric/new')
│   │   ├── log_entry.py           # @ui.page('/log/{metric_id}')
│   │   └── analyze.py             # @ui.page('/analyze/{metric_id}')
│   ├── components/
│   │   ├── layout.py              # Shared header/nav/drawer shell
│   │   ├── metric_card.py         # Dashboard summary card with sparkline
│   │   └── chart.py               # Reusable ECharts wrapper
│   └── repositories/
│       ├── user_repo.py           # User CRUD
│       └── metric_repo.py         # Metric definitions + entries CRUD
├── design/
│   └── mockups/
│       ├── 01-dashboard/index.html
│       ├── 02-add-metric/index.html
│       ├── 03-log-entry/index.html
│       └── 04-analyze/index.html
└── metrics.db                     # SQLite file (gitignored)
```

---

## Phase 1: UI Mockups

Pure HTML/CSS/JS using Quasar CDN + Tailwind CDN. Dark theme, mobile-first. Each in its own self-contained directory under `design/mockups/`. **Only use UI elements that map directly to NiceGUI components** (which wrap Quasar elements).

### Available NiceGUI elements to use in mockups:
- Layout: `q-header`, `q-drawer`, `q-page`, `q-card`/`q-card-section`, `q-stepper`/`q-step`, `q-tabs`/`q-tab-panels`, `q-separator`, `q-page-sticky`
- Inputs: `q-input`, `q-select`, `q-radio`, `q-toggle`, `q-checkbox`, `q-date`, `q-time`, `q-knob`
- Buttons: `q-btn`, `q-btn-group`, `q-fab`, `q-chip`
- Display: `q-table`, `q-badge`, `q-icon`, `q-spinner`, `q-dialog`, `q-tooltip`, `q-list`/`q-item`
- Charts: Apache ECharts (via CDN — this maps to `ui.echart` in NiceGUI)
- Grid: Quasar's `row`/`col` classes (maps to `ui.row`/`ui.column`/`ui.grid`)

### 1a. Dashboard (`01-dashboard/`)
- `q-header` with app title + user avatar/menu (shows "Sign in with Google" if anonymous)
- `q-drawer` with nav links
- 2-column grid (1-col on mobile) of metric summary cards (`q-card`)
- Each card: metric name, latest value+unit, timestamp, mini ECharts sparkline bar chart, tap opens log entry
- Mock one card per type: Weight (real), Meditate (binary), Mood (categorical), Blood Glucose (conditional properties)
- `q-page-sticky` FAB "+" button for adding new metric

### 1b. Add Metric Definition (`02-add-metric/`)
- `q-stepper` with 3 steps:
  - Step 1: Name (`q-input`) + type selector (`q-radio`: Binary / Real Valued / Categorical / With Properties)
  - Step 2: Type-specific config (conditional panels):
    - Binary: "No additional config needed" message
    - Real Valued: unit `q-input`, default aggregate `q-select`
    - Categorical: dynamic `q-chip` list for allowed values via `q-input` + add button
    - With Properties: sub-type `q-radio` (Cross-Product vs Conditional), then property builder using `q-input` + `q-select` for each property's allowed values
  - Step 3: Review summary + Save `q-btn`

### 1c. Log Entry (`03-log-entry/`)
- `q-dialog` (bottom-sheet position) overlaid on dashboard
- `q-tabs` to switch between metric type demos:
  - Binary: large "Log Now" `q-btn` with timestamp preview
  - Real Valued: `q-input` (type=number) with unit suffix + `q-date`/`q-time` + submit
  - Categorical: `q-radio` group of allowed values + `q-date`/`q-time` + submit
  - Cross-Product: one `q-select` per property + optional number input + datetime + submit
  - Conditional: primary `q-select`, dependent `q-select` appears/hides via v-if + value input + datetime + submit

### 1d. Analyze (`04-analyze/`)
- `q-select` at top to pick metric
- `q-btn-group` time range toggles: D / W / M / 6M / Y
- Filter row (for property metrics): `q-select` (multiple) per property
- Group-by `q-select` + aggregate function `q-select`
- ECharts bar chart (dark theme, teal bars, rounded tops — hardcoded data matching Apple Health style)
- `q-table` below with mock aggregated data rows

---

## Phase 2: Scaffold + Auth + Schema

### SQLite Schema (all tables created upfront)

```sql
users (id, firebase_uid UNIQUE, display_name, email, is_anonymous BOOL, created_at)
metric_definitions (id, user_id, name, metric_type, unit, config JSON, created_at)
  -- metric_type IN ('binary','real_valued','categorical','cross_product','conditional')
  -- config stores type-specific schema (allowed values, properties, etc.)
entries (id, metric_id, user_id, recorded_at, value REAL nullable, created_at)
entry_properties (id, entry_id, property_name, property_value)  -- EAV for property metrics
entry_category (entry_id, value TEXT)  -- for categorical metrics
```

Key design: single polymorphic `entries` table avoids runtime DDL. The `config` JSON column in `metric_definitions` stores type-specific schema. EAV `entry_properties` handles any property combination. Aggregation done in Python with numpy (acceptable at personal-tracker scale).

### Auth: Firebase Anonymous + Google Sign-In

**How it works:**
1. Firebase JS SDK loaded on every page via `ui.add_head_html()`
2. On first visit, client-side JS calls `signInAnonymously()` → gets ID token
3. Client POSTs token to FastAPI endpoint `POST /auth/firebase-token`
4. Server verifies with `firebase_admin.auth.verify_id_token(token)`, creates/finds user in SQLite
5. Stores `firebase_uid` + `user_id` in `app.storage.user`
6. All subsequent page loads check `app.storage.user` in middleware

**Anonymous → Google upgrade:**
- Dashboard header shows "Sign in with Google" button for anonymous users
- Clicking triggers `linkWithPopup(auth.currentUser, GoogleAuthProvider)` client-side
- Firebase preserves the same UID — all data stays linked
- New ID token sent to server, updates `users.is_anonymous = false`, adds email/display_name

**Dependencies:** `firebase-admin` (Python, server-side verification)

**Files:**
- `app/auth.py`: `FirebaseAuthMiddleware` (Starlette BaseHTTPMiddleware), `POST /auth/firebase-token` endpoint, `verify_and_upsert_user()` function
- `app/pages/login.py`: Minimal page shown only if JS is disabled or token exchange fails — has "Sign in with Google" button
- `app/components/layout.py`: Injects Firebase JS SDK, handles auto-anonymous-sign-in on page load

---

## Phase 3: Real Valued Metrics (first vertical slice)

- Add Metric page: name + unit + default aggregate
- Log Entry dialog: `ui.number` + `ui.date`/`ui.time` inputs
- Dashboard card: latest value + unit + mini `ui.echart` sparkline
- Analyze page: time range `ui.button_group`, aggregate `ui.select`, `ui.echart` bar chart + `ui.table`
- `analytics.py`: `bucket_by_period()` and `aggregate_real_valued()` using numpy

## Phase 4: Binary Metrics
- Log: just a "Log Now" button (timestamp only)
- Card: "3x this week" count display
- Analyze: count-only aggregate

## Phase 5: Categorical Metrics
- Add Metric: dynamic chip list for allowed values
- Log: radio group of allowed values
- Card: latest value display
- Analyze: grouped/stacked bars per category value

## Phase 6: Cross-Product Property Metrics
- Add Metric: property builder (name + allowed values per property)
- Log: one dropdown per property + optional value input
- Analyze: filter by property values, group by any property

## Phase 7: Conditional Property Metrics
- Add Metric: conditional property builder (parent property + visibility rules)
- Log: reactive form—dependent properties show/hide based on primary value
- Analyze: dynamic filter UI adjusts based on primary property selection

## Phase 8: Polish
- Input validation, error handling, 404 page
- Mobile optimization (test at 375px)
- Security: `storage_secret` from env var, Firebase config from env vars
- `.gitignore`: add `metrics.db`, `.nicegui/`

---

## Verification

- **Mockups**: Open each `index.html` in a browser, verify responsiveness at 375px and 1440px
- **Auth**: Visit as anonymous → verify auto-sign-in → upgrade to Google → verify data persists
- **Each metric type**: Define metric → log 5+ entries → view on dashboard → analyze with different time ranges and aggregates
- **Mobile**: Test all flows on a phone-width browser window
