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

## Phase 3: Database and API for Documents and Requirements
- **Date**: 2026-09-16
- **What was built**:
  - `backend/app/core/database.py`: SQLAlchemy database engine, session factory, declarative base, and FastAPI session dependency `get_db`.
  - `backend/app/models/document.py`: SQLAlchemy models for `Document`, `DocumentVersion`, and `Requirement` with simple cascading relationships.
  - Alembic migration environment initialized (`alembic.ini`, `backend/alembic/env.py`) and migration `58e6a70d176c` applied to SQLite database (`srs_guardian.db`).
  - Pydantic schemas in `backend/app/schemas/`: `DocumentListItem`, `DocumentDetail`, `RequirementResponse`, and `DocumentExtractResponse`.
  - REST API router in `backend/app/api/documents.py`:
    - `POST /api/documents/upload`: Saves file, runs validation, extracts raw/cleaned text, stores Document and DocumentVersion v1.0 (201 Created).
    - `GET /api/documents`: Lists documents with requirement counts (200 OK).
    - `GET /api/documents/{id}`: Document detail with cleaned text and requirement count (200 OK, 404 on missing).
    - `DELETE /api/documents/{id}`: Deletes document and cascading versions/requirements (200 OK).
    - `POST /api/documents/{id}/extract`: Runs Phase 2 extractor on document text, stores requirements in DB, sets status to 'extracted' (200 OK).
    - `GET /api/documents/{id}/requirements`: Returns all extracted requirements for a document (200 OK).
  - API test suite in `backend/tests/test_api_documents.py` (3 tests covering full lifecycle, invalid file rejection, 404 checks).
- **Key decisions**:
  - Kept ORM models simple with no polymorphic tables or unnecessary inheritance.
  - Used Alembic for formal schema tracking and migration history.
  - Idempotent requirement extraction endpoint wipes existing requirements before re-inserting to prevent duplicate runs.
- **How to run**:
  - Run server: `uvicorn backend.app.main:app --port 8000`
  - Run all tests: `pytest backend/tests/ -v`
  - Upload document: `curl -X POST "http://127.0.0.1:8000/api/documents/upload" -F "file=@data/test/sample_srs.txt"`
- **Known limitations**:
  - Analysis, classification (Functional/Non-Functional), and quality scoring are not yet attached to requirements (deferred to Phase 4+).
  - Frontend not yet built (deferred to Phase 10).

## Phase 4: Requirement Classification with SHAP Explainability
- **Date**: 2026-09-16
- **What was built**:
  - PROMISE_exp dataset ingested into `data/raw/PROMISE_exp.arff` (969 total requirements: 444 Functional, 525 Non-Functional) and documented in `docs/DATASETS.md`.
  - `backend/app/ml/train_classifier.py`: Pipeline training TF-IDF (word 1-2 grams, min_df=2, sublinear_tf=True) + LogisticRegression (`max_iter=1000`, `random_state=42`) with stratified 80/20 train/test split.
  - Evaluation results on held-out test split (194 samples):
    - Accuracy: 86.08%
    - Precision (Non-Functional): 82.50%
    - Recall (Non-Functional): 94.29%
    - F1-Score: 0.8800
    - Confusion Matrix: TN=68, FP=21, FN=6, TP=99
  - Model pipeline serialized to `backend/app/ml/artifacts/classifier_pipeline.joblib`.
  - Global SHAP summary plot generated and saved to `docs/figures/shap_summary.png`.
  - `backend/app/ml/classifier.py`: Lightweight classifier loading pipeline once and predicting label + confidence probability.
  - `backend/app/ml/explain_classifier.py`: Millisecond-level SHAP LinearExplainer returning top 8 token attributions for the predicted class with in-memory caching.
  - Database schema & API update:
    - Added `classification_label`, `classification_prob`, and `classification_explanation` columns to `Requirement` model via Alembic migration `9f880cb9f8ed`.
    - Integrated classification directly into `POST /api/documents/{id}/extract`.
    - Added `GET /api/requirements/{id}` and `GET /api/requirements/{id}/explain` endpoints in `backend/app/api/requirements.py`.
  - Test suite in `backend/tests/test_classifier.py` (2 tests, 19 tests total passing across backend).
- **Key decisions**:
  - TF-IDF + Logistic Regression chosen as default: instant CPU inference, deterministic behavior, and exact word-level linear attribution with SHAP.
  - SHAP values cached per requirement ID to avoid recomputing attributions.
- **How to run**:
  - Train model: `python -m backend.app.ml.train_classifier`
  - Run tests: `pytest backend/tests/ -v`
  - Query requirement explanation: `curl http://127.0.0.1:8000/api/requirements/1/explain`
- **Known limitations**:
  - Semantic duplicate detection and rule-based ambiguity checks are not yet built (deferred to Phase 5 and 6).

## Phase 5: Ambiguity Detection and Readability Analysis
- **Date**: 2026-09-16
- **What was built**:
  - `backend/app/nlp/rules/weak_terms.yaml`: Vocabulary of subjective and vague terms categorized into speed, quality, quantity, usability, and generic, with per-term explanations and actionable suggestions.
  - `backend/app/nlp/ambiguity.py`: Deterministic rule-based ambiguity detection engine featuring 6 independent checks:
    - CHECK A (Weak / Subjective Terms): Matches configurable YAML terms with exact word boundaries.
    - CHECK B (Weak Modals): Identifies non-binding modals (`should`, `may`, `could`, `might`).
    - CHECK C (Missing Measurable Criterion): Detects unquantified performance/capacity concepts (`time`, `speed`, `latency`, etc.) lacking numeric thresholds.
    - CHECK D (Vague Pronouns): Flags subject pronouns (`it`, `this`, `that`, `they`) lacking preceding noun antecedents.
    - CHECK E (Compound Requirements): Flags multiple normative modals or coordinated actions violating requirement singularity.
    - CHECK F (Passive Voice Without Actor): Dependency check identifying `nsubjpass` constructions without an explicit agent (`by <actor>`).
  - Unified explanation schema contract implemented (`finding_id`, `module`, `method`, `rule_id`, `spans`, `factors`, `human_explanation`, `suggestion`, `confidence`).
  - `backend/app/nlp/readability.py`: Computes objective readability metrics:
    - Word count, clause count, clause nesting depth, passive voice ratio, Flesch Reading Ease, and Gunning Fog index.
  - Unit test suites:
    - `backend/tests/test_ambiguity.py`: Positive and negative test cases for all 6 ambiguity checks + schema validation.
    - `backend/tests/test_readability.py`: Metric calculation and passive voice ratio verification.
  - 28/28 tests passing across the backend test suite.
