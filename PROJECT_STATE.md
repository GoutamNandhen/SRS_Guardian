# PROJECT_STATE.md — Current State Snapshot

- **Current Phase**: Phase 4
- **Phase Status**: COMPLETE
- **Completed Phases**: Phase 0 (Project Setup), Phase 1 (Document Ingestion and Text Extraction), Phase 2 (Requirement Extraction), Phase 3 (Database and API for Documents and Requirements), Phase 4 (Requirement Classification with SHAP Explainability)
- **Current Task**: Ready to begin Phase 5 (Ambiguity detection and readability analysis)

## What Is Actually Implemented
- Standard project structure (`backend/app/{api,core,models,schemas,services,nlp,ml,utils}`, `frontend/`, `data/`, `docs/`, `docker/`).
- SQLAlchemy database configuration in `backend/app/core/database.py`.
- SQLAlchemy ORM models in `backend/app/models/document.py` (`Document`, `DocumentVersion`, `Requirement`).
- Alembic migrations:
  - `58e6a70d176c`: Initial tables.
  - `9f880cb9f8ed`: Requirement classification columns (`classification_label`, `classification_prob`, `classification_explanation`).
- PROMISE_exp dataset ingested (969 requirements) and documented in `docs/DATASETS.md`.
- Machine Learning classification pipeline:
  - `backend/app/ml/train_classifier.py`: TF-IDF (1-2 grams) + Logistic Regression training with stratified 80/20 train/test split.
  - Test set evaluation (194 samples): Accuracy 86.08%, Non-Functional Precision 82.50%, Non-Functional Recall 94.29%, F1-Score 0.8800.
  - Serialized pipeline in `backend/app/ml/artifacts/classifier_pipeline.joblib`.
  - Global SHAP summary plot in `docs/figures/shap_summary.png`.
- Inference & Explainability modules:
  - `backend/app/ml/classifier.py`: Loads model once and executes fast predictions.
  - `backend/app/ml/explain_classifier.py`: Computes top 8 SHAP token contributions per class with in-memory caching.
- Integrated API:
  - `POST /api/documents/{id}/extract` classifies all extracted requirements and stores predictions + SHAP token attributions in database.
  - `GET /api/requirements/{id}` and `GET /api/requirements/{id}/explain` return requirement details and SHAP token explanations.
- Full test suite: 19 passing unit and integration tests across the backend.

## What Has Actually Been Verified
- 19/19 tests pass in 7.01s with 100% pass rate.
- Classifier test evaluation metrics verified from actual execution:
  - Accuracy: 86.08%
  - Non-Functional Precision: 82.50%
  - Non-Functional Recall: 94.29%
  - F1-Score: 0.8800
  - Confusion Matrix: TN=68, FP=21, FN=6, TP=99
- Classification and SHAP word-level explanation executed on all 6 sample requirements:
  - REQ-001: Functional (54.69%) - 'should', 'when', 'the user', 'account'
  - REQ-002: Functional (69.44%) - 'shall allow', 'allow', 'their'
  - REQ-003: Non-Functional (58.45%) - 'users', 'their', 'using'
  - REQ-004: Non-Functional (67.45%) - 'password', 'at', 'must'
  - REQ-005: Non-Functional (64.43%) - 'password', 'must', 'contain'
  - REQ-006: Functional (77.66%) - 'shall allow', 'allow', 'download'
- SHAP summary plot verified at `docs/figures/shap_summary.png`.

## Known Issues
- None.

## Important Architecture & Technology Decisions
- Default Classifier: TF-IDF (word 1-2 grams, min_df=2, sublinear_tf) + Logistic Regression. CPU-runnable, free, fast, and exactly explainable with SHAP LinearExplainer.
- SHAP LinearExplainer provides word-level attributions in milliseconds, cached per requirement ID.
- Classification data persisted in the `requirements` table.

## Files/Modules Currently Being Worked On
- None (Phase 4 completed).

## Exact Next Step
- Phase 5: Ambiguity detection and readability analysis (rule-based only, no LLM):
  - Subjective/vague terms from `weak_terms.yaml`.
  - Weak modal verbs ("should", "may", "could", "might").
  - Missing measurable criterion.
  - Vague pronoun references.
  - Compound requirements (singularity).
  - Passive voice without actor.
  - Readability metrics via textstat and spaCy.
  - Unified explanation schema.

## Last Verification Performed
- `pytest backend/tests/ -v`: 19 passed in 7.01s on 2026-09-16 15:52:45.
- Sample requirements evaluation verified with word-level SHAP attributions.

## Remote Repository
- **URL**: https://github.com/GoutamNandhen/SRS_Guardian.git
- **Tracking Branch**: `main`
- **Rule**: Automatically commit and push to `origin main` after each phase is completed and verified.

## Metadata
- **Last Updated**: 2026-09-16 15:53:00
- **Last Commit Hash**: Pending Phase 4 commit
