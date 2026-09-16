# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 3
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements)
- **Current Task**: Ready to begin Phase 4 (Requirement classification with SHAP explainability)

## What Is Actually Implemented
- Standard project structure (`backend/app/{api,core,models,schemas,services,nlp,ml,utils}`, `frontend/`, `data/`, `docs/`, `docker/`).
- SQLAlchemy database configuration in `backend/app/core/database.py`.
- SQLAlchemy ORM models in `backend/app/models/document.py` (`Document`, `DocumentVersion`, `Requirement`).
- Alembic migration environment (`alembic.ini`, `backend/alembic/env.py`) with initial migration applied to SQLite.
- Pydantic v2 schemas in `backend/app/schemas/` (`DocumentListItem`, `DocumentDetail`, `RequirementResponse`, `DocumentExtractResponse`).
- API routes in `backend/app/api/documents.py`:
  - `POST /api/documents/upload`: Multipart file upload, validation, extraction, cleaning, storage in DB.
  - `GET /api/documents`: List of documents with requirement counts.
  - `GET /api/documents/{id}`: Document detail.
  - `DELETE /api/documents/{id}`: Delete document and cascade.
  - `POST /api/documents/{id}/extract`: Run layered requirement extraction and persist to database.
  - `GET /api/documents/{id}/requirements`: List requirements for a document.
- Mounted routers in `backend/app/main.py`.
- Full test suite: 17 passing tests across extraction, cleaning, requirement extraction, and API integration.

## What Has Actually Been Verified
- All 17 unit and integration tests passing in `backend/tests/` (100% pass rate).
- Live server run and real curl verification against all 6 API endpoints:
  - `POST /api/documents/upload` with `sample_srs.txt`: returned 201 Created (ID 1, status 'uploaded', version 'v1.0').
  - `GET /api/documents`: returned 200 OK with list of 1 document.
  - `GET /api/documents/1`: returned 200 OK with document detail.
  - `POST /api/documents/1/extract`: returned 200 OK, extracted and saved 6 requirements (REQ-001 to REQ-006).
  - `GET /api/documents/1/requirements`: returned 200 OK with all 6 extracted requirement records.
  - `DELETE /api/documents/1`: returned 200 OK and verified subsequent `GET` returned 404 Not Found.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- SQLAlchemy 2.0 with declarative base and simple cascade relationships.
- Alembic handles schema evolution cleanly with versioned migration scripts.
- Idempotent requirement extraction cleans existing requirements before inserting new ones.
- SQLite is default for development via `DATABASE_URL=sqlite:///./srs_guardian.db`.

## Files/Modules Currently Being Worked On
- None (Phase 3 completed).

## Exact Next Step
- Phase 4: Functional / Non-Functional requirement classification with SHAP explainability:
  - Add scikit-learn, shap, joblib, pandas to `requirements.txt`.
  - Obtain confirmation for PROMISE_exp requirements dataset.
  - Train TF-IDF + Logistic Regression pipeline in `backend/app/ml/train_classifier.py`.
  - Build `backend/app/ml/classifier.py` and `backend/app/ml/explain_classifier.py` (SHAP LinearExplainer).
  - Update Requirement model/API.

## Last Verification Performed
- Full pytest test suite (17 passed in 6.62s) on 2026-09-16 15:36:08.
- Live curl HTTP test against all endpoints verified on 2026-09-16 15:36:42.

## Metadata
- **Last Updated**: 2026-09-16 15:37:00
- **Last Commit Hash**: Pending Phase 3 commit
