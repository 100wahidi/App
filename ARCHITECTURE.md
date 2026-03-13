# Project Architecture

## Overview
This project is split into two runtime applications:
- Backend API (FastAPI) for data-quality reporting
- Frontend UI (React + Vite) for file upload and report visualization

All data-quality logic is centralized in predefined checks and reused by the API service layer.

## Directory Structure

```text
Models/
├── backend/
│   └── app/
│       ├── core/
│       │   └── quality_checks.py        # predefined checks (source of truth)
│       ├── models/
│       │   └── api_models.py            # Pydantic request/response models
│       ├── routers/
│       │   └── reporting_routes.py      # REST endpoints
│       ├── services/
│       │   └── reporting_service.py     # orchestration between API and checks
│       └── main.py                       # FastAPI app wiring
├── frontend/
│   ├── src/
│   │   ├── App.tsx                       # reporting screen
│   │   └── main.tsx                      # React entrypoint
│   ├── index.html                        # Vite HTML entry
│   ├── vite.config.ts                    # Vite + API proxy
│   └── package.json
├── data/                                 # input data files
├── scripts.py                            # compatibility export of predefined checks
├── run_server.py                         # root launcher for backend
└── requirements.txt
```

## Runtime Flow
1. Frontend uploads file(s) to `/api/reporting/upload-analyze`.
2. Router delegates to `ReportingService`.
3. Service executes checks from `backend/app/core/quality_checks.py`.
4. Aggregated report is returned to frontend and rendered.

## Start Commands

### Backend
From project root:
- `python run_server.py`

Alternative:
- `uvicorn backend.app.main:app --reload`

### Frontend
From `frontend`:
- `npm run dev`

## Notes
- Keep `quality_checks.py` as the single source for data-quality rules.
- `scripts.py` is kept for compatibility imports and points to the same logic.
