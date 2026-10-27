# M19 — Prevent negative-link abstention from inflating research acceptance

**Scope:** Evaluation-integrity improvement only. It does not change inference, measure model improvement, or validate independent real-world data.

## Why M18 was insufficient

M18 requires at least 10 adjudicated negative candidate links in each held-out project, but did not require the evaluated system to **make a negative-link decision** on those examples. A method could abstain on every negative in one project while reporting perfect pooled link precision/recall and perfect conformance accuracy. Another method could assert a false link for all 20 negatives in one project, yet keep pooled precision above 95% thanks to 500 correctly linked cases.

## M19 policy

The comparison evaluator now records per-project **unlinked decision coverage**, **unlinked abstentions**, and **unlinked correct rejection rate**. Missing predictions and explicit null link predictions count as abstentions, never as correct rejections. It requires **at least 95% link-decision coverage on gold-negative candidates** and **at least 90% correct rejection of gold-negative candidates**, separately for every held-out project, in addition to M1–M18 requirements. A zero-negative project fails the existing M18 support gate.

The acceptance result exposes `m19_project_negative_link_performance_passed` and, when M1–M18 would otherwise pass, `BLOCKED_BY_M19_PROJECT_NEGATIVE_LINK_PERFORMANCE`. Existing support gates remain separate so blocked results retain their primary cause. These thresholds are a conservative **project-level research policy**, not measured model performance.

**Caution:** The rejection denominator is the annotated candidate-pair sample, not every possible missing code link. Biased negative sampling can still inflate results. Independent adjudication, frozen source revisions, representative sampling, and provenance review remain necessary.

## Reproduce

```bash
python -m pytest -q backend/tests/test_m17_project_robustness.py backend/tests/test_m18_project_link_coverage.py backend/tests/test_m19_negative_link_performance.py
```

The new tests create mock provenance and synthetic evidence. One adversarial case abstains on all 20 negative pairs of one project; another falsely claims all 20 links. Both retain perfect 500/500 conformance accuracy; pooled link precision is respectively 100% and approximately 96.15%. M19 must block both. A balanced all-reject control must continue passing **only as synthetic arithmetic**.

## Actual data acquisition priorities

Existing Dronology M6–M7 observed-positive trace links cover only one project and cannot measure conformance or negative-link precision. For a *separate* trace-link-only validation, investigate published iTrust, eTour and related traceability datasets and their licenses/snapshot integrity (for example the fine-grained traceability artifact at https://github.com/tobhey/finegrained-traceability). These are **not** conformance-violation ground truth. NIST SARD (https://samate.nist.gov/SARD/) has labeled weakness cases, but its security weakness labels cannot be silently substituted for SRS-to-code conformance judgments. Do not claim 95% until independently adjudicated project-specific requirement/code/test evidence exists.