- **Key decisions**:
  - Strictly rule-based without transformer or LLM overhead (free, deterministic, explainable).
  - Every finding highlights exact character spans (`start`, `end`, `text`) for inline frontend display.
- **How to run**:
  - Run tests: `pytest backend/tests/test_ambiguity.py backend/tests/test_readability.py -v`
  - Run all tests: `pytest backend/tests/ -v`
- **Known limitations**:
  - Semantic duplicate detection via embeddings is not yet implemented (deferred to Phase 6).

## Phase 6: Semantic Duplicate Detection with Similarity Attribution
- **Date**: 2026-09-16
- **What was built**:
  - `sentence-transformers` added to `backend/requirements.txt` and installed (`all-MiniLM-L6-v2`, 384-dimensional dense vectors on CPU).
  - `backend/app/ml/embeddings.py`:
    - Model loaded once on CPU with batching.
    - Two-tier caching system (in-memory dict + persistent SHA-256 disk cache at `data/cache/embeddings/{hash}.npy`).
    - Guarantees zero redundant recomputation of embeddings.
  - `backend/app/core/config.py`:
    - Added configurable `DUPLICATE_SIMILARITY_THRESHOLD: float = 0.80`.
  - `backend/app/ml/duplicates.py`:
    - Candidate blocking for documents with >50 requirements via spaCy content lemma intersection (`NOUN`, `PROPN`, `VERB`).
    - Pairwise cosine similarity matrix computation over normalized embeddings.
    - Similarity attribution via noun-chunk and verb-object phrase extraction (`extract_key_phrases`), pairwise phrase encoding, and greedy alignment.
    - Full compliance with unified explanation schema (`finding_id`, `module="duplicates"`, `method="embedding_similarity"`, `rule_id="SEMANTIC_DUPLICATE"`, `spans`, `factors`, `human_explanation`, `suggestion`, `confidence`).
  - `backend/app/schemas/duplicate.py`:
    - Pydantic models: `PhraseSpan`, `AlignedPhrase`, `DuplicatePair`, `DocumentDuplicatesResponse`.
  - `backend/app/api/documents.py`:
    - Exposed `GET /api/documents/{id}/duplicates` endpoint with optional `threshold` query parameter.
  - Test suites and validation:
    - `backend/tests/test_duplicates.py` with 6 automated tests (embedding disk caching, phrase extraction, duplicate detection, false positive rejection, candidate blocking on 54 requirements, and live FastAPI endpoint test).
    - Full test suite passing: 34/34 tests across the backend.
- **Key decisions**:
  - `all-MiniLM-L6-v2` runs locally on CPU with zero API costs and high semantic fidelity for short technical sentences.
  - Persistent SHA-256 disk cache ensures embeddings survive server restarts and are never re-encoded.
  - Similarity attribution extracts both noun chunks and verb-object actions to provide transparent concept mappings (e.g. "reset their password" <-> "recover forgotten passwords").
- **How to run**:
  - Run duplicate tests: `pytest backend/tests/test_duplicates.py -v`
  - Run all tests: `pytest backend/tests/ -v`
  - Live endpoint: `curl http://127.0.0.1:8000/api/documents/1/duplicates`
- **Known limitations**:
  - Numeric contradictions (like REQ-004 vs REQ-005) currently surface as high semantic duplicates (0.9160) because sentence embeddings capture topic similarity rather than numerical logical exclusivity. A dedicated contradiction module (Phase 12) will address constraint conflicts.

## Phase 7: Requirement Quality Score and Explanation Aggregation
- **Date**: 2026-09-16
- **What was built**:
  - `backend/app/nlp/rules/score_weights.yaml`:
    - Configurable point deductions for all active ambiguity rules, readability thresholds, and semantic duplicates.
  - `docs/SCORING.md`:
    - Formal mathematical formulation of overall score and 6 sub-scores (Clarity, Ambiguity, Testability, Readability, Structure, Consistency).
    - Deduction weights table with engineering justifications.
    - Worked example on REQ-001.
  - `backend/app/nlp/scoring.py`:
    - `score_requirement`: Calculates 0–100 deterministic quality score, 6 bounded sub-scores, and a step-by-step waterfall trace starting from 100 down to final score.
    - `score_document`: Aggregates document mean, median, min, max, score distribution bins (`90-100`, `70-89`, `50-69`, `<50`), worst-performing requirements, and issue counts.
  - `backend/app/schemas/scoring.py`:
    - Pydantic models: `WaterfallStepResponse`, `PenaltyApplied`, `RequirementScoreResponse`, `WorstRequirementItem`, `DocumentQualitySummaryResponse`.
  - `backend/app/api/documents.py`:
    - Exposed `GET /api/documents/{id}/quality` endpoint returning document aggregates and individual requirement waterfall breakdowns.
  - `backend/tests/test_scoring.py`:
    - 7 automated tests covering clean requirement scoring, waterfall trace integrity, duplicate penalties, floor clamping, document aggregation, and live API endpoint.
    - 41/41 tests passing across the backend suite in 54.20s.
