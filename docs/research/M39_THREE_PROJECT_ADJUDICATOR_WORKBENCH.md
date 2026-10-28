# M39 — Three-project offline adjudicator workbench (not gold)

## Bounded implementation

Connect M36's existing independent reviewer reconciliation for EDC and pip with the M38 Werkzeug reviewer exports. Generate one offline, editable **human adjudicator** workbench covering all three real, permissively licensed upstream projects. This is a direct human-review handoff, **not** another accuracy gate, a machine-generated verdict, or a completed independent evaluation.

External sources are already pinned and Git-blob-verified in M28/M29/M37: Eclipse EDC (Apache-2.0), pip (MIT), Werkzeug (BSD-3-Clause). Historical issues, fixes, upstream tests and conditional source models are **not** independently adjudicated behavioral truth.

## Reproduce the pending handoff

Run from the repository root with Python 3.11:

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m36_adjudication_handoff.py backend/tests/test_m39_three_project_adjudicator_workbench.py
python -m backend.evaluation.m35_independent_review_workspace --out-dir /tmp/m39/reviews
python -m backend.evaluation.m38_werkzeug_offline_review --out-dir /tmp/m39/werkzeug_source
mkdir -p /tmp/m39/reviews/werkzeug/reviewers
for r in A B; do
  cp "/tmp/m39/werkzeug_source/reviewer_${r}/link_seed.jsonl" "/tmp/m39/reviews/werkzeug/reviewers/reviewer_${r}.jsonl"
  cp "/tmp/m39/werkzeug_source/reviewer_${r}/behavior_seed.jsonl" "/tmp/m39/reviews/werkzeug/reviewers/behavior_reviewer_${r}.jsonl"
done
python -m backend.evaluation.m39_three_project_adjudicator_workbench --review-root /tmp/m39/reviews --out-dir /tmp/m39/handoff
```

These commands only download and hash-verify pinned external **source text** and execute first-party tooling. They do **not** execute third-party project code. Generated seed files are **blank** and must never be represented as independent human submissions. The resulting `adjudicator_workbench.html` contains 30 pending tasks: EDC 8, pip 12, Werkzeug 10 (16 candidate trace links and 14 revision-specific behavior cases). All research metrics remain null.

## Actual independent review and adjudication

Distribute each project's **separate** M35/M38 browser reviewer workspace to two genuinely independent human reviewers. For each project, collect both exported JSONL files from each reviewer. Place them under `<review-root>/<project>/reviewers/` using the exact names `reviewer_A.jsonl`, `reviewer_B.jsonl`, `behavior_reviewer_A.jsonl`, `behavior_reviewer_B.jsonl`. Do not overwrite real exports with seeds. Preserve original exports and timestamps separately. Keep reviewer A/B work isolated.

For each link judgment, reviewers must cite exact pinned source lines and explain whether the link is justified. For each revision-specific behavior, reviewers must cite approved independent runtime logs or equivalent trusted execution evidence with input fixture, pinned commit, dependencies/environment, and observed result. The historical issue and post-fix upstream test alone do not establish the outcome. A separate human adjudicator inspects both submissions and evidence, resolves disagreements, and explicitly leaves unsupported cases unknown.

Re-run M39 on the **real** exports, open `adjudicator_workbench.html` locally, record a distinct adjudicator identity, verdict, exact source/evidence citation, rationale, and approved runtime record for behavioral cases, then export the JSONL. Reviewer agreement is never automatically adjudicated. Cases with incomplete A/B submissions cannot be finalized in the UI. The exported file is an attributable **proposed human decision record** requiring provenance checks before it may be accepted as ground truth.

## Research limitations and next step

This pipeline currently has **zero** independently adjudicated cases. The three projects were selected and inspected during development; Werkzeug is a reserved candidate, **not a genuinely untouched held-out project**. Do not calculate or advertise conformance accuracy, violation precision/recall or coverage from these blank seeds or static models.

Next, obtain actual independent A/B reviews and a third-party adjudicator, freeze the verifier, then score it on new, previously untouched projects with per-project confusion matrices, abstentions, coverage and confidence intervals. The research targets (accuracy >=95%, precision >=95%, recall >=90%) remain **unverified**. Keep the branch and PR draft; do not merge into main.
