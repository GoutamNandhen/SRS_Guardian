# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 5
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis)
- **Current Task**: Ready to begin Phase 6 (Duplicate detection with similarity attribution)

## What Is Actually Implemented
- Standard project structure (`backend/app/{api,core,models,schemas,services,nlp,ml,utils}`, `frontend/`, `data/`, `docs/`, `docker/`).
- Database & ORM: SQLAlchemy models for `Document`, `DocumentVersion`, `Requirement` with Alembic migrations.
- Ingestion & Extraction: Multi-format text ingestion (PDF, DOCX, TXT) and layered requirement extraction engine (explicit IDs, structural cues, modal verbs, fallback).
- Classification & Explainability: TF-IDF + Logistic Regression model with 86.08% test accuracy, serialized in `classifier_pipeline.joblib`, and millisecond SHAP LinearExplainer attribution.
- Ambiguity Detection Engine in `backend/app/nlp/ambiguity.py`:
  - Vocabulary config in `backend/app/nlp/rules/weak_terms.yaml` (speed, quality, usability, quantity, generic).
  - CHECK A: Weak / Subjective terms detection with exact spans.
  - CHECK B: Weak modals (`should`, `may`, `could`, `might`).
  - CHECK C: Missing measurable criteria on performance/capacity concepts.
  - CHECK D: Vague pronoun references without preceding noun antecedents.
  - CHECK E: Compound requirements (multiple normative modals or coordinate actions).
  - CHECK F: Passive voice constructions without actor agents.
  - Unified explanation schema (`finding_id`, `module`, `method`, `rule_id`, `spans`, `factors`, `human_explanation`, `suggestion`, `confidence`).
- Readability Analysis in `backend/app/nlp/readability.py`:
  - Computes word count, clause count, max clause nesting depth, passive voice ratio, Flesch Reading Ease, and Gunning Fog index.
- Full test suite: 28 passing unit and integration tests across the backend.

## What Has Actually Been Verified
- 28/28 tests pass in 17.83s with 100% pass rate.
- Positive and negative test cases verified for all 6 ambiguity checks.
- Execution on sample document (`data/test/sample_srs.txt`):
  - REQ-001 correctly flagged with 2 ambiguity findings:
    - `CHECK_A_WEAK_TERM`: "quickly" (chars 26..33, conf=0.95)
    - `CHECK_B_WEAK_MODAL`: "should" (chars 11..17, conf=0.95)
  - REQ-002 through REQ-006 confirmed free of ambiguity findings.
  - Readability metrics verified across all 6 requirements.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Deterministic rule-based checks without transformers or LLMs keep ambiguity detection fast, repeatable, explainable, and cost-free.
- Unified explanation schema ensures frontend viewer can highlight exact spans and present uniform factor weights.
- Readability reports raw objective metrics without imposing arbitrary pass/fail verdicts.

## Files/Modules Currently Being Worked On
- None (Phase 5 completed).

## Exact Next Step
- Phase 6: Semantic duplicate detection with similarity attribution:
  - Add `sentence-transformers` to `requirements.txt`.
  - Build `backend/app/ml/embeddings.py` (load `all-MiniLM-L6-v2` once on CPU, cache embeddings to disk/DB by text hash).
  - Build `backend/app/ml/duplicates.py` (cosine similarity matrix, threshold 0.80, candidate blocking).
  - Similarity attribution (token-level cosine similarity + shared key noun phrases).
  - Store results as Issue records with unified explanation schema.
  - Wire into API: `GET /api/documents/{id}/duplicates`.

## Last Verification Performed
- `pytest backend/tests/ -v`: 28 passed in 17.83s on 2026-09-16 15:58:47.
- Sample document ambiguity analysis verified on 2026-09-16 15:59:21.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 16:00:00
- **Last Commit Hash**: Pending Phase 5 commit
