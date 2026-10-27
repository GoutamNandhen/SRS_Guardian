# M33 — Pinned upstream integration-test intent replay (not independent gold)

## Why this is a different evidence step

M28–M32 replay two **reporter-selected** EDC pagination examples. M33 instead reads
the six parameterized inputs and expected-size expression authored in the
**post-fix upstream integration test**, from the pinned Eclipse EDC Connector
revision `bab97cccf4d61a3a380a1d70925b34f4cec1b401`.
The selected Java implementation and integration test are Apache-2.0 licensed.
The existing M28 Git-blob SHA checks cover all six before/after static file
objects (including both LICENSE files); M30 verifies source-expression anchors.
No third-party Java is executed, installed or imported.

Upstream test: [ContractOfferResolverImplIntegrationTest.java](https://github.com/eclipse-edc/Connector/blob/bab97cccf4d61a3a380a1d70925b34f4cec1b401/core/control-plane/contract-core/src/test/java/org/eclipse/edc/connector/contract/offer/ContractOfferResolverImplIntegrationTest.java)

## Concrete conditional results

Two definitions each contain ten distinct assets. The upstream test's
`Range(from,to)` assertion expects `min(to-from,max(0,20-from))`.

| Range | Upstream test expected (not gold) | Before Python abstraction | After Python abstraction |
| --- | ---: | ---: | ---: |
| 0,12 | 12 | 20 | 12 |
| 8,14 | 6 | 8 | 6 |
| 0,999 | 20 | 20 | 20 |
| 4,888 | 16 | 16 | 16 |
| 3,20 | 17 | 17 | 17 |
| 23,25 | 0 | 0 | 0 |

**2/6 conditional pre-fix model predictions disagree** with the upstream
post-fix test intent. **6/6 conditional post-fix predictions agree**. Neither
fraction is conformance accuracy, recall, precision, independent behavioral
verification or a measured Java execution result. These tests were introduced
with the upstream fix and are not independent held-out evidence. No assertion
about actual before/after runtime behavior is justified.

## Reproduce

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m28_historical_pagination_regression.py backend/tests/test_m30_static_pagination_witness.py backend/tests/test_m33_upstream_test_intent_replay.py
python -m backend.evaluation.m33_upstream_test_intent_replay --out-dir /tmp/m33
```

The internal report at `/tmp/m33/internal/test_intent_replay.json` records
pinned source links and conditional predictions. Do **not** give it to
independent reviewers. The `/tmp/m33/reviewers/` packet uses M20 to prepare
12 **unlabeled** requirement-to-code/test pairs and 12 **unanswered**
behavior/revision cases per reviewer, without model predictions or sampling
strata.

## Independent review and missing evidence

Two independent reviewers must (1) decide whether each developer-authored test
assertion is an appropriate behavioral requirement, (2) review 12 M20
requirement-to-implementation/test links with pinned line citations, and
(3) obtain approved, version-compatible runtime or trustworthy archived
execution evidence for all 12 before/after behavioral cases. A separate
adjudicator resolves disagreements. Reviewers must not infer labels from a
merged patch or from this Python model. Cases lacking evidence remain unknown.

These purposively selected upstream regression tests cannot support an
unbiased estimate on held-out projects. A frozen verifier must subsequently be
evaluated on independently labeled, unseen projects, reporting per-project
coverage, abstentions, conformance accuracy, violation precision and recall.
Until then all four research metrics remain NULL; **0 independent adjudications**.

**PR is draft, based on M32, no merge and no change to main.**
