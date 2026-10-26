# SRS Guardian 2.0 — Milestone M1: Research Evaluation Protocol

**Status:** Implemented evaluator and synthetic smoke tests; **no 95% system result has been achieved or claimed**.  
**Scope:** Python/FastAPI backends, REST endpoints and explicitly testable numeric/boolean/business-rule requirements.  
**Branch:** `feature/srs-guardian2-m1-evaluation-20261026` (does not change `main`).

## A. Research question

Does an evidence-grounded requirement-to-code verification pipeline detect actual requirement violations more reliably than semantic-only traceability or text-only LLM classification, **on unseen software projects**?

The initial system (SRS Guardian 1.x) reviews requirement *text*. SRS Guardian 2.0 will link requirements to candidate code, derive concrete test conditions, execute tests in isolation and attach evidence to each observed result. This milestone only builds the **independent benchmark protocol and scorer**; it does **not** implement retrieval, inference, a test runner or a new user interface.

## B. Frozen existing baseline — from repository docs, NOT rerun here

Source: `docs/EVALUATION.md`, generated **2026-10-05**, using `python -m backend.evaluation.run_evaluation`.

| Task | Reported benchmark | Sample size | Reported result |
|---|---|---:|---:|
| FR/NFR classifier | PROMISE_exp held-out | 194 | **85.05% accuracy, 84.55% macro F1** |
| Ambiguity detection | curated | 40 | **74.42% F1** |
| Duplicate detection | paired benchmark | 36 pairs | **86.67% best F1** |
| Numeric contradiction detection | numeric pairs | 16 | **54.55% F1** |
| Semantic contradiction detection | NLI pairs | 16 | **77.78% F1** |
| Integrated contradiction detection | combined pairs | 32 | **73.17% F1** |

**Inconsistency requiring reconciliation:** `PROJECT_STATE.md` refers to **86.08% test accuracy** for the serialized classifier, while `docs/EVALUATION.md` reports 85.05%. Treat these as different/unreconciled past runs until the training dataset, seed, artifact checksum and exact predictions are reproduced. The 85.05% value is the Phase 16 evaluated baseline cited in our research plan; **it is not a newly measured result**.

The 389-page NASA `nasa-gb-8719.13.pdf` used in load testing is NASA's *Software Safety Guidebook*, not a labeled software specification; it must NOT be treated as ground truth for conformance accuracy.

## C. Benchmark schema

Two line-delimited JSON files are required.

### `gold.jsonl`

One record per **requirement–candidate implementation pair**:

```json
{"case_id":"unique-case-id","split":"test","project_id":"independent-project-A","requirement_id":"REQ-014","requirement_text":"...","candidate_code_ref":"backend/api/payments.py::transfer","source_commit":"40_hex_char_commit_sha","gold_link":true,"gold_conformance":"violates","adjudication_status":"adjudicated","annotation_source":"path/to/independent/review/evidence","dataset_status":"real_adjudicated"}
```

- `gold_link`: true if the candidate implementation is related to the requirement, false otherwise. **Do not** assign a conformance label when `gold_link` is false; use JSON `null`.
- `gold_conformance`: `conforms` or `violates`, based on independently checked testable obligations and the pinned code version; `conforms` means **conforms to the independently specified conditions in this benchmark**, NOT formal proof of arbitrary implementation correctness.
- `split`: `train`, `validation`, `test`, or `dev`. **Every project can appear in only one split**, and exact-normalized requirement text cannot cross splits.
- `dataset_status=synthetic_fixture` is reserved for smoke tests and can NEVER qualify for the 95% gate.
- Test labels must be resolved by reviewers independently from the system's predictions. Record evidence, disagreement resolution, requirements ambiguity and revisions to labels.
- The eligible primary test cohort must be selected using a written supported-scope policy **before** seeing model predictions. Report all excluded/unsupported cases separately.

### `predictions.jsonl`

One record per test candidate:

```json
{"case_id":"unique-case-id","predicted_link":true,"confidence":0.93,"decision":"violates","source_commit":"40_hex_char_commit_sha","candidate_code_ref":"backend/api/payments.py::transfer","evidence_path":"run-123/case-14.json"}
```

Allowed decisions: `conforms`, `violates`, `insufficient_evidence`, `needs_clarification`, `unsupported`. Missing predictions become **abstentions**; they are never deleted from the denominator.

For a final `conforms` or `violates` prediction, the scorer requires a **matching evidence JSON file**, relative to a configured evidence root. The evidence file must include `case_id`, `source_commit`, `candidate_code_ref`, `test_run_id`, `test_case_id`, `expected`, `observed`, `status=completed`, and `result=pass|fail`. Failure must have `failure_type=assertion_mismatch`; crashes and timeouts do not constitute observed violations.

