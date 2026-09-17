# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 12 (Contradiction Detection)
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution), Phase 7 (Requirement Quality Score and Explanation Aggregation), Phase 8 (Human-in-the-Loop Review and MVP API Surface), Phase 9 (Report Generation), Phase 10 (Frontend Foundation), Phase 11 (MVP Core Feature Pages), Phase 12 (Contradiction Detection)
- **Current Task**: Phase 12 Complete! Two-tier contradiction detection (numeric constraint conflicts + candidate-blocked NLI semantic contradictions with Captum attribution) fully implemented, scored, exposed via REST APIs, integrated into frontend analysis view, and verified.

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
  - `POST /api/documents/{id}/analyze`: End-to-end orchestration running extraction, classification, ambiguity rules, readability, semantic duplicates, contradiction detection, and quality scoring; persists issues with `ai_flagged` status while preserving human reviews.
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
  1. Page 1: Documents list & multi-format upload.
  2. Page 2: Requirement Viewer with waterfall deductions, SHAP token strip, and review actions.
  3. Page 3: Dashboard with 4 KPI cards, score histogram, issue category bars, and classification donut.
  4. Page 4: Analysis with category tabs, expandable issue cards, and side-by-side duplicates.
  5. Page 5: Reports with preview iframe and PDF/HTML/CSV export downloads.
- Contradiction Detection Engine (Phase 12):
  - `backend/app/nlp/numeric_constraints.py` (Mechanism 1 - Primary): Deterministic 5-tuple extraction `(entity, attribute, comparator, value, unit)` and mathematical interval conflict checking ($[low_1, high_1] \cap [low_2, high_2] = \emptyset$). Catches REQ-004 vs REQ-005.
  - `backend/app/ml/contradictions.py` (Mechanism 2 - Secondary): Candidate-blocked NLI semantic contradiction detection with bidirectional inference, SHA-256 disk caching, and on-demand Captum `LayerIntegratedGradients` token attribution.
  - `backend/app/nlp/rules/score_weights.yaml` & `backend/app/nlp/scoring.py`: Added 25.0 point `POTENTIAL_CONTRADICTION` penalty deducted from Consistency sub-score and reflected in waterfall trace.
  - `GET /api/documents/{id}/contradictions`: Returns detected contradiction pairs, mechanisms, conflicting constraints/intervals, and review statuses.
  - `GET /api/contradictions/{id}/explain`: On-demand token attribution endpoint.
  - `frontend/app/analysis/page.tsx`: Added Contradictions category tab displaying side-by-side conflict cards, quantitative interval badges, and review action buttons.

## What Has Actually Been Verified
- `pytest backend/tests/ -v`: 56/56 backend unit and integration tests pass with 100% pass rate in 40.57s.
- `npm run build`: 11/11 Next.js pages cleanly compiled with zero TypeScript or lint errors.
- Live browser subagent verification:
  - Navigated to `http://localhost:3000/analysis?doc=8`.
  - Confirmed Contradictions tab badge displays `1`.
  - Confirmed side-by-side card showing REQ-004 vs REQ-005 is visible with the red `POTENTIAL CONTRADICTION` badge, constraint tags `>= 8.0 characters` vs `== 6.0 characters`, logical conflict analysis, and engineering recommendation.
  - Screenshot verified at `contradictions_tab_1789629210052.png`.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Two-tier hybrid contradiction detection: deterministic rules for quantitative numeric intervals (primary) and candidate-blocked NLI for semantic conflicts (secondary).
- Candidate blocking (lemma overlap + embedding cosine similarity >= 0.55) avoids expensive $O(N^2)$ cross-inferences.
- Captum Integrated Gradients token attribution is computed strictly on-demand when requested by the user and permanently cached to disk.
- All contradiction findings are strictly labeled `POTENTIAL contradiction` as per Rule 10.

## Exact Next Step
- Phase 13: EARS and ISO 29148 checks (rule-based EARS pattern matcher in `backend/app/nlp/ears.py` and machine-checkable standards checks in `backend/app/nlp/iso_checks.py`).

## Last Verification Performed
- `pytest backend/tests/ -v`: 56 passed in 40.57s on 2026-09-17.
- `npm run build`: 11/11 pages compiled with zero errors on 2026-09-17.
- Live browser subagent verified Contradictions tab and conflict card rendering on 2026-09-17.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-17 12:44:00
- **Last Commit Hash**: 9670fd7
