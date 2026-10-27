# M30 — Source-grounded pagination counterexample (not gold)

This milestone reuses the pinned, hash-verified Apache-2.0 Eclipse EDC historical regression from M28 (issue #2493, fix #2494). It adds a **static, explicit abstraction** of the pre-fix and post-fix `queryContractOffers` method, bound to the exact pinned Git blobs and 12 source-expression anchors. No third-party Java code is executed.

## Conditional model outputs

Assume two contract definitions, 50 matching assets each, one offer per asset, no filtering or policy failures, and correct per-definition offset/limit semantics:

| Offset | Limit | Reporter expected | Pre-fix static model | Post-fix static model |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 52 | 52 | 100 | 52 |
| 49 | 2 | 2 | 3 | 2 |

The pre-fix code uses `numSeenAssets` and a per-definition `limit` without tracking offers already fetched. The post-fix code uses `numFetchedAssets`, `dynamicOffset`, and `dynamicLimit`. These conditional outputs reproduce the **reported** anomaly but do not verify that it occurred at runtime. They are not observed measurements, independently adjudicated labels, or conformance accuracy.

## Reproduce without executing upstream code

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m28_historical_pagination_regression.py backend/tests/test_m30_static_pagination_witness.py
python -m backend.evaluation.m30_static_pagination_witness --out-dir /tmp/m30
```

The last command downloads only M28's six allowlisted pinned static text objects, verifies Git blob SHA-1 and license, then creates two separated artifacts: `reviewers/` contains unanswered M20 link and behavior/revision forms; `internal/` contains source anchors, model traces, assumptions, and reporter comparisons. Model predictions must not be shown to blinded reviewers.

## Precisely what independent reviewers must do

Two reviewers independently check the source-to-requirement links, whether each stated behavior is an appropriate requirement, and whether the five model assumptions hold for each revision. For each of two scenarios on both revisions, they must inspect the pinned source, obtain approved version-compatible runtime evidence or trustworthy archived execution logs, and record observed offer counts, complete configuration, source-line citations, and uncertainty. A third adjudicator resolves disagreements. Do not infer behavior from merged fixes or from this model. Never label cases without evidence.

**Measured research metrics:** conformance accuracy = NULL, violation precision = NULL, violation recall = NULL, coverage = NULL. Zero independently adjudicated cases. This is a selected historical regression, not an unseen representative held-out test project. The next research step is approved independent reproduction and cross-project held-out evaluation (including the separate pip M29 candidate).
