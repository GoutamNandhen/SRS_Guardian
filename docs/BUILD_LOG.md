# SRS Guardian - Build Log

## Phase 0: Project Setup
- **Date**: 2026-09-16
- **What was built**:
  - Project directory structure matching the architecture specification (`backend/app/`, `frontend/`, `data/`, `docs/`, `docker/`).
  - Backend requirements specification in `backend/requirements.txt` scoped to Phase 1 dependencies.
  - Environment settings in `backend/app/core/config.py` using `pydantic-settings` with `.env.example`.
  - Simple logger setup in `backend/app/core/logging.py`.
  - FastAPI application entrypoint in `backend/app/main.py` with `/health` endpoint.
  - Root `.gitignore` covering Python, Node, `.env`, uploads, models, and cache files.
- **Key decisions**:
  - Kept dependencies minimal (no ML packages added before needed).
  - Used standard logging to stdout without external logging framework overhead.
  - Used SQLite as default database URL in configuration.
- **How to run**:
  - Create virtual environment: `python -m venv .venv`
  - Activate: `.\.venv\Scripts\Activate.ps1`
  - Install dependencies: `pip install -r backend/requirements.txt`
  - Run server: `uvicorn backend.app.main:app --reload --port 8000`
  - Health check: `curl http://127.0.0.1:8000/health`
- **Known limitations**:
  - No database tables, models, or frontend views implemented yet (strictly bounded to Phase 0).
