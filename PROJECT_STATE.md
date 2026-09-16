# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 11 (MVP Core Feature Pages)
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution), Phase 7 (Requirement Quality Score and Explanation Aggregation), Phase 8 (Human-in-the-Loop Review and MVP API Surface), Phase 9 (Report Generation), Phase 10 (Frontend Foundation), Phase 11 (MVP Core Feature Pages)
- **Current Task**: MVP Complete! All 5 core feature pages built, integrated, and verified against live backend APIs and database.

## What Is Actually Implemented
- Standard project structure (`backend/app/{api,core,models,schemas,services,nlp,ml,utils}`, `frontend/`, `data/`, `docs/`, `docker/`).
- Database & ORM: SQLAlchemy models for `Document`, `DocumentVersion`, `Requirement`, `Issue`, and `Review` with Alembic migrations.
- Ingestion & Extraction: Multi-format text ingestion (PDF, DOCX, TXT) and layered requirement extraction engine (explicit IDs, structural cues, modal verbs, fallback).
- Classification & Explainability: TF-IDF + Logistic Regression model with 86.08% test accuracy, serialized in `classifier_pipeline.joblib`, and millisecond SHAP LinearExplainer attribution.
- Ambiguity Detection Engine in `backend/app/nlp/ambiguity.py`:
  - Configurable vocabulary in `backend/app/nlp/rules/weak_terms.yaml`.
  - 6 independent rule checks (weak terms, weak modals, missing metrics, vague pronouns, compound clauses, passive voice without actor).
  - Unified explanation schema (`finding_id`, `module`, `method`, `rule_id`, `spans`, `factors`, `human_explanation`, `suggestion`, `confidence`).
- Readability Analysis in `backend/app/nlp/readability.py`:
  - Computes word count, clause count, max clause nesting depth, passive voice ratio, Flesch Reading Ease, and Gunning Fog index.
- Semantic Duplicate Detection in `backend/app/ml/duplicates.py` and `backend/app/ml/embeddings.py`:
  - CPU inference with `all-MiniLM-L6-v2` and SHA-256 disk caching.
  - Candidate blocking for >50 requirements via content lemma intersection.
  - Cosine similarity matrix and phrase alignment attribution.
  - REST endpoint: `GET /api/documents/{id}/duplicates`.
- Deterministic Quality Scoring & Waterfall Aggregation in `backend/app/nlp/scoring.py`:
  - Configurable penalty weights in `backend/app/nlp/rules/score_weights.yaml`.
  - Formal documentation in `docs/SCORING.md`.
  - 0–100 overall score with step-by-step waterfall trace (`Base Score 100 -> -20.0 -> -15.0 -> Final`).
  - 6 orthogonal sub-scores (Clarity, Ambiguity, Testability, Readability, Structure, Consistency).
  - Document-level summary metrics (mean, median, min, max, distribution histogram, worst requirements, issue counts).
  - REST endpoint: `GET /api/documents/{id}/quality`.
- Human-in-the-Loop Review and MVP API Surface (Phase 8):
  - `Issue` and `Review` SQLAlchemy models with audit history and status lifecycle (`ai_flagged`, `accepted`, `rejected`, `reviewed`, `edited`).
  - `POST /api/documents/{id}/analyze`: End-to-end orchestration running extraction, classification, ambiguity rules, readability, semantic duplicates, and quality scoring; persists issues with `ai_flagged` status while preserving human reviews.
  - `GET /api/documents/{id}/issues`: Filterable by `module`, `severity`, and `status_filter`.
  - `POST /api/issues/{id}/review`: Records human actions (`accept`, `reject`, `edit`, `mark_reviewed`), creates immutable `Review` audit record, and updates requirement text on edit.
  - `GET /api/requirements/{id}`: Full requirement detail with classification, quality score, waterfall trace, and issues with review status.
- Report Generation (Phase 9):
  - `backend/app/services/reports.py`: Data aggregation and export engine for HTML, CSV, and PDF formats.
  - `backend/app/templates/report.html`: Clean corporate report template with KPI cards, score distribution table, issue breakdowns, and requirement review cards.
  - `GET /api/documents/{id}/report?format=html|csv|pdf&type=requirements|issues`: REST endpoint serving printable HTML, structured CSVs, and offline-rendered PDFs via pure Python `xhtml2pdf`.
- Backend CORS Support:
  - Enabled `CORSMiddleware` in `backend/app/main.py` allowing cross-origin requests from `http://localhost:3000`.
- Frontend Foundation & Design System (Phase 10):
  - Next.js 14 App Router project in `frontend/` with TypeScript and Tailwind CSS.
  - Stitch UI reference design tokens (`surface`, `on-surface`, `secondary`, `outline`, `error`).
  - Persistent left sidebar (`sidebar.tsx`) and persistent top bar (`topbar.tsx`).
  - Typed API client (`frontend/services/api.ts`) with typed models in `frontend/types/index.ts`.