- **Key decisions**:
  - Entirely deterministic scoring with zero LLM involvement (reproducible, instant, zero cost).
  - Waterfall audit trail provides complete transparency for why points were deducted.
- **How to run**:
  - Run scoring tests: `pytest backend/tests/test_scoring.py -v`
  - Run all tests: `pytest backend/tests/ -v`
  - Live endpoint: `curl http://127.0.0.1:8000/api/documents/1/quality`
- **Known limitations**:
  - Quality scores reflect only machine-checkable heuristics; human review is required in Phase 8 to accept, reject, or edit findings.

## Phase 8: Human-in-the-Loop Review and MVP API Surface
- **Date**: 2026-09-16
- **What was built**:
  - `backend/app/models/document.py`:
    - `Issue` model (`id`, `requirement_id`, `module`, `type`, `severity`, `explanation_json`, `status`, `created_at`).
    - `Review` model (`id`, `issue_id`, `action`, `edited_text`, `note`, `reviewed_at`).
    - Added `issues` relationship on `Requirement` model with cascading delete.
  - `backend/alembic/versions/3a4b5c6d7e8f_create_issues_and_reviews_tables.py`:
    - Formal database migration creating `issues` and `reviews` tables with indices and foreign keys.
  - `backend/app/schemas/issue.py`:
    - Pydantic models: `ReviewActionRequest`, `ReviewResponse`, `IssueResponse`, `DocumentAnalysisResponse`.
  - `backend/app/schemas/requirement.py`:
    - Added `RequirementDetailResponse` with quality score, waterfall, and attached issues.
  - `backend/app/api/documents.py`:
    - `POST /api/documents/{id}/analyze`: Orchestrates the complete analysis pipeline (extraction, classification, ambiguity rules, readability, semantic duplicates, quality scoring), persists all detected issues to the `issues` table with `ai_flagged` status while preserving human-reviewed decisions, updates document status to `analyzed`, and returns document summary and issue counts.
    - `GET /api/documents/{id}/issues`: Returns issues for a document with filtering by `module`, `severity`, and `status_filter`.
  - `backend/app/api/issues.py`:
    - `POST /api/issues/{id}/review`: Accepts human reviewer actions (`accept`, `reject`, `edit`, `mark_reviewed`), creates an audit trail entry in `reviews` table, updates the `Issue.status`, and if `action == "edit"` updates the `Requirement.text` directly in the database.
  - `backend/app/api/requirements.py`:
    - `GET /api/requirements/{id}`: Returns full requirement detail including requirement metadata, classification, quality score, waterfall trace, and associated issues with human review status.
  - `backend/tests/test_issues_and_review.py`:
    - Full end-to-end integration test covering document analysis, issue listing with filters, review actions (accept, edit, reject), database text modification, and requirement detail query.
    - Full test suite passing: 42/42 tests across the backend in 39.09s.
- **Key decisions**:
  - Clear separation between AI findings (`ai_flagged`) and human decisions (`accepted`, `rejected`, `edited`, `reviewed`).
  - Analysis pipeline is idempotent: re-analyzing clears unreviewed AI flags while preserving human-reviewed decisions.
  - Every review action creates an immutable record in the `reviews` table for auditability and future evaluation.
- **How to run**:
  - Run tests: `pytest backend/tests/test_issues_and_review.py -v`
  - Run all tests: `pytest backend/tests/ -v`
  - Trigger analysis: `curl -X POST http://127.0.0.1:8000/api/documents/1/analyze`
  - Review an issue: `curl -X POST http://127.0.0.1:8000/api/issues/1/review -H "Content-Type: application/json" -d '{"action": "accept", "note": "Verified"}'`
- **Known limitations**:
  - Export reports (HTML, CSV, PDF) are not yet implemented (deferred to Phase 9).

## Phase 9: Report Generation
- **Date**: 2026-09-16
- **What was built**:
  - `backend/app/services/reports.py`:
    - `build_report_data`: Compiles document info, functional/non-functional split, quality score distribution, worst requirements, issues grouped by type and severity, and human review decisions.
    - `generate_html_report`: Jinja2-rendered printable enterprise report.
    - `generate_csv_report`: Exports `requirements` (row per requirement with sub-scores) or `issues` (row per issue with explanation and review decision).
    - `generate_pdf_report`: Offline PDF compilation of the HTML report using `xhtml2pdf` (pure Python / ReportLab, zero external GTK system dependencies on Windows).
  - `backend/app/templates/report.html`:
    - Clean corporate stylesheet with print layout (`@page A4`), KPI metric cards, score distribution table, issue breakdowns, and per-requirement review audit cards.
  - `backend/app/api/documents.py`:
    - Exposed `GET /api/documents/{id}/report?format=html|csv|pdf&type=requirements|issues`.
  - `backend/tests/test_reports.py`:
    - 6 automated tests covering HTML rendering, CSV requirements export, CSV issues export, valid binary PDF generation (`%PDF-1.4`), 404 handling, and 400 invalid format validation.
    - Full test suite passing: 48/48 tests across the backend in 40.19s.
  - Live verification on sample document (`data/test/sample_srs.txt`) producing:
    - `data/test/sample_report.html` (16,720 chars)
    - `data/test/sample_report_requirements.csv` (986 chars)
    - `data/test/sample_report_issues.csv` (2,567 chars)
    - `data/test/sample_report.pdf` (14,271 bytes, valid PDF)
- **Key decisions**:
  - Selected `xhtml2pdf` over `WeasyPrint` because WeasyPrint requires external C/GTK libraries on Windows, whereas `xhtml2pdf` is 100% self-contained pure Python wheels running completely offline without system DLL configuration.
  - Jinja2 template is self-contained with embedded CSS for maximum portability and deterministic printing.
