# SRS Guardian 2.0 — M1 Build Log

- **Scope:** research evaluation infrastructure only; current production analyzers untouched.
- **Primary code:** `backend/evaluation/evaluate_conformance.py` (Python standard library; no heavy ML dependencies).
- **Tests:** `backend/tests/test_evaluate_conformance.py` — 9/9 passed locally on M1 code at authoring time.
- **Fixture:** `backend/evaluation/fixtures/synthetic_gold_dev.jsonl` and `synthetic_predictions_dev.jsonl`, 6 artificial development pairs.
- **Smoke output:** `backend/evaluation/fixtures/synthetic_dev_report.json` — `NOT_ELIGIBLE`, zero evidence-backed decisions, zero conformance accuracy. Correctly prevents a synthetic 95% claim.
- **Frozen baseline reference:** `docs/EVALUATION.md` (old phase-16 numbers; NOT rerun).
- **Unresolved:** Need actual independently labeled requirement↔code benchmark, sample applications, real execution runner, and independent evaluation.
- **Safety:** No runtime model calls, arbitrary code execution, frontend changes, or modifications to production `main`.
- **Next:** M2 code ingestion + candidate linking vertical slice.