# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 8
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution), Phase 7 (Requirement Quality Score and Explanation Aggregation), Phase 8 (Human-in-the-Loop Review and MVP API Surface)
- **Current Task**: Ready to auto-proceed to Phase 9 (Report Generation)

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
- Full test suite: 42 passing unit and integration tests across the backend.

## What Has Actually Been Verified
- 42/42 tests pass in 39.09s with 100% pass rate.
- End-to-end human review and analysis verified on sample document (`data/test/sample_srs.txt`):
  - Ingestion -> Analyze -> 6 requirements, 6 AI-flagged issues, quality score 82.5.
  - Issue accept: CHECK_A_WEAK_TERM on REQ-001 accepted with reviewer note.
  - Issue edit: CHECK_B_WEAK_MODAL on REQ-001 edited text -> requirement text directly updated in DB.
  - Issue reject: SEMANTIC_DUPLICATE rejected with note.
  - Requirement detail query reflects updated text and human-reviewed issues.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Deterministic scoring and rule-based checks without LLM ensure instantaneous evaluation, zero execution cost, and mathematical repeatability.
- Clear separation between AI findings (`ai_flagged`) and human decisions (`accepted`, `rejected`, `edited`, `reviewed`).
- Analysis pipeline is idempotent: re-analyzing clears unreviewed AI flags while preserving human-reviewed decisions.
- Every review action creates an immutable record in the `reviews` table for auditability and future evaluation.

## Files/Modules Currently Being Worked On
- None (Phase 8 completed).

## Exact Next Step
- Phase 9: Report Generation (HTML, CSV, PDF export of analysis and human review decisions).
  - Provide short Rule 8 explanation.
  - Implement report generation service in `backend/app/services/reports.py`.
  - Expose `GET /api/documents/{id}/report?format=html|csv|pdf`.
  - Verify on sample document and commit/push.

## Last Verification Performed
- `pytest backend/tests/ -v`: 42 passed in 39.09s on 2026-09-16 18:31:01.
- Live sample document analysis and review workflow verification in `scratch/verify_phase8.py`.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 18:32:00
- **Last Commit Hash**: b8129ce
