# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 10
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution), Phase 7 (Requirement Quality Score and Explanation Aggregation), Phase 8 (Human-in-the-Loop Review and MVP API Surface), Phase 9 (Report Generation), Phase 10 (Frontend Foundation)
- **Current Task**: Ready to proceed to Phase 11 (Core Feature Pages)

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
  - `GET /api/documents/{id}/report?format=html|csv|pdf&type=requirements|issues`: REST endpoint serving printable HTML, structured CSVs, and offline-rendered PDFs.
  - Offline PDF generation powered by pure Python `xhtml2pdf` (ReportLab engine, zero external GTK system dependencies on Windows).
- Frontend Foundation (Phase 10):
  - Next.js 14 App Router project in `frontend/` with TypeScript and Tailwind CSS.
  - Design system tokens from Stitch UI reference archive: typography (`Inter`, `JetBrains Mono`), color tokens (`surface`, `on-surface`, `secondary`, `primary`, `outline`, `error`), calm enterprise layout without gradients/neon.
  - Persistent left sidebar (`sidebar.tsx`) with shield logo, workspace switcher, 8 navigation links (`Dashboard`, `Documents`, `Requirement Viewer`, `Analysis`, `AI Suggestions`, `Version Comparison`, `Reports`, `Settings`), and `ISO 29148 Engine Online` badge.
  - Top bar (`topbar.tsx`) with breadcrumb trail, global search input (`⌘K`), backend connection badge, theme switcher, and user profile.
  - Reusable UI state components in `frontend/components/ui/`: `LoadingState`, `EmptyState`, `ErrorState`.
  - Typed API client in `frontend/services/api.ts` with one typed method per FastAPI endpoint.
  - TypeScript types mirroring backend models in `frontend/types/index.ts`.
  - Shell pages: `/` (Dashboard overview), `/documents` (Document management repository), and foundation placeholders for all remaining routes.
- Full test suite: 48 passing unit and integration tests across the backend.

## What Has Actually Been Verified
- 48/48 tests pass in 40.19s with 100% pass rate.
- Frontend build: `npm run build` compiled 11/11 static pages with zero errors.
- Live browser verification: Browser subagent navigated to `http://localhost:3000/`, verified topbar and sidebar with all 8 links, clicked through to `/documents` with shell intact, and returned to `/`.
- Report generation: Verified on sample document with generated HTML, CSV, and PDF artifacts.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Deterministic scoring and rule-based checks without LLM ensure instantaneous evaluation, zero execution cost, and mathematical repeatability.
- Report generation is 100% offline and self-contained; `xhtml2pdf` runs via pure Python without requiring GTK runtime binaries on Windows.
- Next.js 14 App Router with persistent layout and typed client ensures clean component boundaries and zero redundant re-renders.

## Files/Modules Currently Being Worked On
- None (Phase 10 completed).

## Exact Next Step
- Phase 11: Core frontend feature pages (built one at a time):
  - Page 1: Documents (Upload drag & drop / picker, list with filename, type, size, req count, status, date, actions: analyze, view, delete).
  - Page 2: Requirement Viewer (Table/list of requirements, filters, search, click requirement -> detail panel with highlighted problem spans, score waterfall, SHAP token chart, and review buttons).
  - Page 3: Dashboard (KPI cards, functional vs non-functional donut, issue counts by type, score distribution histogram, worst requirements list).
  - Page 4: Analysis (Issues grouped by category, expandable cards, side-by-side duplicate view with aligned phrases).
  - Page 5: Reports (Preview plus export buttons for HTML, CSV, PDF).

## Last Verification Performed
- `npm run build`: 11/11 pages compiled successfully with zero errors.
- Live browser subagent testing on 2026-09-16 18:51:53.
- `pytest backend/tests/ -v`: 48 passed in 40.19s on 2026-09-16 18:42:06.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 18:52:00
- **Last Commit Hash**: 1cc83fd


