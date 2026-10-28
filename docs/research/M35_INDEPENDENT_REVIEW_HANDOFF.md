# M35 — Independent annotation handoff (two external projects)

## Bounded contribution

This is an **actual human-review interface**, not another benchmark gate. A single
first-party command generates four **separate, offline, browser-editable workspaces**:
Eclipse EDC (Apache-2.0) reviewer A/B and pip (MIT) reviewer A/B. The workflow
reuses the M31 pinned, Git-blob-verified upstream source, revision and license
evidence, and the M20 unlabeled candidate queue. It never imports, builds or
executes external Java/pip code.

Run:

\`\`\`bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m28_historical_pagination_regression.py backend/tests/test_m29_pip_historical_regression.py backend/tests/test_m30_static_pagination_witness.py backend/tests/test_m31_two_project_casebook.py backend/tests/test_m35_independent_review_workspace.py
python -m backend.evaluation.m35_independent_review_workspace --out-dir /tmp/m35
\`\`\`

The four reviewer-specific HTML files are in
\`/tmp/m35/{edc,pip}/reviewers/workspace_reviewer_{A,B}.html\`.
Open the appropriate HTML file locally. Reviewers can record link judgments
with source-line reasoning and revision-specific behavioral verdicts with
independent observations, evidence citation, fixture/environment and notes.
Export both JSONL files for later third-party adjudication. The UI permits
unanswered cases, retains null labels, and does not transmit annotations.

**Give each reviewer only their own project's artifact**. Never give reviewers
\`/tmp/m35/internal\`, source-model predictions, M20 sampling provenance, the
other reviewer's file, or an upstream issue's alleged failure as an answer key.

## Exact pending human work

Each reviewer independently assesses:
- Eclipse EDC: **4 requirement-to-code/test pairs** and **4 revision/behavior cases**.
- pip: **6 requirement-to-code/test pairs** and **6 revision/behavior cases**.

Each of two reviewers must verify the requirement's authority, trace links
against pinned source lines, whether each expectation applies to each revision,
and behavioral observations from approved version-matched execution or trustworthy
archived logs. Record environment, fixtures and exact evidence reference.
Historical reports and developer-written regression tests are **not gold**.
A separate adjudicator resolves reviewer disagreement; unknowns stay unknown.

This yields 4 HTML workspaces, **20 link decisions and 20 behavior decisions
across both reviewers** if all are eventually completed. At generation, **all
20 + 20 decisions are pending**; independent adjudications are **zero**.

## Research limits

These two projects were deliberately selected from known bugs, not sampled as
representative unseen held-out projects. The HTML workspaces are annotation
capture tools, not a behavioral verifier or a claim of independently verified
runtime outcomes. All four metrics (conformance accuracy, violation precision,
violation recall, coverage) remain **null**. Once two reviewers and a third
adjudicator complete the evidence, freeze the verifier, collect independent
held-out projects with genuine positive and negative labels, and report each
project's numerator, denominator, abstentions and coverage. Do not count
historical casebook/model agreement as real-world accuracy.

Main remains untouched; do not merge this draft PR.
