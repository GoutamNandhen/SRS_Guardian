# M38 — Offline, complete independent-review handoff for Werkzeug

## Purpose and limits

This is one practical evidence-delivery step, **not another benchmark gate**.
The historical Pallets Werkzeug issue #2422 and merged fix #2442 form a third,
BSD-3-Clause-licensed, purposively selected held-out **candidate**. The code
downloads only the eight M37 allowlisted pinned source/revision text objects,
checks their Git blob hashes and license, then writes **inert .txt** source copies
plus separate offline reviewer A and B HTML workspaces. No third-party code is
imported, installed or executed. No behavioral conformance is inferred.

The two workspaces are derived from the existing M20 blinded annotation seeds
and reuse M35's editable HTML/export implementation. Each contains six
unlabeled requirement-to-code pairs, four unlabeled revision-specific
behavior cases, all four pinned source files at both revisions, and an offline
source index with line-numbered snippets and upstream permalinks. Internal
M20 selection provenance and source manifest are kept outside reviewer packets.

## Reproduce

From the repository root, using an approved Python 3.11 environment:

    python -m pip install 'pytest==8.4.2'
    python -m pytest -q backend/tests/test_m37_werkzeug_holdout.py backend/tests/test_m38_werkzeug_offline_review.py
    python -m backend.evaluation.m38_werkzeug_offline_review --out-dir /tmp/m38

The output directory must be empty. The generator needs network access to
raw.githubusercontent.com **only to fetch static, pinned source text**.
After generation, both reviewer workspaces and source copies work offline.
GitHub Actions publishes reviewer A, reviewer B, and internal provenance as
**three separate artifacts**. Do not send internal artifacts to reviewers.

## Independent reviewer instructions

Each reviewer opens their own workspace.html and source_index.html in a
modern browser. For each of the six candidate pairs, independently judge
linked/not linked/uncertain, citing exact source lines and reasoning. For each
of the four revision/scenario cases, use approved, version-compatible
independent runtime evidence: revision, environment and dependency versions,
exact input, observed output, run ID and log/artifact reference. Export **both**
JSONL files before closing the page. Do not use upstream bug reports,
post-fix unit tests or static before/after differences as proof of runtime
behavior. The header-parser unit test does not establish multipart behavior.

A separate adjudicator must examine the A/B submissions and evidence,
resolve disagreements, and document exclusions. Do not treat agreement
alone as adjudication. No approved runtime evidence, reviewer submissions,
or adjudications have been received in this run. **All research accuracy,
violation precision, violation recall and coverage metrics remain null.**

## Held-out integrity

Werkzeug is a reserved candidate, not a valid statistically independent
test set by itself. The issue and implementation have already been examined
for evidence construction; do not tune a verifier using this material or
claim that it was prospectively unseen. Freeze a method and project split
before scored evaluation. The final evaluation must use independently
adjudicated project-level held-out examples, per-project denominators,
abstentions, and trace-link evidence. The 95%/95%/90% targets remain unproven.

**Next blocker:** real A/B human submissions, approved before/after runtime
evidence for both scenarios, third-party adjudication, and evaluation of
a frozen verifier on untouched projects.
