# M31 — Two-project source-grounded verification casebook

**Purpose:** demonstrate a single reproducible workflow that traces externally authored behavioral expectations to pinned implementation revisions and separate independent-review packets. This is a *demonstration and annotation handoff*, not an independently measured conformance benchmark.

## One-command demonstration

From the repository root (only our own Python is executed):

~~~bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m28_historical_pagination_regression.py backend/tests/test_m29_pip_historical_regression.py backend/tests/test_m30_static_pagination_witness.py backend/tests/test_m31_two_project_casebook.py
python -m backend.evaluation.m31_two_project_casebook --out-dir /tmp/m31
~~~

Open **/tmp/m31/internal/index.html** to demonstrate the five scenario cards with source URLs, before/after revisions, conditional EDC predictions and unresolved research status. The accompanying machine-readable record is **/tmp/m31/internal/casebook.json**.

Each upstream project has its **own** M20 blinded packet in **/tmp/m31/edc/reviewers/** and **/tmp/m31/pip/reviewers/**. Internal provenance and model predictions are in **/tmp/m31/edc/internal/**, **/tmp/m31/pip/internal/** and **/tmp/m31/internal/**. Do **not** distribute internal material to blinded reviewers.

## Pinned real-world evidence

| Project | Source license | Pinned revisions | Scenarios | M20 link pairs / reviewer | Behavioral revision cases / reviewer |
| --- | --- | --- | ---: | ---: | ---: |
| Eclipse EDC pagination, issue #2493 | Apache-2.0 | Before 3d0bd14d62f2fc29762027e94c5f778c90991228; after bab97cccf4d61a3a380a1d70925b34f4cec1b401 | 2 | 4 | 4 |
| pypa/pip link/extras resolution, issue #12372 | MIT | Before 9685f64fe8c78e1e39cd9b32e5615f42e0a01f1c; after 417ca92b439dba33d707b5da2493358863256bc3 | 3 | 6 | 6 |

Twelve static file/revision objects (six per project) are downloaded from allowlisted pinned commits and verified against expected Git blob SHA-1, with pinned license text checks. This does not audit every dependency's license or establish the provenance of every upstream issue statement.

The EDC casebook includes two **conditional static-model** before/after count predictions from M30; these depend on its explicit five assumptions and do not reproduce Java execution. The pip casebook deliberately provides **no** behavioral predictions. Its two upstream regression tests use fixtures different from the gitlint issue and must not be called exact reproductions.

## What must be independently reviewed

1. Two independent reviewers separately evaluate the ten M20 requirement-to-code/test pairs (four EDC and six pip). Each must record linked/not-linked/uncertain, cited source lines and whether the upstream expectation is a legitimate requirement. These are *candidate* links, not gold.
2. Each reviewer evaluates the ten behavior/revision cases (four EDC and six pip), collecting approved, version-matched execution evidence or trustworthy archived logs, fixture and environment details, exact observed outcomes, source citations, and unresolved assumptions. No third-party code is run by this workflow.
3. A separate adjudicator resolves disagreements and signs a versioned label manifest. The casebook contains **zero** completed adjudications.
4. Only after independently verified labels exist, run a frozen verifier on previously unseen projects, disclose eligible denominators, abstentions, coverage and per-project confusion matrices, and calculate conformance accuracy, violation precision and violation recall. Do not use these purposively selected cases as representative held-out gold.

**Research status:** independently measured conformance accuracy = NULL; violation precision = NULL; violation recall = NULL; conformance coverage = NULL. The >=95%, >=95%, >=90% targets remain unproven. No external Java or pip code is executed, and no upstream reported result is promoted to an independent observation.

## Scope of this milestone

M31 integrates the existing M20, M28, M29 and M30 workflows into a self-contained HTML/JSON research demonstration and separate reviewer handoff. It does not add a new benchmark gate, train a model, change existing model parameters, or alter main. Keep this branch/PR draft and unmerged.
