# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: ALL PHASES COMPLETE (Phases 0 through 18.1)
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution), Phase 7 (Requirement Quality Score and Explanation Aggregation), Phase 8 (Human-in-the-Loop Review and MVP API Surface), Phase 9 (Report Generation), Phase 10 (Frontend Foundation), Phase 11 (MVP Core Feature Pages), Phase 12 (Contradiction Detection), Phase 13 (EARS Syntax Validation and ISO 29148 Checks), Phase 14 (AI Rewrite Suggestions and Gherkin Generation), Phase 15A (Rule-Based Gherkin Test Skeletons via EARS), Phase 15B (Requirement Clustering & Thematic Topic Labeling), Phase 15C (Version Comparison & Semantic Diffing), Phase 16 (Testing and Quantitative Evaluation), Phase 17 (Packaging, Documentation, and Final Presentation Readiness), Phase 18 (Explainable Visual Review & Comprehensive Reporting), Phase 18.1 (Simplified Review Output & SHAP Appendix).
- **Current Task**: All planned phases (0 to 18.1) are 100% complete, fully verified with automated test suites and live evaluation benchmarks, containerized via Docker and Docker Compose, and comprehensively documented for final-year project defense.

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
  - `POST /api/documents/{id}/analyze`: End-to-end orchestration running extraction, classification, ambiguity rules, readability, semantic duplicates, contradiction detection, ISO standards checks, and quality scoring; persists issues with `ai_flagged` status while preserving human reviews.
  - `GET /api/documents/{id}/issues`: Filterable by `module`, `severity`, and `status_filter`.
  - `POST /api/issues/{id}/review`: Records human actions (`accept`, `reject`, `edit`, `mark_reviewed`), creates immutable `Review` audit record, and updates requirement text on edit.
  - `GET /api/requirements/{id}`: Full requirement detail with classification, quality score, waterfall trace, issues, EARS result, and ISO checks.
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
- EARS Syntax Validation & ISO 29148 Checks (Phase 13):
  - `backend/app/nlp/ears.py`: Evaluates requirements against 6 EARS templates (Ubiquitous, Event-driven, State-driven, Unwanted behavior, Optional feature, Complex), identifies structural non-conformities, and provides restructuring tips.
  - `backend/app/nlp/iso_checks.py`: Evaluates 7 machine-checkable quality characteristics based on ISO/IEC/IEEE 29148: Singular, Unambiguous, Verifiable, Complete, Consistent, Traceable, Conforming Structure.
  - `docs/ISO_CHECKS.md`: Documented all 7 checks, what they inspect, scoring impact, and limitations.
  - `GET /api/documents/{id}/standards`: Returns document-level ISO 29148 conformance statistics and per-requirement reports.
  - UI integration: EARS syntax and ISO checklist cards in Requirement Viewer (`frontend/app/requirements/page.tsx`) and `ISO 29148 Checks` category tab in Analysis page (`frontend/app/analysis/page.tsx`).

- Rule-Based Gherkin Test Skeletons via EARS (Phase 15A):
  - `backend/app/nlp/gherkin.py`: Deterministic Given/When/Then scenario generator mapping from EARS parsed elements (Event-driven, State-driven, Unwanted, Optional, Ubiquitous, Complex) with fallback to LLM or deterministic template.
  - REST endpoints `POST /api/requirements/{id}/generate-gherkin` and ad-hoc `POST /api/requirements/generate-gherkin` return `source` (`ears_rule`, `llm`, `fallback_rule`) and `ears_pattern`.
  - Frontend badges in `frontend/app/requirements/page.tsx` display `EARS Rule-Based` (emerald) and pattern tag.
- Requirement Clustering & Thematic Topic Labeling (Phase 15B):
  - `backend/app/ml/clustering.py`: Adaptive requirement clustering over cached sentence embeddings with deterministic Agglomerative Clustering.
  - Distinctive TF-IDF topic keyword extraction providing human-readable cluster titles.
  - REST endpoint: `GET /api/documents/{id}/clusters`.
  - Frontend: `Thematic Clusters` category tab in `frontend/app/analysis/page.tsx` displaying grouped cards, sizes, and keywords.
