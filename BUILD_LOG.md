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

## Phase 2: Requirement Extraction
- **Date**: 2026-09-16
- **What was built**:
  - `backend/app/nlp/requirement_extractor.py`: Layered requirement extraction architecture:
    - Layer 1: Explicit ID patterns (`REQ-`, `FR-`, `NFR-`, `\d+\.\d+`, etc.) with confidence 0.95.
    - Layer 2: Structural cues (bullet/numbered lists within requirement-oriented sections) with confidence 0.85.
    - Layer 3: Modal verb sentences (`shall`, `must`, `should`, `will`, `is required to`, `needs to`) with subject parsing via spaCy (`en_core_web_sm`) with confidence 0.70.
    - Layer 4: Fallback for unstructured text with confidence 0.40.
    - Filters: Automatic exclusion of headings, Table of Contents lines, captions (Figure/Table), and short sentences (< 4 words).
  - `Requirement` dataclass tracking `req_id`, `text`, `source_layer`, `confidence`, `char_start`, `char_end`, and `section`.
  - `backend/tests/test_requirement_extractor.py`: 5 tests covering ID-labelled docs, bullet lists in functional sections, modal prose docs, TOC/caption filtering, and fallback layer.
- **Key decisions**:
  - Layered approach prioritizes explicit author structure first, falling back progressively to grammatical and keyword signals.
  - spaCy `en_core_web_sm` loaded for syntactic dependency and POS validation of requirement subjects and modals.
- **How to run**:
  - Run tests: `pytest backend/tests/test_requirement_extractor.py -v`
  - Extract from text: `python -c "from backend.app.nlp.requirement_extractor import extract_requirements; print(len(extract_requirements('REQ-001: The system shall...')))"`
- **Known limitations**:
  - Requirements are not yet stored in a persistent database (deferred to Phase 3).
  - Classification and quality analysis are not yet applied (deferred to Phase 4+).


