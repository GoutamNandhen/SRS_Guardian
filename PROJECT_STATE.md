# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 9
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution), Phase 7 (Requirement Quality Score and Explanation Aggregation), Phase 8 (Human-in-the-Loop Review and MVP API Surface), Phase 9 (Report Generation)
- **Current Task**: Ready to proceed to Phase 10 (Frontend Foundation)

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
- Full test suite: 48 passing unit and integration tests across the backend.

## What Has Actually Been Verified
- 48/48 tests pass in 40.19s with 100% pass rate.
- Report generation verified on sample document (`data/test/sample_srs.txt`):
  - `sample_report.html` (16,720 chars): Executive KPI cards, score tables, issue summaries, human reviewer notes.
  - `sample_report_requirements.csv` (986 chars): 6 requirement rows with classifications, confidence, overall score, and 6 sub-scores.
  - `sample_report_issues.csv` (2,567 chars): 6 issue rows with rule types, explanations, suggestions, and reviewer decisions.
  - `sample_report.pdf` (14,271 bytes): Valid `%PDF-1.4` binary stream rendered offline.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Deterministic scoring and rule-based checks without LLM ensure instantaneous evaluation, zero execution cost, and mathematical repeatability.
- Report generation is 100% offline and self-contained; `xhtml2pdf` runs via pure Python without requiring GTK runtime binaries on Windows.
- CSV export supports dual modes (`type=requirements` and `type=issues`) for spreadsheet ingestion and auditing.

## Files/Modules Currently Being Worked On
- None (Phase 9 completed).

## Exact Next Step
- Phase 10: Frontend foundation:
  - Next.js App Router project in `frontend/` with TypeScript and Tailwind CSS.
  - Install and configure shadcn/ui and Recharts.
  - Design system: light/dark theme tokens, typography, enterprise-SaaS layout (no neon, no cyber styling).
  - App shell with persistent left sidebar (Dashboard, Documents, Requirements, Analysis, Suggestions, Compare, Reports, Settings).
  - Typed API client in `frontend/services/api.ts` and types in `frontend/types/`.

## Last Verification Performed
- `pytest backend/tests/ -v`: 48 passed in 40.19s on 2026-09-16 18:42:06.
- Live sample document report export verification in `scratch/verify_phase9.py`.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 18:43:00
- **Last Commit Hash**: 69d60f0

