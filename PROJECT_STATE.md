# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 2
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction)
- **Current Task**: Ready to begin Phase 3 (Database and API for documents and requirements)

## What Is Actually Implemented
- Standard project structure created (`backend/app/{api,core,models,schemas,services,nlp,ml,utils}`, `frontend/`, `data/`, `docs/`, `docker/`).
- Backend dependencies installed in `.venv` (including spaCy and `en_core_web_sm`).
- Configuration module in `backend/app/core/config.py` using `pydantic-settings`.
- Standard logger in `backend/app/core/logging.py`.
- Entrypoint FastAPI application in `backend/app/main.py` with `/health` endpoint.
- File validation utility in `backend/app/utils/file_validation.py`.
- Multi-format text extraction in `backend/app/nlp/extractors.py` for PDF, DOCX, and TXT.
- Text cleaning module in `backend/app/nlp/cleaning.py`.
- Layered requirement extraction engine in `backend/app/nlp/requirement_extractor.py`:
  - Layer 1: Explicit ID pattern detection (`REQ-`, `FR-`, etc.)
  - Layer 2: Structural cue extraction (bullet/numbered lists in requirement sections)
  - Layer 3: Modal sentence extraction with dependency and POS validation via spaCy
  - Layer 4: Fallback requirement detection
  - Filtering: Headings, Table of Contents lines, captions, and short sentences (< 4 words)
- Full test suite: 14 passing unit tests (9 in `test_extraction.py`, 5 in `test_requirement_extractor.py`).

## What Has Actually Been Verified
- 14/14 unit tests pass in 2.56s.
- `extract_requirements` executed against `data/test/sample_srs.txt`:
  - Exactly 6 requirements extracted (REQ-001 through REQ-006).
  - All 6 captured under `layer_1_explicit_id` with 0.95 confidence.
  - Section heading `ONLINE BANKING SYSTEM` excluded.
  - 0 false positives, 0 missed requirements.
- Verified exclusion of Table of Contents and Figure/Table captions in unit tests.
- Verified Layer 2 structural bullet lists in functional sections and Layer 3 modal verbs in prose.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Layered approach ensures documents with explicit numbering are not corrupted by sentence segmentation heuristics.
- spaCy `en_core_web_sm` loaded once at module level for sentence boundary detection, POS tagging, and syntactic dependency verification.
- Every requirement carries exact character start/end offsets, source layer, and confidence score.

## Files/Modules Currently Being Worked On
- None (Phase 2 completed).

## Exact Next Step
- Phase 3: Build SQLAlchemy models (`Document`, `DocumentVersion`, `Requirement`), Alembic migrations, Pydantic schemas, and FastAPI REST endpoints (`POST /api/documents/upload`, `GET /api/documents`, `GET /api/documents/{id}`, `DELETE /api/documents/{id}`, `POST /api/documents/{id}/extract`, `GET /api/documents/{id}/requirements`).

## Last Verification Performed
- `pytest backend/tests/ -v`: 14 passed in 2.56s on 2026-09-16 15:22:50.
- Sample extraction output verified.

## Metadata
- **Last Updated**: 2026-09-16 15:23:00
- **Last Commit Hash**: 851ccd1

