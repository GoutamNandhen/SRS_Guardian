# M18 — Project-level negative-link coverage integrity

**Scope:** Evaluation-only safeguard. This does not add new inference, prove model performance, or certify any independent external labels.

## Failure mode fixed

M17 computed project support from only gold-positive requirement-to-code pairs. An evaluator could accept three otherwise excellent projects even if **all unlinked candidate pairs came from only one project**. This left the other projects' false-link behavior unevaluated. A fourth test project containing only unlinked candidate pairs could also disappear from the per-project conformance summary entirely.

## M18 changes

The M5 comparison now enumerates **all projects in the held-out split**, not only projects containing gold-positive links. Each project reports its linked and unlinked candidate-pair counts, conforming and violating label counts, conformance accuracy (null when there are no linked cases), predicted-link coverage, correct rejections of unlinked pairs, false link claims on unlinked pairs, and unlinked rejection rate (null when there are no unlinked cases).

In addition to M17's existing requirements (>=50 linked cases and >=10 of each conformance class per project, macro accuracy >=95%, worst-project accuracy >=90%), M18 requires **>=10 independently adjudicated unlinked candidate pairs per project** before the overall acceptance can pass. A project containing only unlinked pairs fails M17's linked-case support check; a project with enough linked cases but fewer than 10 unlinked cases fails the new M18 gate.

The report distinguishes `m17_conformance_gate_passed` from `m18_negative_link_gate_passed`. If the M17 gate passes but M18 fails, the otherwise passing research acceptance becomes `BLOCKED_BY_M18_PROJECT_LINK_COVERAGE`. Other established M1/M5 acceptance requirements remain unchanged. Unlinked counts are *candidate-pair labels*, not the count of all absent links in the complete codebase; the benchmark sampling design still requires independent review.

## Reproduction

```bash
python -m pytest -q backend/tests/test_m17_project_robustness.py backend/tests/test_m18_project_link_coverage.py
```

The tests use **fabricated mock provenance and test evidence**. The synthetic balanced control exercises a passing arithmetic path; adversarial controls include all 50 negative pairs concentrated in one project, a fourth project containing only negatives, and a project with just nine negatives. None is a real-world accuracy experiment.

## Research limitations and next step

Even when all evaluation gates pass, this software cannot independently authenticate the human annotators, source snapshot digests, test-run artifacts, or whether the candidate-pair sample is representative. Independently verify at least three genuinely distinct, frozen software projects, audit source snapshots and annotation adjudication, and record project-wise coverage and errors before making a 95% accuracy claim. The current M18 change closes an evaluation blind spot, **not a demonstrated model-performance gap**.