**Critical limitation:** M1 checks the presence and internal consistency of run manifests, **not** that an independent runner truly executed the code. M3 will implement a trustworthy, isolated execution engine and immutable execution provenance. Do not treat hand-edited evidence JSON as experimental ground truth.

## D. Metrics, denominations and ≥95% gate

**Primary endpoint:** strict **full-denominator conformance accuracy**, defined as `correct evidence-backed decisions / all linked, adjudicated test cases`. An abstention, absent prediction, or invalid evidence counts as an error. **Do not** substitute accuracy among decided-only cases.

Secondary endpoints:

- Precision/recall/F1 of *observed requirement violations*, including abstentions as misses in recall.
- Macro F1 for conformant and violated cases; class distribution and confusion table including abstentions.
- Automatic decision coverage (`evidence-backed decided / all eligible cases`).
- 95% Wilson confidence interval for strict accuracy.
- Pairwise requirement-to-code link precision/recall/F1 and link prediction coverage.
- Future M2+: Recall@K, MRR; M3+: test oracle validity, known injected bug detection, runtime/resource cost; M4+: ablations and transfer to unseen projects.

**Release acceptance** (all required; these are target thresholds, NOT current achievements):

| Rule | Gate |
|---|---|
| Dataset | Independently adjudicated, **real** test cohort |
| Projects | **At least 3 held-out projects**; no project overlap with training/validation |
| Conformance sample | **At least 500 linked, labeled** cases |
| Class balance minimum | At least 50 `conforms` and 50 `violates` |
| Link detection negatives | At least 50 unlinked candidate pairs in held-out data |
| Strict accuracy | **≥95%** on ALL eligible linked cases, abstentions included as errors |
| Violation precision | **≥95%** |
| Violation recall | **≥90%** |
| Evidence-backed coverage | **≥70%** (strict 95% accuracy already implies ≥95% coverage) |

**Interpretation:** A tiny dataset cannot pass merely because all examples are correct. A benchmark with no predicted violations cannot pass the violation precision gate. Accuracy and precision must always be reported alongside sample counts, recall and coverage. Even 95% benchmark accuracy is not a guarantee across all software systems.

## E. Run commands

From repository root:

```bash
python -m unittest backend.tests.test_evaluate_conformance -v

# Safe synthetic smoke test: result MUST be NOT_ELIGIBLE
python -m backend.evaluation.evaluate_conformance \
  --gold backend/evaluation/fixtures/synthetic_gold_dev.jsonl \
  --predictions backend/evaluation/fixtures/synthetic_predictions_dev.jsonl \
  --split dev \
  --evidence-root backend/evaluation/fixtures \
  --output docs/research/m1_dev_smoke_report.json

# Real independently labeled benchmark, once acquired:
python -m backend.evaluation.evaluate_conformance \
  --gold data/verification/gold.jsonl \
  --predictions data/verification/predictions.jsonl \
  --split test \
  --evidence-root data/verification/evidence \
  --output docs/research/m1_test_results.json
```

The synthetic gold file uses explicitly fabricated development examples; it is **not a model benchmark**. The scorer reports missing predictions as abstentions, with zero verification claims.

## F. Immediate next milestone: M2 vertical slice

1. Take one explicitly permitted Python/FastAPI repository and pin it to a commit SHA.
2. Implement restricted repository ingestion and Python AST route/function indexing. Do not run uploaded code on the host.
3. Recover candidate links through lexical/semantic retrieval and code-structure evidence. Keep the expected code links hidden from the retrieval method during evaluation.
4. Add reviewer confirmation and data annotation tooling for gold labels.
5. M3: derive boundary-value test oracles for a small supported requirement type, execute in an isolated, offline test environment and record authentic evidence manifests.
6. Compare against lexical-only, semantic-only and execution-grounded baselines on independently labeled unseen projects.

## G. Research integrity checkpoints

- **No accuracy claim without real adjudicated cases and genuine, reproducible execution evidence.**
- No model tuning, threshold selection or prompt editing on the test set. Validation is separate.
- Prevent near-duplicate semantic leakage across project splits, not only exact duplicates.
- Compare on the same cases and compute confidence intervals/statistical uncertainty.
- Mark environment failures `insufficient_evidence`; never report them as code violations.
- Restrict test execution: offline/sandboxed by default, bounded CPU/memory, no secrets, no production credentials, no arbitrary network access.