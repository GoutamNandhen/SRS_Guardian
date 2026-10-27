# M17 — Project-balanced generalization gate for SRS-to-code research

**Scope:** Evaluation safeguard only; no change to inference, retrieval, or measured real-world accuracy.

## Problem

A pooled 95% or 98% accuracy score can conceal a failure on one independent project. M1 previously required at least three project IDs but did not require sufficient labeled test cases in **each** project. For example, 490 perfect cases from one project and five cases each from two others satisfy the nominal 500-case/three-project gate, despite inadequate evidence of generalization to the smaller projects.

Likewise, 225 correct cases from each of two projects plus 40/50 correct cases from a third yields 490/500 = **98% pooled accuracy** while the third project achieves only **80%**. The 98% result is not an adequate cross-project claim.

## M17 change

M5 now reports `project_robustness` for each compared system, including each project's linked-case count, conformance class counts, full-denominator accuracy, macro project accuracy, and worst-project accuracy.

For an otherwise M1- and M5-eligible acceptance, the **additional M17 gate** requires:

- At least **50 linked, adjudicated test cases per project**.
- At least **10 conforming and 10 violating labeled cases per project**.
- **Project-macro full-denominator accuracy ≥95%** (each project receives equal weight).
- **Worst-project full-denominator accuracy ≥90%**.

Any failing condition changes an otherwise-passing research acceptance to `BLOCKED_BY_M17_PROJECT_ROBUSTNESS`. Existing M1 global thresholds remain unchanged. M17 does not relax provenance, link precision/recall, violation precision/recall, or coverage.

## Verification

`python -m pytest -q backend/tests/test_m17_project_robustness.py`

The three adversarial tests use **entirely fabricated** metadata, source digests, predictions, and evidence to test arithmetic. Their mock `real_adjudicated` labels are **not real**; a mock `PASSED` from the evaluator is never a publishable result. The M17 CI also runs the M1–M17 research regression, trusted restricted-Docker tests, and Next.js production build.

## Remaining research blockers

No independent multi-project adjudicated conformance benchmark is available in this repository. Project IDs and claimed source SHA-256 strings are not proof of independent codebases. The M5 audit checks for obvious leakage, but cannot independently verify source authenticity, human annotation, or execution provenance. Before reporting ≥95%, obtain and freeze an external project-level test set, audit the annotation and source snapshots, and report project-level confidence intervals and coverage. M17 is a conservative guard against pooled-score domination, **not evidence of improved model performance**.
