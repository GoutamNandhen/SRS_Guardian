# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 7
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution), Phase 7 (Requirement Quality Score and Explanation Aggregation)
- **Current Task**: Ready to begin Phase 8 (Human-in-the-loop review and MVP API completion)

## What Is Actually Implemented
- Standard project structure (`backend/app/{api,core,models,schemas,services,nlp,ml,utils}`, `frontend/`, `data/`, `docs/`, `docker/`).
- Database & ORM: SQLAlchemy models for `Document`, `DocumentVersion`, `Requirement` with Alembic migrations.
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
- Full test suite: 41 passing unit and integration tests across the backend.

## What Has Actually Been Verified
- 41/41 tests pass in 54.20s with 100% pass rate.
- Quality scoring verified on sample document (`data/test/sample_srs.txt`):
  - REQ-001 scored 65.0 / 100.0 (Step 1: -20.0 on "quickly", Step 2: -15.0 on "should").
  - REQ-002 & REQ-003 scored 85.0 / 100.0 (Penalized -15.0 for semantic duplicate candidate, 82.2% similarity).
  - REQ-004 & REQ-005 scored 85.0 and 75.0 / 100.0 (Penalized for high semantic duplicate / Fog index).
  - REQ-006 scored 100.0 / 100.0 (Clean requirement, 0 issues).
  - Document mean score: 82.5, Median: 85.0, Distribution: 1 Excellent (90-100), 4 Acceptable (70-89), 1 Needs Revision (50-69).

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Deterministic scoring without LLM ensures instantaneous evaluation, zero execution cost, and mathematical repeatability.
- Complete externalization of weights in `score_weights.yaml` enables easy tuning without code modifications.
- Waterfall breakdown provides an auditable trail directly consumable by the UI.

## Files/Modules Currently Being Worked On
- None (Phase 7 completed).

## Exact Next Step
- Phase 8: Human-in-the-loop review, and finish the MVP API surface:
  - Create models: `Issue(id, requirement_id, module, type, severity, explanation_json, status)` and `Review(id, issue_id, action, edited_text, reviewed_at, note)`. Status values: `ai_flagged`, `accepted`, `rejected`, `reviewed`, `edited`.
  - Alembic migration for Issue and Review tables.
  - API routes:
    - `POST /api/issues/{id}/review`
    - `GET /api/documents/{id}/issues` (filters by module, type, status)
    - `GET /api/requirements/{id}` (full detail with findings and score)
    - `POST /api/documents/{id}/analyze` (runs full analysis pipeline and persists issues)
  - Clear distinction between AI findings and human decisions.

## Last Verification Performed
- `pytest backend/tests/ -v`: 41 passed in 54.20s on 2026-09-16 18:23:42.
- Live sample document scoring and waterfall verification on 2026-09-16 18:22:33.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 18:25:00
- **Last Commit Hash**: 7cf7c92


