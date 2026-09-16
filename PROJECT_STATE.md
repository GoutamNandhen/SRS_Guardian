# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 6
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability), Phase 5 (Ambiguity Detection and Readability Analysis), Phase 6 (Semantic Duplicate Detection with Similarity Attribution)
- **Current Task**: Ready to begin Phase 7 (Requirement quality score and waterfall aggregation)

## What Is Actually Implemented
- Standard project structure (`backend/app/{api,core,models,schemas,services,nlp,ml,utils}`, `frontend/`, `data/`, `docs/`, `docker/`).
- Database & ORM: SQLAlchemy models for `Document`, `DocumentVersion`, `Requirement` with Alembic migrations.
- Ingestion & Extraction: Multi-format text ingestion (PDF, DOCX, TXT) and layered requirement extraction engine (explicit IDs, structural cues, modal verbs, fallback).
- Classification & Explainability: TF-IDF + Logistic Regression model with 86.08% test accuracy, serialized in `classifier_pipeline.joblib`, and millisecond SHAP LinearExplainer attribution.
- Ambiguity Detection Engine in `backend/app/nlp/ambiguity.py`:
  - Vocabulary config in `backend/app/nlp/rules/weak_terms.yaml` (speed, quality, usability, quantity, generic).
  - 6 independent rule checks (weak terms, weak modals, missing metrics, vague pronouns, compound clauses, passive voice without actor).
  - Unified explanation schema (`finding_id`, `module`, `method`, `rule_id`, `spans`, `factors`, `human_explanation`, `suggestion`, `confidence`).
- Readability Analysis in `backend/app/nlp/readability.py`:
  - Computes word count, clause count, max clause nesting depth, passive voice ratio, Flesch Reading Ease, and Gunning Fog index.
- Semantic Duplicate Detection & Explainability in `backend/app/ml/duplicates.py` and `backend/app/ml/embeddings.py`:
  - `sentence-transformers` running `all-MiniLM-L6-v2` on CPU.
  - Two-tier embedding cache (memory dict + persistent SHA-256 disk cache in `data/cache/embeddings/`).
  - Candidate blocking for documents with >50 requirements via content lemma intersection.
  - Pairwise cosine similarity matrix with configurable threshold (`settings.DUPLICATE_SIMILARITY_THRESHOLD = 0.80`).
  - Similarity attribution via spaCy noun-chunk and action-phrase extraction with token/phrase embeddings and greedy alignment.
  - REST endpoint: `GET /api/documents/{id}/duplicates`.
- Full test suite: 34 passing unit and integration tests across the backend.

## What Has Actually Been Verified
- 34/34 tests pass in 60.31s with 100% pass rate.
- Duplicate detection verified on sample document (`data/test/sample_srs.txt`):
  - REQ-002 vs REQ-003 correctly flagged with similarity `82.18%` (above 0.80 threshold).
  - Aligned phrases surfaced:
    - `'users'` <-> `'Users'` (1.0000)
    - `'their registered email'` <-> `'their registered email address'` (0.9679)
    - `'reset their password'` <-> `'forgotten passwords'` (0.7491)
  - Unified explanation schema validated.
- False positive behavior verified on dissimilar requirement pairs:
  - REQ-001 vs REQ-004: similarity = 0.2073 (flagged = False)
  - REQ-001 vs REQ-006: similarity = 0.4031 (flagged = False)
  - REQ-004 vs REQ-006: similarity = 0.1797 (flagged = False)
  - False positive rate = 0% on test pairs.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- `all-MiniLM-L6-v2` on CPU provides high semantic accuracy without GPU overhead or cloud API dependencies.
- Persistent SHA-256 disk caching prevents redundant recomputation of embeddings across requests and restarts.
- Phrase-level attribution breaks down sentence embeddings into human-understandable concept pairs.
- Candidate blocking on content lemmas prevents quadratic scaling bottlenecks on large specification documents.

## Files/Modules Currently Being Worked On
- None (Phase 6 completed).

## Exact Next Step
- Phase 7: Requirement quality scoring and explanation aggregation:
  - Build `backend/app/nlp/scoring.py` with reproducible, deterministic formula starting at 100 with deduction penalties from findings in Phases 4–6.
  - Sub-scores (Clarity, Ambiguity, Testability, Readability, Structure, Consistency).
  - Deductions config file: `backend/app/nlp/rules/score_weights.yaml`.
  - Waterfall breakdown data structure: `100 -> -15 (weak modal) -> -20 (weak term) -> score`.
  - Document-level aggregates (mean score, score distribution, worst requirements, issue counts).
  - Document formula in `docs/SCORING.md`.

## Last Verification Performed
- `pytest backend/tests/ -v`: 34 passed in 60.31s on 2026-09-16 18:13:49.
- Live sample document duplicate detection and false positive script verified on 2026-09-16 18:12:30.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 18:15:00
- **Last Commit Hash**: 2bec58a