- **How to run**:
  - Run tests: `pytest backend/tests/test_reports.py -v`
  - Run all tests: `pytest backend/tests/ -v`
  - Export HTML: `curl http://127.0.0.1:8000/api/documents/1/report?format=html`
  - Export CSV: `curl http://127.0.0.1:8000/api/documents/1/report?format=csv&type=requirements`
  - Export PDF: `curl http://127.0.0.1:8000/api/documents/1/report?format=pdf -o report.pdf`
- **Known limitations**:
  - Frontend user interface is not yet built (ready for Phase 10: Frontend foundation).

## Phase 10: Frontend Foundation
- **Date**: 2026-09-16
- **What was built**:
  - `frontend/package.json`: Next.js 14 App Router project with TypeScript, Tailwind CSS, Lucide React, Recharts, clsx, and tailwind-merge.
  - `frontend/tailwind.config.ts` & `frontend/app/globals.css`:
    - Clean enterprise design system implemented directly from Stitch UI reference tokens (`surface`, `surface-container-lowest`, `on-surface`, `secondary`, `outline`, `error`).
    - Calm enterprise-SaaS styling with zero neon, zero gradients, and crisp borders.
  - `frontend/lib/utils.ts`: `cn` class merger.
  - `frontend/types/index.ts`: TypeScript interfaces mirroring backend Pydantic models (`DocumentListItem`, `DocumentDetail`, `Requirement`, `RequirementDetail`, `SubScores`, `WaterfallStep`, `Issue`, `Review`, `DocumentQualitySummary`, `DocumentAnalysisResponse`, `DuplicatePair`).
  - `frontend/services/api.ts`: Typed API client with one function per backend endpoint (`getDocuments`, `getDocument`, `uploadDocument`, `deleteDocument`, `extractRequirements`, `getDocumentRequirements`, `getRequirement`, `analyzeDocument`, `getDocumentQuality`, `getDocumentDuplicates`, `getDocumentIssues`, `reviewIssue`, `getReportUrl`).
  - Reusable UI state components in `frontend/components/ui/`:
    - `loading-state.tsx`: Spinner and status text.
    - `empty-state.tsx`: Dashed container with icon, title, description, and action button.
    - `error-state.tsx`: Error alert box with retry button.
  - App Shell in `frontend/components/layout/` and `frontend/app/layout.tsx`:
    - Persistent left sidebar (`sidebar.tsx`) with shield logo, workspace switcher, 8 navigation items (`Dashboard`, `Documents`, `Requirement Viewer`, `Analysis`, `AI Suggestions`, `Version Comparison`, `Reports`, `Settings`), and `ISO 29148 Engine Online` badge.
    - Persistent top bar (`topbar.tsx`) with breadcrumbs, global search bar (`⌘K`), sync status badge, theme toggle, and user chip.
  - Routes implemented:
    - `/`: Dashboard landing page with executive KPI cards and quick actions.
    - `/documents`: Document management page with empty/loading states and table view.
    - `/requirements`, `/analysis`, `/suggestions`, `/compare`, `/reports`, `/settings`: Clean foundation placeholder pages.
  - `npm run build`: Verified 11/11 static routes compiled with zero errors.
  - Live Browser Subagent Verification: Automated browser test confirming navigation between `/`, `/documents`, and return to `/` with intact app shell and active highlights.
- **Key decisions**:
  - Adhered strictly to Stitch design tokens for consistent visual identity.
  - Avoided ad-hoc styles in favor of reusable design tokens.
  - Kept feature page logic bounded to Phase 11 per Rule 3.
- **How to run**:
  - Run backend: `.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000`
  - Run frontend: `cd frontend && npm run dev`
  - Open browser: `http://localhost:3000`
- **Known limitations**:
  - Feature pages are implemented in Phase 11.

## Phase 11: MVP Core Feature Pages & Full-Stack Integration
- **Date**: 2026-09-16
- **What was built**:
  - **FastAPI CORS Middleware**: Added `CORSMiddleware` in `backend/app/main.py` allowing frontend requests from `http://localhost:3000`.
  - **API Client & Type Definitions**:
    - `frontend/services/api.ts`: Typed fetch methods with request body-based header handling.
    - `frontend/types/index.ts`: Updated `DocumentListItem` (`requirement_count`) and `ShapToken` definitions.
  - **Page 1: Documents** (`frontend/app/documents/page.tsx`):
    - Drag-and-drop file upload zone with 20MB limit and format validation (.pdf, .docx, .txt).
    - Real-time search and status filter chips (`All`, `Analysed`, `Uploaded`).
    - Data table showing filename, format badge, size, page count, requirement count, status badge, and uploaded date.
    - Actions per row: "Analyze" / "Re-Analyze" (triggers `api.analyzeDocument`), "View Reqs", "Reports", and delete with confirmation dialog.
  - **Page 2: Requirement Viewer** (`frontend/app/requirements/page.tsx`):
    - Document selector dropdown with requirement count.
    - Search in document input and classification filter (`All`, `Functional`, `Non-Functional`).
    - Requirements list (left pane) with active selection indicator, score badge, and statement preview.
    - Inspection Workspace (right pane):
      - Header with requirement key, classification pill, confidence percentage, and copy ID button.
      - Quality Score gauge (/100) with rating and threshold delta.
      - Requirement statement box with problematic terms highlighted in amber with tooltip hints.
      - Classification Attribution (SHAP) token strip showing positive and negative word contributions.
      - Waterfall Score Deductions trace (`Base 100 -> deductions -> Final`).
      - 6 Sub-Scores breakdown with colored progress bars (Clarity, Ambiguity, Testability, Readability, Structure, Consistency).
      - Detected issues cards with human review action buttons (Accept, Reject, inline Edit).
  - **Page 3: Dashboard** (`frontend/app/page.tsx`):
    - Document selector with live metrics.
    - 4 KPI metric cards: Total Requirements, Average Quality Score, Potential Findings, and Human Review Status.
    - Quality Score Distribution histogram bars (90-100, 70-89, 50-69, <50).
    - Findings by Rule Category bars (Ambiguity, Semantic Duplicates, Readability).
    - Requirement Classification Donut Graphic (Functional vs Non-Functional counts and percentages).
    - Lowest Scoring Requirements list with overall score badges and direct links to Requirement Viewer.
  - **Page 4: Analysis** (`frontend/app/analysis/page.tsx`):
    - Category tabs: All Findings, Ambiguity & Weak Terms, Semantic Duplicates, Readability & Voice.
    - Search and filter bar by severity (Critical, Warning, Info) and status (Unreviewed, Accepted, Rejected, Edited).
    - Issue cards with highlighted statement text, violation explanation, and suggestion.
    - Side-by-side Semantic Duplicate comparison box showing Req 1 vs Req 2 with cosine similarity percentage and key aligned phrases.
    - Inline review action buttons: Accept, Reject, Edit Statement.
  - **Page 5: Reports** (`frontend/app/reports/page.tsx`):
    - Document selector dropdown.
    - Executive Scorecard rail showing mean score, total requirements, total findings, human reviews closed, and score range.
    - Export download buttons: Formal Audit Report (PDF), Printable HTML Scorecard (HTML), Requirements Dataset (CSV), Defect & Review Ledger (CSV).
    - Live interactive in-browser report preview iframe rendering the full printable HTML report.