- MVP Core Feature Pages (Phase 11):
  1. **Page 1 (Documents)** (`frontend/app/documents/page.tsx`):
     - Drag-and-drop upload zone + file picker for PDF, DOCX, TXT up to 20MB.
     - Live document table displaying filename, format badge, size, page count, requirement count, status badge, uploaded date.
     - Real-time search by filename/type, status filter chips (`All`, `Analysed`, `Uploaded`).
     - Actions per row: "Analyze" / "Re-Analyze" (triggers `api.analyzeDocument`), "View Reqs" (`/requirements?doc={id}`), "Reports" (`/reports?doc={id}`), and Delete with confirmation (`api.deleteDocument`).
  2. **Page 2 (Requirement Viewer)** (`frontend/app/requirements/page.tsx`):
     - Document picker selector with count of requirements.
     - Search in document input and classification filter (`All`, `Functional`, `Non-Functional`).
     - Requirements list (Left panel) with score badge, statement preview, and active selection border.
     - Inspection Workspace (Right panel):
       - Requirement ID, classification badge, probability, copy button.
       - Overall Quality Score gauge (/100) with rating and delta.
       - Statement box with problem spans highlighted and tooltips.
       - Classification Attribution (SHAP) token strip with directional contributions (`+0.32`, `-0.19`).
       - Waterfall Score Deductions trace (`Base 100 -> -25.0 -> Final`).
       - 6 Sub-Scores breakdown with color-coded progress bars (Clarity, Ambiguity, Testability, Readability, Structure, Consistency).
       - Detected Issues cards with Accept, Reject, and direct inline Edit of requirement text.
  3. **Page 3 (Dashboard)** (`frontend/app/page.tsx`):
     - Document picker with live statistics.
     - 4 KPI metric cards: Total Requirements, Average Quality Score, Potential Findings with critical/warning breakdown, Human Review Status.
     - Quality Score Distribution histogram bars (90-100, 70-89, 50-69, <50).
     - Findings by Rule Category bars (Ambiguity, Semantic Duplicates, Readability).
     - Requirement Classification Donut Graphic (Functional vs Non-Functional counts and percentages).
     - Lowest Scoring Requirements list with overall score badges and direct links to Requirement Viewer.
  4. **Page 4 (Analysis)** (`frontend/app/analysis/page.tsx`):
     - Category tabs: All Findings, Ambiguity & Weak Terms, Semantic Duplicates, Readability & Voice.
     - Search and filter bar by severity (Critical, Warning, Info) and review status (Unreviewed, Accepted, Rejected, Edited).
     - Issue cards with highlighted statement text, violation explanation, and suggestion.
     - Side-by-side Semantic Duplicate comparison box showing Req 1 vs Req 2 with cosine similarity percentage and key aligned phrases.
     - Inline review action buttons: Accept, Reject, Edit Statement.
  5. **Page 5 (Reports)** (`frontend/app/reports/page.tsx`):
     - Document selector dropdown.
     - Executive Scorecard rail showing mean score, total requirements, total findings, human reviews closed, and score range.
     - Export download buttons: Formal Audit Report (PDF), Printable HTML Scorecard (HTML), Requirements Dataset (CSV), Defect & Review Ledger (CSV).
     - Live interactive in-browser report preview iframe rendering the full printable HTML report.

## What Has Actually Been Verified
- 48/48 backend tests pass in 35.52s with 100% pass rate (`pytest backend/tests/ -v`).
- Frontend build: `npm run build` compiled 11/11 static pages with zero errors (`/`, `/documents`, `/requirements`, `/analysis`, `/reports`).
- Live browser subagent verification:
  - Page 1 (Documents): Upload dropzone, live table with 2 documents, format badges, requirement counts, status badges, and action buttons verified.
  - Page 2 (Requirement Viewer): Document picker, requirement list (REQ-001 through REQ-006), inspection panel with quality score, highlighted problem spans, SHAP tokens, waterfall penalty deductions, 6 sub-scores, and review buttons verified.
  - Page 3 (Dashboard): 4 KPI cards, score distribution histogram, rule category bars, classification donut, and lowest scoring requirements list verified.
  - Page 4 (Analysis): Category tabs, issue cards with Accept/Reject/Edit actions, and side-by-side semantic duplicate pair comparison verified.
  - Page 5 (Reports): Executive scorecard rail, PDF/HTML/CSV export buttons, and live in-browser HTML report preview iframe verified.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Full-stack integration with FastAPI backend running on `http://127.0.0.1:8000` with CORS middleware and Next.js 14 App Router on `http://localhost:3000`.
- Pure deterministic algorithms (rules, TF-IDF + LR, MiniLM embeddings, mathematical scoring) require zero GPU and zero LLM credits.
- Offline PDF generation via `xhtml2pdf` requires zero external GTK/C dependencies.

## Exact Next Step
- The MVP is complete! Stop here and report MVP completion to the user.

## Last Verification Performed
- `npm run build`: 11/11 pages compiled with zero errors on 2026-09-16.
- Live browser subagent verification across all 5 core feature pages on 2026-09-16.
- `pytest backend/tests/ -v`: 48 passed in 35.52s on 2026-09-16.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 20:07:00
- **Last Commit Hash**: 8677692
