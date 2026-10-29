# SRS Guardian 2.0 — evidence-based research stop / independent-review handoff

**Decision date:** 2026-10-29  
**Decision:** MODIFY the research claim. **STOP further retrieval tuning, evaluation gates, and new development milestones until the existing M20 evidence receives independent review.**  
**Scope:** This is a research audit/handoff, **not** an additional benchmark, verifier, ground-truth dataset, or claim of completed independent evaluation.

## Why development should pause

The project has a functioning SRS review application, external source-retrieval experiments, blinded M20 annotation infrastructure, and a narrow real-source static checker. It does **not** yet have independently adjudicated behavioral requirement-to-code labels or a scored untouched project test set. Passing CI and recovering a historical fix file do not establish behavioral conformance.

The current scientifically defensible claim is **feasibility of evidence-grounded source retrieval and restricted static source-property analysis**. A general-purpose or >=95%-accurate requirement-to-code conformance claim is **NO-GO** until independent behavioral evaluation exists.

## Audited repository evidence and precise limitations

The following are linked to existing draft PRs and completed CI runs; **no new experiments were run for this document**. All listed PRs were inspected as draft/unmerged on 2026-10-29. The main branch is not modified by this change.

| Evidence | Reproducible observation | Scientific boundary |
|---|---|---|
| [M20 PR #19](https://github.com/GoutamNandhen/SRS_Guardian/pull/19), [CI #40500278930](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40500278930) | Blinded reviewer A/B candidate-pair workflow; prior first-party regression tests | No submitted independent labels or adjudications established |
| [M42 PR #42](https://github.com/GoutamNandhen/SRS_Guardian/pull/42) | pip repository-wide historical fix-locus retrieval: 2/6 top-5, 0/6 top-1 (reported development proxy) | Correlated inspected cases; not trace-link ground truth |
| [M55 PR #55](https://github.com/GoutamNandhen/SRS_Guardian/pull/55), [CI #40759039678](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40759039678) | SymPy function-level historical changed-file overlap top-5: 0/3 | Three development cases from one project |
| [M57 PR #57](https://github.com/GoutamNandhen/SRS_Guardian/pull/57), [CI #40776393496](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40776393496) | SymPy file-level historical changed-file overlap top-5: 2/3 | Same inspected development cases; not conformance |
| [M58 PR #58](https://github.com/GoutamNandhen/SRS_Guardian/pull/58), [CI #40784044270](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40784044270) | Frozen file-level retrieval transferred to Django: 0/1 historical fix-file overlap top-5; 820 verified production Python files | One inspected cross-project case; not a held-out behavioral result |
| [M59 PR #59](https://github.com/GoutamNandhen/SRS_Guardian/pull/59), [CI #40790778902](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40790778902) | Two-stage blinded Django source/test relevance packets and upstream expected test identifiers | Expectations are not observed outcomes; independent reviews not received |
| [M60 PR #60](https://github.com/GoutamNandhen/SRS_Guardian/pull/60), [CI #40797182378](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40797182378) | Pinned Django before/after static property: violated -> satisfied | Oracle-informed source location/rule; not runtime behavior |
| [M61 PR #61](https://github.com/GoutamNandhen/SRS_Guardian/pull/61), [CI #40803234998](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40803234998) | Whole-tree AST discovery: 820 before / 823 after; same narrow static property; CI success | Symbol and checker are oracle-informed; not blind or held out |

**Fresh checks for this handoff:** GitHub reports M61 CI #40803234998 completed successfully; M59 and M61 GitHub PR review-submission lists were empty. An empty PR review list is not proof about any off-GitHub reviewer activity, but no such independent submissions were supplied to the research workflow.

### Source provenance: concrete Django example

- External requirement/fix context: [Django PR #10097](https://github.com/django/django/pull/10097).
- Before commit: `b9cf764be62e77b4777b3a75ec256f6209a57671`.
- After commit: `cdcf4164bec9dc09465424d7042c3f9d4f0f1fdc`.
- Previously verified `django/core/validators.py` Git blobs: `92394a7eaeadb697481b905332cc6e5af5bd7d33` (before) and `c1c9cd1c87e83564c90493a506da51fef7cea30f` (after).
- Previously verified BSD-3-Clause `LICENSE` Git blob: `5f4f225dd282aa7e4361ec3c2750bbbaaed8ab1f`.
- The M58/M61 pipelines verify source trees and license as inert bytes; no external Django source is imported, installed, or executed.
- Source property: unescaped `:`, `@`, `/` are disallowed in URL userinfo regex character classes. The checker handles a restricted static regex grammar, not general runtime semantics.

Other externally sourced development projects previously used include Eclipse EDC (Apache-2.0), pip (MIT), Werkzeug (BSD-3-Clause), Requests (Apache-2.0), ItsDangerous (BSD-3-Clause), and SymPy (BSD-3-Clause). **Each individual case's pinned license/source provenance must be checked in its own existing evidence manifest before reuse; this summary is not a new license audit.**

## EXACTLY what independent humans must review (not done)

**Stage 1 — two independent, blinded reviewers (A and B):**
1. Receive the existing M59/M20 *stage-1* Django source packets, not the internal oracle-informed M60/M61 witnesses, historical production fix, or stage-2 test patch.
2. Read the original upstream requirement and the complete pinned candidate source excerpts.
3. For each candidate, record relevant / irrelevant / uncertain, cited file and line(s), evidence, uncertainty, and reviewer identity/time. Freeze and timestamp each submission independently before revealing any test/fix hints.

**Stage 2 — same reviewers, after stage-1 freeze:**
4. Receive the separate M59 regression-test evidence; judge whether each expected test actually expresses the stated requirement. Record relevant / irrelevant / uncertain and supporting test identifiers/lines.
5. For any approved behavioral experiment, record *actual* before/after inputs, outputs, pinned revisions, dependencies, environment, source hashes, logs, and observer identity. Upstream FAIL_TO_PASS identifiers alone are **not** observations. External project execution requires separately approved isolated execution and is **not authorized by this handoff**.

**Stage 3 — independent adjudicator:**
6. A distinct third person resolves A/B disagreements using documented criteria and records rationale and final labels. Do not infer adjudication from consensus, historical patches, or model outputs.

**Stage 4 — only after ground truth exists:**
7. Freeze the end-to-end retrieval+verification method, predeclare the target population and project-held-out split, check for issue/project contamination, and score on genuinely untouched projects. Report per-project TP/FP/TN/FN, abstentions, support counts, coverage, accuracy, violation precision/recall, and uncertainty intervals. Distinguish accuracy on all cases from accuracy on non-abstained cases.
8. If labels or observations remain missing, report those metrics as **undefined**, not zero. Never treat synthetic tests, static source diagnostics, or historical changed-file overlap as real-world behavioral labels.

**Existing handoff location:** [M59 CI evidence artifact](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40790778902/artifacts/12861107941) and [M59 draft PR](https://github.com/GoutamNandhen/SRS_Guardian/pull/59). The M61 internal oracle-informed artifact must **not** be shown before blinded stage-1 submissions are frozen.

## Reproduction — existing, not rerun by this docs-only handoff

On the **M61 feature branch** (not necessarily `main`):

```sh
python -m pip install 'pytest==8.4.2' 'pyarrow==17.0.0'
python -m pytest -q backend/tests/test_m57_sympy_file_level_retrieval.py
python -m pytest -q backend/tests/test_m58_django_frozen_file_transfer.py
python -m pytest -q backend/tests/test_m59_django_two_stage_review.py
python -m pytest -q backend/tests/test_m60_django_static_userinfo_verification.py
python -m pytest -q backend/tests/test_m61_django_whole_tree_static_discovery.py
python -m backend.evaluation.m61_django_whole_tree_static_discovery --out-dir /tmp/m61_django_handoff
```

The last command downloads pinned inert upstream bytes; it does not execute external project code. Use a fresh output directory. Prior successful CI runs above are evidence of their own branch revisions, not evidence that this combined command has been executed.

## Research decision and stopping rule

- **GO** for an explicitly limited feasibility-study manuscript describing retrieval, negative transfer results, and a narrow static source-property witness, with honest limitations.
- **NO-GO** for a paper claiming validated behavioral conformance or the target >=95% accuracy, >=95% violation precision, >=90% violation recall. Those metrics remain **undefined**.
- Existing preliminary manuscript: [draft PR #40](https://github.com/GoutamNandhen/SRS_Guardian/pull/40). Update its evidence claims rather than starting another paper or benchmark.
- **Stop now:** new retrieval variants, additional evidence-gate milestones, more reviewer UI, more unscored external cases, and CI-count-driven progress reports.
- **Resume only when:** two independent stage-1/stage-2 reviewer submissions, approved behavioral observation provenance, and a separate adjudicator are available; then conduct one preregistered, bounded pilot and make a GO/NO-GO decision.
- If those people and observations cannot be obtained, finish the feasibility paper with the evidence already available and clearly state the limits. Do not imply that further automation will resolve a human-evidence dependency.

**This handoff itself creates no labels, no new CI, no conformance scores, and no independent ground truth.**
