# Metrics Tracker - Implementation Plan

## Context

Build a mobile-friendly web app for tracking personal metrics over time, inspired by Apple Health. Uses NiceGUI (Python framework on Vue.js/Quasar/Tailwind/FastAPI) with SQLite storage. Multi-user with Firebase auth (anonymous + Google sign-in) since it will be hosted on the public internet. Anonymous users identified by long-lived browser session; users who want multi-device access sign in with Google.

Metrics are defined with a unified model: a **value type** (numeric, categorical, or none) plus zero or more **properties** (each numeric or categorical). All combinations are valid. Implementation proceeds in capability slices rather than per-type phases.

---

## Target Project Structure

```
metrics-tracker/
├── main.py                        # Entry point: init_db() + ui.run()
├── app/
│   ├── auth.py                    # Firebase auth middleware + token verification
│   ├── database.py                # SQLite connection, schema DDL
│   ├── models.py                  # Dataclasses: User, MetricDefinition, Entry
│   ├── analytics.py               # load_metrics() + aggregation (pandas)
│   ├── pages/
│   │   ├── login.py               # @ui.page('/login')
│   │   ├── dashboard.py           # @ui.page('/')
│   │   ├── add_metric.py          # @ui.page('/metric/new')
│   │   └── metric_detail.py       # @ui.page('/metric/{metric_id}') - analyze + log
│   ├── components/
│   │   ├── layout.py              # Shared header/nav shell
│   │   ├── metric_card.py         # Dashboard summary card with sparkline
│   │   ├── chart.py               # Reusable ECharts wrapper
│   │   ├── log_modal.py           # Dynamic log entry bottom-sheet modal
│   │   └── filter_controls.py     # Filter/group-by/aggregate controls
│   └── repositories/
│       ├── user_repo.py           # User CRUD
│       └── metric_repo.py         # Metric definitions + entries CRUD
├── design/
│   └── mockups/ui/                # Completed mockups (Phase 1 done)
└── metrics.db                     # SQLite file (gitignored)
```

---

## Phase 1: UI Mockups - DONE

Pure HTML/CSS/JS using Quasar CDN + Tailwind CDN. Dark theme, mobile-first. Each in its own self-contained directory under `design/mockups/ui/`. Only uses UI elements that map directly to NiceGUI components (which wrap Quasar elements).

### Mockup inventory

- `01-dashboard/` — 5 metric cards (Weight, Meditate, Mood, Blood Glucose, Hike)
- `02-add-metric/` — Dynamic form: name, value type selector, unit/labels config, property builder
- `03a-detail-meditate/` — Count chart, time range toggle, log modal (date/time only)
- `03b-detail-weight/` — Bar chart, aggregate selector, numeric log modal
- `03c-detail-mood/` — Stacked bars by category, radio group log modal
- `03d-detail-food/` — Filter/group-by dropdowns, stacked bars, multi-select log modal
- `03e-detail-glucose/` — Filter by Event/Delta, group-by with stacked bars, numeric log
- `03f-detail-hike/` — Numeric filters (min/max), binned grouping, mixed-type log

---

## Phase 2: Scaffold + Auth + Schema

### SQLite Schema (all tables created upfront)

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    firebase_uid TEXT UNIQUE NOT NULL,
    display_name TEXT,
    email TEXT,
    is_anonymous BOOLEAN NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    value_type TEXT NOT NULL CHECK (value_type IN ('numeric', 'categorical', 'none')),
    unit TEXT,
    definition_json TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_id INTEGER NOT NULL,
    recorded_at INTEGER NOT NULL,
    value REAL,
    label TEXT,
    properties_json TEXT,
    FOREIGN KEY (metric_id) REFERENCES metrics(id)
);

