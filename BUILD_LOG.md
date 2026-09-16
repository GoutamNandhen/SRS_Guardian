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

## Phase 1: Document Ingestion and Text Extraction
- **Date**: 2026-09-16
- **What was built**:
  - `backend/app/nlp/extractors.py`: Multi-format text extraction supporting PDF (via PyMuPDF), DOCX (via python-docx including tables), and TXT, unified through `ExtractedDocument` dataclass and `extract_text()` dispatcher.
  - `backend/app/nlp/cleaning.py`: Rule-based text cleaning covering repeated running headers/footers removal across pages, standalone page number elimination, hyphenated line break repair, structured wrapped line joining (preserving requirement keys/bullets), and whitespace normalization while preserving raw text in `CleanedDocument`.
  - `backend/app/utils/file_validation.py`: Pre-ingestion validation for file existence, extension whitelist, non-empty check, and size limits.
  - Test datasets in `data/test/`: `sample_srs.txt`, `sample_srs.docx` (with paragraphs and tables), and `sample_srs.pdf` (multi-page with running headers/footers).
  - Unit test suite in `backend/tests/test_extraction.py` (9 tests covering extraction, cleaning, and validation).
- **Key decisions**:
  - Used PyMuPDF for fast, layout-aware PDF text extraction.
  - Python-docx extracts both standard paragraphs and table rows/cells so requirements defined in tables are not lost.
  - Kept original raw text alongside cleaned text to support downstream character offset highlighting.
- **How to run**:
  - Run test suite: `pytest backend/tests/test_extraction.py -v`
  - Run sample extraction: `python -c "from backend.app.nlp.extractors import extract_text; print(extract_text('data/test/sample_srs.txt').text)"`
- **Known limitations**:
  - Requirement segmentation/extraction logic is not yet implemented (deferred to Phase 2).
  - REST endpoints for upload/extraction are not yet wired (deferred to Phase 3).

