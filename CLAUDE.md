# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

On-call shift scheduler for Japanese hospitals. FastAPI backend + React 18 SPA frontend, using `jpholiday` for Japanese holiday detection and pandas for data processing.

## Commands

### Backend

```bash
# Create venv and install dependencies
uv venv -p 3.11
source .venv/bin/activate
uv pip install -r requirements.txt

# Run development server
uvicorn oncall_app.oncall_app:app --reload
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # Vite dev server (port 5173, proxies /api to :8000)
npm run build     # Build to oncall_app/static/ for production
```

### Tests

```bash
pytest tests/ -v              # All 33 tests
pytest tests/test_scheduler.py -v   # Unit tests only (21 tests)
pytest tests/test_api.py -v         # Integration tests only (12 tests)
```

Tests require `pytest` and `httpx` (`uv pip install pytest httpx`).

## Architecture

### Request Flow (Production)

```
Browser → FastAPI (port 8000)
  ├── /api/*  → routes.py (API handlers)
  └── /*      → serves oncall_app/static/index.html (React SPA)
```

### Request Flow (Development)

```
Browser → Vite (port 5173)
  ├── /api/*  → proxied to FastAPI (port 8000)
  └── /*      → Vite dev server (React SPA)
```

### Backend (`oncall_app/`)

- **`oncall_app.py`** — FastAPI app init; mounts `StaticFiles` from `static/`; catch-all route serves `index.html` for SPA routing
- **`routes.py`** — Three endpoints: `POST /api/calendar` (returns doctor list + week layout), `POST /api/schedule` (runs scheduler, stores CSV in temp file, returns token), `GET /csv?tok=` (streams stored CSV)
- **`scheduler.py`** — Core scheduling logic: `generate_shift_slots()` builds date/shift grid; `make_schedule()` randomly assigns doctors with gap constraints (min days between same-doctor shifts); `ok_gap()` validates gap constraint
- **`holiday_utils.py`** — Wraps `jpholiday` to detect Japanese public holidays

### Frontend (`frontend/src/`)

- **`App.jsx`** — React Router setup with three routes: `/`, `/calendar`, `/schedule`
- **`pages/IndexPage.jsx`** — Landing page with navigation
- **`pages/CalendarPage.jsx`** — Calls `POST /api/calendar`, displays shift calendar
- **`pages/SchedulePage.jsx`** — Calls `POST /api/schedule`, displays generated schedule, links to CSV download

### Frontend Build

Vite builds to `oncall_app/static/`. The `vite.config.js` sets `build.outDir: '../oncall_app/static'`. After `npm run build`, the FastAPI server serves the compiled assets directly.