CREATE INDEX IF NOT EXISTS idx_logs_metric_id ON logs(metric_id);
CREATE INDEX IF NOT EXISTS idx_logs_recorded_at ON logs(recorded_at);
```

Key design decisions:
- **`metrics.definition_json`**: Stores the full metric schema — allowed labels (for categorical value_type), properties array. Each property has: `{ name, value_type ('numeric'|'categorical'), unit, categories }`.
- **`logs.properties_json`**: Stores all property values as a JSON object (e.g., `{"event": "breakfast", "delta": "one-hour-after"}`). This avoids an EAV table — properties are unpacked into DataFrame columns at query time.
- **`logs.value`**: Populated when metric `value_type = 'numeric'`.
- **`logs.label`**: Populated when metric `value_type = 'categorical'`.
- **`logs.recorded_at`**: Unix timestamp (seconds). Converted to timezone-aware datetime in pandas.
- Aggregation done in Python with pandas (acceptable at personal-tracker scale).

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

## Phase 3: Simple Metrics (no properties)

Covers: Meditate (none), Weight (numeric), Mood (categorical)

- **Add Metric page**: name + value type selector + unit (for numeric) / allowed labels (for categorical)
- **Dashboard card**: renders based on value_type — count for none, latest value+unit for numeric, latest label for categorical; all with mini `ui.echart` sparkline
- **Detail page**: time range `ui.button_group` (D/W/M/6M/Y), aggregate selector (for numeric: sum/avg/median), ECharts bar chart, data table, log modal
- **Log modal**: bottom-sheet dialog with date/time; "Log Now" button for none, `ui.number` + unit for numeric, `ui.radio` group for categorical

### Analytics (`analytics.py`)

Core function: `load_metrics(user_id, metric_name, tz) -> pd.DataFrame`
- Queries `metrics` table for `definition_json`, then `logs` table for entries
- Converts `recorded_at` (unix timestamps) to timezone-aware datetimes via `pd.Series(..., dtype=f"datetime64[s, {tz}]")`
- Adds `value` column as `float64` for numeric, or as `CategoricalDtype` for categorical
- Returns a DataFrame indexed by log id with `recorded_at` + value column(s)

Aggregation patterns:
- **None (Meditate)**: `df.resample("W", on="recorded_at").size()` — returns a Series of counts per period
- **Numeric (Weight)**: `df.resample("W", on="recorded_at").mean()` (or `.median()`, `.sum()`) — returns a DataFrame with aggregated `value` column
- **Categorical (Mood)**: `df.groupby([pd.Grouper(key="recorded_at", freq="W"), "value"]).size()` — returns a Series with MultiIndex (period, category) for stacked bar charts; `.unstack(fill_value=0)` to pivot for charting

---

## Phase 4: Metrics with Categorical Properties

Covers: Food/Meal (none + categorical props), Blood Glucose (numeric + categorical props)

- **Add Metric page**: property builder — add/remove properties, each with name + allowed categories
- **Detail page**: filter `ui.select` (multiple) per categorical property, group-by `ui.select`, stacked bar charts
- **Log modal**: adds `ui.select` per categorical property

### Analytics

`load_metrics()` extended: unpacks `properties_json` into DataFrame columns. Each categorical property becomes a column with `CategoricalDtype(categories=prop["categories"])`.

Filtering: standard pandas boolean indexing on property columns:
```python
# Filter: source == "home-cooked" & taste == "delicious"
filtered = df[(df["source"] == "home-cooked") & (df["taste"] == "delicious")]
```

Grouping by categorical property:
```python
# Group by "healthy" property within time periods
filtered.groupby([pd.Grouper(key="recorded_at", freq="W"), "healthy"]).size()
```

For numeric-valued metrics with categorical properties (Blood Glucose):
```python
# Average glucose grouped by delta, filtered to breakfast events
glucose.loc[glucose["event"] == "breakfast", ["recorded_at", "value", "delta"]].groupby(
    [pd.Grouper(key="recorded_at", freq="W"), "delta"]
).mean()
```

---

## Phase 5: Metrics with Numeric Properties

Covers: Hike (numeric value + mixed numeric/categorical props)

- **Add Metric page**: property builder supports numeric properties (name + unit input)
- **Detail page**: min/max `ui.number` filter inputs for numeric properties, auto-binned grouping
- **Log modal**: adds `ui.number` inputs for numeric properties

### Analytics

`load_metrics()` extended: numeric properties unpacked as `float64` columns.

Filtering numeric properties: standard comparison operators:
```python
# Hikes between 2 and 10 miles
filtered = df[(df["loop_length"] >= 2) & (df["loop_length"] <= 10)]
```

Binning numeric properties for group-by using `pd.cut()`:
```python
# Bin elevation_gain into low/medium/high
df["elevation_gain_bin"] = pd.cut(df["elevation_gain"], bins=3, labels=["low", "medium", "high"])

# Then group and aggregate
df[["recorded_at", "value", "elevation_gain_bin"]].groupby(
    [pd.Grouper(key="recorded_at", freq="W"), "elevation_gain_bin"]
).mean()
```

---

## Phase 6: Polish

- Input validation, error handling, 404 page
- Mobile optimization (test at 375px)
- Security: `storage_secret` from env var, Firebase config from env vars
- `.gitignore`: add `metrics.db`, `.nicegui/`

---

## Verification

- **Mockups**: Open each `design/mockups/ui/*/index.html` in a browser, verify responsiveness at 375px and 1440px
- **Auth**: Visit as anonymous → verify auto-sign-in → upgrade to Google → verify data persists
- **Phase 3**: Define each simple metric type (none/numeric/categorical) → log 5+ entries → view on dashboard → analyze with different time ranges and aggregates
- **Phase 4**: Define metrics with categorical properties → log entries with property values → filter and group-by on detail page
- **Phase 5**: Define metric with numeric properties → log entries → filter by numeric range → verify binned grouping
- **Mobile**: Test all flows on a phone-width browser window