- **Key decisions**:
  - All 5 pages wired directly to real backend REST endpoints and database data.
  - Adhered strictly to Stitch design tokens for calm, clean enterprise layout.
  - All interactions (upload, analyze, review, export) function end-to-end without mocking.
- **How to run**:
  - Run backend: `.venv\Scripts\python -m uvicorn backend.app.main:app --port 8000`
  - Run frontend: `cd frontend && npm run dev`
  - Open browser: `http://localhost:3000`
- **Known limitations**:
  - None for MVP scope. This completes the core MVP pipeline.

## Final Audit & End-to-End Verification (Phases 0–11)
- **Date**: 2026-09-16 20:35:00
- **What was verified**:
  - **Git History**: All 12 phase completion commits verified in git history (`1e26d77` through `0f1695f` + `168d98e`). Branch `main` synchronized with `origin/main`.
  - **Backend Test Suite**: 48/48 unit and integration tests passed in 19.15s (100% pass rate).
  - **Frontend Production Build**: Next.js 14 App Router compiled 11/11 static pages with 0 errors (`npm run build`).
  - **Live End-to-End Smoke Test**: Complete 14-step automated execution using `data/test/sample_srs.txt` against live backend API (`http://127.0.0.1:8000`) and database:
    1. Health check: 200 OK.
    2. Upload document: HTTP 201 Created.
    3. Document listing in repository: Verified.
    4. Orchestrated analysis: 6 requirements extracted, 6 issues detected.
    5. Requirement classification: 3 Functional, 3 Non-Functional.
    6. Quality scoring: Mean=82.5, Median=85.0, Min=65.0, Max=100.0.
    7. Semantic duplicate detection: 2 pairs detected (REQ-004 <-> REQ-005: 91.6%, REQ-002 <-> REQ-003: 82.2%).
    8. Issue persistence in DB: 6 issues created with `ai_flagged` status.
    9. Requirement detail: SHAP linear attributions and waterfall steps verified.
    10. Human review: Issue #13 accepted and recorded in immutable `Review` audit table.
    11. HTML audit report: Generated (16,398 bytes).
    12. CSV requirements export: Generated (7 rows).
    13. CSV issues export: Generated (7 rows).
    14. PDF report: Generated (13,847 bytes, valid `%PDF` header).
  - **Frontend Real-Data Verification**: All 5 core feature pages (`/documents`, `/requirements`, `/`, `/analysis`, `/reports`) verified to load live data via `frontend/services/api.ts` with zero hardcoded analytical data.
  - **Database & Alembic Migrations**: Migration chain `58e6a70d176c -> 9f880cb9f8ed -> 3a4b5c6d7e8f (head)` verified.
  - **Architecture Integrity**: All locked technical decisions (Python 3.11, FastAPI, SQLite, Next.js, spaCy, scikit-learn TF-IDF + LR, all-MiniLM-L6-v2, pure Python xhtml2pdf, LLM disabled) preserved.
## Phase 12: Contradiction Detection
- **Date**: 2026-09-17
- **What was built**:
  - `backend/app/nlp/numeric_constraints.py`: Mechanism 1 (Numeric Constraint Engine):
    - Extracts structured 5-tuples `(entity, attribute, comparator, value, unit)` using regex and spaCy dependency parsing.
    - Mathematical interval conflict detection checking if $[low_1, high_1] \cap [low_2, high_2] = \emptyset$.
    - Catches REQ-004 ("at least 8 characters" -> `[8, inf)`) vs REQ-005 ("exactly 6 characters" -> `[6, 6]`).
  - `backend/app/ml/contradictions.py`: Mechanism 2 (Candidate-Blocked NLI Engine):
    - Candidate blocking filter requiring shared entity lemma >= 1 and embedding cosine similarity >= 0.55 to avoid $O(N^2)$ inference.
    - Bidirectional NLI inference on CPU with permanent SHA-256 disk caching in `data/cache/nli_cache.json`.
    - On-demand token attribution using Captum `LayerIntegratedGradients` on token embeddings, cached permanently in `data/cache/nli_attributions_cache.json`.
  - Scoring & Quality Waterfall:
    - Added `POTENTIAL_CONTRADICTION: 25.0` penalty in `backend/app/nlp/rules/score_weights.yaml`.
    - Integrated into `score_requirement` in `backend/app/nlp/scoring.py` with Consistency subscore deduction and waterfall trace.
  - REST APIs:
    - Wired into `POST /api/documents/{id}/analyze`.
    - Added `GET /api/documents/{id}/contradictions` in `backend/app/api/documents.py`.
    - Added `GET /api/contradictions/{id}/explain` in `backend/app/api/contradictions.py`.
  - Frontend:
    - Added Contradictions category tab in `frontend/app/analysis/page.tsx` with side-by-side conflict cards, numeric constraint tags, and review action buttons.
    - Updated `frontend/services/api.ts` and `frontend/types/index.ts`.
  - Unit Tests:
    - `backend/tests/test_contradictions.py`: 8 tests covering extraction, comparators, interval logic, sample cases, candidate blocking, NLI semantic contradictions, Captum attribution, and end-to-end analyze.