- Explainable Visual Review & Comprehensive Reporting (Phase 18):
  - Schemas in `backend/app/schemas/review_report.py`: `FindingSpan`, `AnnotatedFinding`, `RequirementReviewItem`, `DocumentReviewReportResponse`, and confidence bands (`high`, `medium`, `low`, `unavailable`).
  - Reporting Service in `backend/app/services/review_report.py`:
    - `build_review_report_data`: Compiles complete finding locations and audit trails without recomputation or LLM calls.
    - `generate_annotated_srs_pdf`: Uses PyMuPDF (`fitz`) to highlight finding regions, add note popups, and prepend an audit legend page without modifying the uploaded source.
    - `generate_comprehensive_pdf_report`: Renders 19-section formal audit report to PDF via `xhtml2pdf`.
    - `generate_comprehensive_docx_report`: Renders 19-section formal audit report to Microsoft Word (`.docx`) format using `python-docx`.
  - REST Endpoints in `backend/app/api/review_reports.py`:
    - `GET /api/documents/{id}/review-report` (includes `overall_status`, `executive_summary_table`, `shap_attributions`, `dynamic_conclusion`)
    - `GET /api/documents/{id}/review-report/annotated-pdf`
    - `GET /api/documents/{id}/review-report/pdf` (formal Executive PDF Review Report)
    - `GET /api/documents/{id}/review-report/docx` (formal Executive Word DOCX Report)
  - Phase 18.1 Simplified Review Output & SHAP Appendix:
    - Primary output re-architected to prioritize human reviewer scannability: Page 1 Executive Summary Table (`Requirement | Status | Finding Summary | Suggested Action`), Important Findings cards, No Issue Detected list, and Reviewer Decision & Sign-off Block.
    - Section 6 / Final Section: Classifier Feature Attribution (SHAP) Appendix with real TF-IDF + Logistic Regression linear explainability via `backend.app.ml.explain_classifier.explain` (CPU real-time and cached, showing tokens, SHAP values, and plain-English interpretations).
    - Report integrity fixes: 100% scoring consistency (81.7/100 verified), target requirement resolution (`REQ-003`), pair finding deduplication, and contradiction prioritization over duplicates for quantitative conflicts.
  - Frontend Interactive Detailed Review Page in `frontend/app/reports/review/page.tsx`:
    - Tab Switcher: `[Executive Review]` (default executive report layout with decision block) and `[Interactive Workbench]` (3-pane span highlight and inspection interface).
  - Dynamic redirect route `frontend/app/reports/review/[id]/page.tsx`.

## What Has Actually Been Verified
- `pytest backend/tests/test_review_report.py -v`: 6/6 unit and integration tests pass with 100% pass rate in 39.97s (verifying score consistency, status determination, executive table structure, pair deduplication, and real SHAP attributions).
- `python scratch/verify_phase18.py`: Live end-to-end demonstration on `data/test/sample_srs.txt` passed, verified REQ-001 ambiguity ('quickly'), REQ-002/003 duplicate, REQ-004/005 contradiction, REQ-006 acceptable (score 100), document score 81.7, and generated all 3 artifacts (`sample_srs_annotated.pdf`, `sample_srs_comprehensive_report.pdf`, `sample_srs_comprehensive_report.docx`).
- `npm run build`: 12/12 Next.js pages cleanly compiled with zero TypeScript or lint errors.
- Live execution on sample document (`data/test/sample_srs.txt`):
  - Clustered into 4 distinct functional groups:
    - Cluster 1: `Using / Registered / Email` (REQ-002, REQ-003: Password recovery/reset)
    - Cluster 2: `Contain / Characters / Password` (REQ-004, REQ-005: Length constraints)
    - Cluster 3: `User / Respond / Account` (REQ-001: Balance checking)
    - Cluster 4: `Transaction / History / Download` (REQ-006: Transaction history export)
  - 100% offline, CPU-runnable, utilizing cached embeddings.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Rule-based EARS pattern parsing using dependency parsing and regular expressions without generative LLM dependency.
- Selected machine-checkable checks based on ISO/IEC/IEEE 29148 (Rule 10: no claims of ISO certification).
- Avoided double-penalization between Phase 5 ambiguity checks and ISO checks.
- All contradiction and quality findings labeled "potential".
- Live Runtime Architecture Mapping: Added Archify skill (`.agents/skills/archify`) and generated verified standalone HTML diagram (`architecture.html` and `docs/architecture.html`) with verified commit line references.
- Rule 6 Enforced: Generative LLM is strictly quarantined to Phase 14 rewrite suggestions and fallback Gherkin generation. All core classification, ambiguity detection, duplication checks, contradiction detection, clustering, and quality scoring remain 100% functional offline with zero LLM dependence.
- Rule 7 Enforced: Permanent SHA-256 disk caching prevents any duplicate API calls or embedding recomputation.

## Exact Next Step
- Final Project Defense & Presentation:
  - System is completely built, tested, containerized, and documented.
  - Deliver live demonstration using `data/test/sample_srs.txt`.
  - Present evaluation findings from `docs/EVALUATION.md` and architecture walkthrough using `docs/architecture.html`.
  - Author formal thesis report chapters referencing `docs/PROJECT_REPORT.md`.

## Last Verification Performed
- Full Backend Test Suite: 18 test modules passing in `backend/tests/`.
- `python -m backend.evaluation.run_evaluation`: Full empirical benchmarking passed across all 4 capabilities, saved to `data/test/evaluation_results.json` and `docs/EVALUATION.md`.
- `npm run build`: 11/11 Next.js pages cleanly compiled with standalone Docker runtime output.
- Docker configuration verified (`docker-compose.yml`, `docker/Dockerfile.backend`, `docker/Dockerfile.frontend`).

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-10-06 00:48:00
- **Last Commit Hash**: 53ddb8e


