# M36 — Independent reviewer-to-adjudicator handoff

## Bounded contribution

Reconcile two independent M35 reviewer JSONL exports per project into an evidence-preserving adjudication queue. This is a **human-review workflow step**, not another benchmark gate. No automatic adjudication, external code execution, synthetic-as-real claims or research accuracy.

## Reproduce

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m36_adjudication_handoff.py
python -m backend.evaluation.m35_independent_review_workspace --out-dir /tmp/m35
python -m backend.evaluation.m36_adjudication_handoff --review-root /tmp/m35 --out-dir /tmp/m36
```

The M35 command creates **blank reviewer seeds**, not human responses. The M36 output in this example contains **20 pending tasks, 0 adjudications and null metrics**. For actual review, distribute only the corresponding M35 reviewer-specific workspace to each of two genuinely independent human reviewers. Each exports two JSONL files. Preserve their original exports, and put the four files per project at `edc/reviewers/{reviewer_A,reviewer_B,behavior_reviewer_A,behavior_reviewer_B}.jsonl` and similarly for `pip`. Never overwrite real submissions with blank seeds.

M36 verifies A/B case identity and immutable fields, distinguishes incomplete submissions from evidence-backed agreement/disagreement, and writes `adjudication_queue.jsonl`, `ADJUDICATOR_HANDOFF.md` and `adjudication_manifest.json`. **Reviewer agreement is never automatically promoted to ground truth**: all adjudicated labels remain null. A *separate human adjudicator* must inspect requirement authority, exact source lines, version-compatible runtime observations, fixture/environment and evidence, then record an attributable decision and rationale. Cases without sufficient evidence remain unknown. Do not share reconciliation outputs with blinded reviewers.

## Research limitations

The two known historical bug projects (Eclipse EDC, Apache-2.0; pip, MIT) are **purposively selected development examples**, not a representative held-out test. The generated 20 tasks comprise 10 candidate requirement-to-code links and 10 revision-specific behavior cases, across both projects, not 20 independent projects. This step does not measure conformance accuracy, violation precision/recall or coverage. Freeze the verifier before evaluating new, unseen, independently adjudicated projects; report confusion matrices, eligible cases, abstentions and coverage per project. External Java/pip code is not imported, built or executed. Keep the PR draft and unmerged; main unchanged.