- **Key decisions**:
  - Rule-based numeric constraint conflict engine chosen as the primary deterministic mechanism for exact explanations and zero ML noise.
  - Candidate blocking strictly bounds NLI pairs to keep execution cheap on CPU.
  - Captum attribution run strictly on-demand when requested by human reviewer.
- **How to run**:
  - Run tests: `pytest backend/tests/test_contradictions.py -v`
  - Verify contradictions endpoint: `curl http://127.0.0.1:8000/api/documents/{id}/contradictions`
- **Known limitations**:
  - EARS template validation and ISO 29148 checks are deferred to Phase 13.

## Phase 13: EARS Syntax Validation and ISO 29148 Checks
- **Date**: 2026-09-18
- **What was built**:
  - `backend/app/nlp/ears.py`:
    - Evaluates requirement syntax against 6 standard EARS templates:
      1. Ubiquitous: `THE <system> SHALL <response>`
      2. Event-driven: `WHEN <trigger>, THE <system> SHALL <response>`
      3. State-driven: `WHILE <state>, THE <system> SHALL <response>`
      4. Unwanted: `IF <condition>, THEN THE <system> SHALL <response>`
      5. Optional feature: `WHERE <feature>, THE <system> SHALL <response>`
      6. Complex: combinations of preconditions (while/when/where/if).
    - Identifies non-conforming structures and missing elements (e.g. non-normative modals, missing actors/systems).
    - Generates actionable restructuring tips.
  - `backend/app/nlp/iso_checks.py`:
    - Implements 7 selected machine-checkable checks based on ISO/IEC/IEEE 29148:
      1. `ISO_SINGULAR`: Checks for single obligation per statement (detects multiple modal verbs and conjoined action verbs).
      2. `ISO_UNAMBIGUOUS`: Flags subjective, vague, or non-normative terms (reuses Phase 5 ambiguity findings without double-penalty).
      3. `ISO_VERIFIABLE`: Inspects measurable performance criteria and quantitative constraints (flags subjective speed/performance terms lacking metrics).
      4. `ISO_COMPLETE`: Evaluates syntactic completeness (actor/subject, modal verb, action verb, and target object).
      5. `ISO_CONSISTENT`: Detects document-wide terminology drift and synonym variation (e.g., 'reset' vs 'recover').
      6. `ISO_TRACEABLE`: Validates unique persistent identifiers (`REQ-XXX`, `FR-XX`) and extraction provenance.
      7. `ISO_STRUCTURE`: Evaluates syntactic conformance to EARS template structures.
  - `docs/ISO_CHECKS.md`:
    - Complete documentation of all 7 checks, methods, score deductions, and engineering limitations.
  - Scoring & Waterfall Integration:
    - Updated `backend/app/nlp/rules/score_weights.yaml` and `backend/app/nlp/scoring.py` to deduct ISO penalties in the waterfall trace while explicitly avoiding double-counting with Phase 5 ambiguity checks.
  - REST APIs:
    - `POST /api/documents/{id}/analyze`: Runs ISO 29148 analysis, persists standards issues with `module="standards"`, and incorporates deductions into scores.
    - `GET /api/documents/{id}/standards`: Returns document-level ISO 29148 and EARS compliance breakdown.
    - `GET /api/requirements/{id}`: Enriches requirement inspection details with EARS pattern and ISO checks.
  - Frontend:
    - `frontend/app/requirements/page.tsx`: Added EARS Syntax & ISO 29148 inspection panel with pattern badges, template preview, and 7-point checklist.
    - `frontend/app/analysis/page.tsx`: Added `ISO 29148 Checks` category tab for reviewing standards findings.
    - `frontend/services/api.ts` and `frontend/types/index.ts`: Added typed methods and interfaces.
  - Automated Tests:
    - `backend/tests/test_iso_checks.py`: 11 unit and integration tests covering all 6 EARS templates, all 7 ISO checks, scoring waterfall, and API endpoints (100% pass rate).
- **Key decisions**:
  - Strictly adhered to Rule 10: "selected machine-checkable checks based on ISO/IEC/IEEE 29148". Zero claims of certification or full standard compliance.
  - Prevented double-penalization: ISO checks reuse ambiguity findings without redundant point loss.
- **How to run**:
  - Run tests: `pytest backend/tests/test_iso_checks.py -v`
  - Run all tests: `pytest backend/tests/ -v`
  - Query standards API: `curl http://127.0.0.1:8000/api/documents/{id}/standards`
- **Known limitations**:
  - Checks evaluate syntax and explicit terminology; semantic domain completeness requires stakeholder review.

## Architecture Tooling: Archify Live Runtime Diagram
- **Date**: 2026-10-05
- **What was built**:
  - Integrated Archify agent skill into the repository under `.agents/skills/archify`.
  - Authored repository-backed architecture specification (`.archify/architecture-srs-guardian-20261005-084200/candidate.json`).
  - Executed `archify finalize` to build verified interactive HTML architecture diagram:
    - Target: `architecture.html` and `docs/architecture.html` (771 KB standalone interactive HTML).
    - 11 core components mapped in exact runtime sequence:
      1. Requirements Engineer (Browser client)
      2. Next.js Web UI (`frontend/app/page.tsx`, `frontend/services/api.ts`)
      3. FastAPI REST Gateway (`backend/app/main.py`, `backend/app/api/documents.py`)
      4. Document Ingestion & Extraction (`backend/app/nlp/requirement_extractor.py`)
      5. Classification & SHAP (`backend/app/ml/classifier.py`)
      6. Ambiguity & Readability Engine (`backend/app/nlp/ambiguity.py`)
      7. Semantic Duplicate Detection (`backend/app/ml/duplicates.py`)
      8. Contradiction Detection Engine (`backend/app/nlp/numeric_constraints.py`)
      9. EARS & ISO 29148 Engine (`backend/app/nlp/iso_checks.py`)
      10. Deterministic Quality Scoring (`backend/app/nlp/scoring.py`)
      11. Relational Database & Audit Store (`backend/app/core/database.py`)
    - Trust Boundaries: "SRS Guardian System Environment" (system boundary) and "NLP & ML Verification Pipeline" (security group boundary).
    - Live Runtime Mapping: Continuous serpentine primary path connecting all components in runtime order with 0 crossings and 0 bends.
    - Verified Source Links: All components include verified line references pinned to commit `43cd880ae7c519e1694006f82e353b969314d8c9`.
    - Guided Story (Press P): 5 presentation chapters covering Ingress, Extraction, Verification, Scoring, and Storage.
- **Key decisions**:
  - Followed Master Prompt guidelines: 11 core components (within 8-12 limit), 1 primary runtime path, trust boundaries, and cards for secondary details.
  - Zero external cloud/LLM runtime dependency; diagram file is 100% self-contained and opens offline in any browser.
- **How to run**:
  - Open `architecture.html` or `docs/architecture.html` directly in any web browser (Chrome, Edge, Firefox).
  - Re-generate / re-finalize: `node .agents/skills/archify/bin/archify.mjs finalize architecture <candidate.json> <output.html> --repo-root . --quality showcase --json`
- **Known limitations**:
  - Requires modern browser with JavaScript enabled for interactive filters, routing inspection, and story presentation.

## Phase 14: AI Rewrite Suggestions and Gherkin Generation (Tier 2)
- **Date**: 2026-10-05
- **What was built**:
  - `backend/app/services/llm.py`:
    - Single centralized gateway for all generative LLM calls in compliance with Rule 6.
    - Global on/off switch governed by `settings.LLM_ENABLED` (system remains 100% operational offline when disabled).
    - Hard disk caching via SHA-256 in `data/cache/llm_cache.json` ensuring no prompt is ever sent twice (Rule 7).
    - `suggest_rewrite`: Resolves flagged ambiguity and ISO defects while preserving domain intent and conforming to EARS templates.
    - `generate_gherkin`: Converts requirements into standard Given-When-Then testable acceptance criteria.
  - `backend/app/schemas/llm.py`:
    - `RewriteSuggestionRequest`, `RewriteSuggestionResponse`, `GherkinGenerationRequest`, `GherkinGenerationResponse`.
  - `backend/app/api/requirements.py`:
    - `POST /api/requirements/{id}/suggest-rewrite`
    - `POST /api/requirements/{id}/generate-gherkin`
    - `POST /api/requirements/suggest-rewrite` (ad-hoc)
    - `POST /api/requirements/generate-gherkin` (ad-hoc)
  - `backend/tests/test_llm.py`:
    - 6 unit and integration tests verifying disabled behavior, disk caching hits, ad-hoc endpoints, and requirement endpoints (100% passing).
  - Frontend Integration:
    - `frontend/services/api.ts` & `frontend/types/index.ts`: Typed API client methods and response models.
    - `frontend/app/requirements/page.tsx`: Added AI Assistance panel with "Suggest Rewrite" and "Generate Gherkin" action buttons, cached badges, rationale breakdown, formatted Gherkin copy button, and "Use This Rewrite" human-in-the-loop edit injection.
- **Key decisions**:
  - Provider: Google Gemini API free-tier (`gemini-2.5-flash`) via official `google-genai` SDK.
  - LLM usage strictly bounded to rewrite suggestions and Gherkin generation; all analytical core detection remains classical ML, rules, and embeddings.
  - Human-in-the-loop guarantee: AI suggestions are never applied automatically; reviewer must explicitly accept or edit.
- **How to run**:
  - Run tests: `$env:PYTHONPATH="."; .venv\Scripts\pytest.exe backend/tests/test_llm.py -v`
  - Query rewrite API: `curl -X POST http://127.0.0.1:8000/api/requirements/{id}/suggest-rewrite`
  - Query Gherkin API: `curl -X POST http://127.0.0.1:8000/api/requirements/{id}/generate-gherkin`
- **Known limitations**:
  - Free-tier rate limits apply if disk cache is bypassed with novel requirements; production deployments should consider dedicated quotas or local Ollama models.

## Phase 15A: Rule-Based Gherkin Test Skeletons via EARS (Tier 3)
- **Date**: 2026-10-05
- **What was built**:
  - `backend/app/nlp/gherkin.py`:
    - Deterministic Gherkin test skeleton generator prioritizing rule-based extraction from EARS syntax patterns (`analyze_ears`).
    - Direct clause mapping for all standard EARS patterns:
      - Event-driven: `Given <system> is operational -> When <trigger> -> Then <system> <modal> <response>`.
      - State-driven: `Given <system> is active and <state> -> When a functional request occurs -> Then <system> <modal> <response>`.
      - Unwanted behavior: `Given <system> is operating -> When <condition> -> Then <system> <modal> <response>`.
      - Optional feature: `Given feature '<feature>' is enabled -> When caller invokes <system> -> Then <system> <modal> <response>`.
      - Ubiquitous: `Given <system> is initialized and ready -> When the function is requested -> Then <system> <modal> <response>`.
      - Complex: Combinations of state, feature, and triggers.
    - Non-conforming fallback: Delegates to generative LLM only if `settings.LLM_ENABLED` is true; otherwise produces structured deterministic fallback skeleton.
  - API Integration:
    - Updated `POST /api/requirements/{id}/generate-gherkin` and ad-hoc `POST /api/requirements/generate-gherkin` to return `source` (`ears_rule`, `llm`, `fallback_rule`) and `ears_pattern`.
  - Frontend:
    - `frontend/app/requirements/page.tsx`: Added badges indicating `EARS Rule-Based` (emerald), `LLM Generated` (indigo), and the specific EARS pattern tag.
  - Automated Tests:
    - `backend/tests/test_gherkin.py`: 8 unit and integration tests covering all 5 EARS patterns, fallback mode, ad-hoc API, and requirement detail API (100% pass rate).
- **Key decisions**:
  - Rule-first generation eliminates external LLM API dependency and costs for all conforming requirements.
  - Preserved existing LLM generation logic as fallback.
- **How to run**:
  - Run tests: `$env:PYTHONPATH="."; .venv\Scripts\pytest.exe backend/tests/test_gherkin.py -v`
  - Query API: `curl -X POST http://127.0.0.1:8000/api/requirements/generate-gherkin -H "Content-Type: application/json" -d "{\"requirement_text\": \"The system shall allow users to download their transaction history.\"}"`
- **Known limitations**:
  - Rule-based skeletons produce template steps; domain-specific edge test cases require human reviewer refinement or optional LLM augmentation.

## Phase 15B: Requirement Clustering & Thematic Topic Labeling (Tier 3)
- **Date**: 2026-10-05
- **What was built**:
  - `backend/app/ml/clustering.py`:
    - Reuses existing cached `all-MiniLM-L6-v2` embeddings from `backend.app.ml.embeddings` (Rule 7: zero recomputation).
    - Adaptive cluster sizing $k$ scaled logarithmically to document size.
    - Deterministic `AgglomerativeClustering` using cosine metric and average linkage.
    - TF-IDF topic keyword extraction to auto-label clusters with top distinguishing terms (e.g. `Password / Contain / Characters`).
  - `backend/app/schemas/clustering.py`:
    - `ClusteredRequirementItem`, `ClusterGroup`, `DocumentClustersResponse`.
  - REST API:
    - `GET /api/documents/{id}/clusters?k=<optional>`: Fetches and clusters document requirements.
  - Frontend:
    - `frontend/services/api.ts` & `frontend/types/index.ts`: Typed methods and data structures.
    - `frontend/app/analysis/page.tsx`: Added "Thematic Clusters" category tab displaying cluster groups, size badges, top keyword tags, and member requirements with links to requirement detail.
  - Automated Tests:
    - `backend/tests/test_clustering.py`: 5 unit and integration tests covering empty, single, sample requirements, and REST API (100% pass rate).
- **Key decisions**:
  - Zero recomputation: MiniLM embeddings are fetched from existing SQLite / file cache.
  - TF-IDF cluster auto-labeling gives immediate human-readable topic summaries without calling generative LLMs.
- **How to run**:
  - Run tests: `$env:PYTHONPATH="."; .venv\Scripts\pytest.exe backend/tests/test_clustering.py -v`
  - Query API: `curl http://127.0.0.1:8000/api/documents/{id}/clusters`
- **Known limitations**:
  - For very small documents (< 3 requirements), clusters collapse to 1 or 2 groups.

## Phase 15C: Version Comparison & Semantic Diffing (Tier 3)
- **Date**: 2026-10-05
- **What was built**:
  - `backend/app/nlp/version_comparison.py`:
    - Cross-version requirement alignment engine using a hybrid matching strategy:
      1. Exact requirement key match (e.g. `REQ-001` <-> `REQ-001`).
      2. High-confidence semantic similarity fallback using cached `all-MiniLM-L6-v2` embeddings (cosine similarity $\ge 0.70$).
    - Requirement delta classification: `added`, `removed`, `modified`, `unchanged`.
    - Fine-grained word-level diffing utilizing Python `difflib.SequenceMatcher` producing structured inline chunks (`[-deleted-]`, `[+added+]`, unchanged).
    - Quality score delta tracking between base and target document requirements.
    - Defect lifecycle tracking: identifies `resolved_issues` (present in base, resolved in target) and `new_issues` (introduced in target).
  - `backend/app/schemas/comparison.py`:
    - Pydantic models: `RequirementDiffItem`, `VersionComparisonSummary`, `VersionComparisonResponse`.
  - REST API:
    - Added `GET /api/documents/{id}/compare/{other_id}` in `backend/app/api/documents.py`.
  - Frontend:
    - Updated `frontend/services/api.ts` with `compareDocuments(id, otherId)`.
    - Updated `frontend/types/index.ts` with version comparison types.
    - `frontend/app/compare/page.tsx`: Implemented full side-by-side comparison page with document selectors, 6 KPI cards (Score Delta, Added, Removed, Modified, Resolved Issues, New Issues), filter tabs, inline diff viewing, and defect lifecycle badges.
  - Automated Tests:
    - `backend/tests/test_version_comparison.py`: 3 tests covering text diff generation, full version comparison lifecycle (modified requirement, defect resolution, score improvements), and 404 validation (100% pass rate).
- **Key decisions**:
  - Reused existing MiniLM embeddings disk cache for semantic matching of renumbered requirements.
  - Inline word-level diffing makes requirement changes instantly clear without requiring external tools.
- **How to run**:
  - Run tests: `$env:PYTHONPATH="."; .venv\Scripts\pytest.exe backend/tests/test_version_comparison.py -v`
  - Query API: `curl http://127.0.0.1:8000/api/documents/1/compare/2`
- **Known limitations**:
  - Re-ordering of paragraphs without textual changes is classified as unchanged based on key/embedding alignment.
