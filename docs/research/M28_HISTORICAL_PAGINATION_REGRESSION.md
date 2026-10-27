# M28 — Real historical EDC pagination regression candidate (not adjudicated)

## Why this matters

M27's four DSP 2025-1 requirements have no independently verified violating
revisions. This milestone identifies a *real externally reported* historical
bug with a merged fix and an accompanying integration-test change. It creates
a reproducible before/after review opportunity instead of another synthetic
benchmark gate. It is not a validated violation dataset.

## Upstream evidence and rights

- Repository: https://github.com/eclipse-edc/Connector
- Public issue: https://github.com/eclipse-edc/Connector/issues/2493
- Merged fix: https://github.com/eclipse-edc/Connector/pull/2494
- Before: 3d0bd14d62f2fc29762027e94c5f778c90991228
- After: bab97cccf4d61a3a380a1d70925b34f4cec1b401
- LICENSE at both commits: Git blob 2bb9ad240fa04c8cf706a4901c4807878e90c2dc (Apache-2.0).
- Source file: core/control-plane/contract-core/src/main/java/org/eclipse/edc/connector/contract/offer/ContractOfferResolverImpl.java
  - Before Git blob: 60b1698d8556771a4913d01b6bfdeb87dd11f20f
  - After Git blob: d2d21bfa5ff02f5f8f73f6b9325c604355f33d4a
- Integration test: core/control-plane/contract-core/src/test/java/org/eclipse/edc/connector/contract/offer/ContractOfferResolverImplIntegrationTest.java
  - Before Git blob: 145e02b1dc6c386bb9acafb9871a9e915fd531cc
  - After Git blob: 47c5ef30e9647dd8c26e0a56ef38b8b2605bb841

Each of these six revision/path objects is fetched as *static text* and checked
against its expected Git blob hash before creating review evidence. Source files
also carry Apache-2.0 SPDX headers.

## Real-world reported scenarios — not gold

The issue describes two contract definitions with 50 assets each:

| Case | Offset | Limit | Reporter expected | Reporter observed before fix |
| --- | ---: | ---: | ---: | ---: |
| PAG_52_0 | 0 | 52 | 52 offers | 100 offers |
| PAG_2_49 | 49 | 2 | 2 offers | 3 offers |

These observations are attributed to the upstream reporter. They were not
independently reproduced by SRS Guardian. The merged PR adds a parameterized
integration test across two contract definitions but uses a **different
20-asset fixture**; passing that test would not by itself reproduce the
reporter's 100-asset scenarios.

This 2023 contract-offer pagination behavior is distinct from the DSP 2025-1
HTTP Link-header requirement studied in M27. Do not combine their outcomes or
assert protocol-version compatibility.

## Reproduction

Run only our Python metadata and review-generation code:

    python -m pip install 'pytest==8.4.2'
    python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m28_historical_pagination_regression.py
    python -m backend.evaluation.m28_historical_pagination_regression --out-dir /tmp/m28

The generator produces a 2-requirement x 2-code/test M20 candidate queue,
two unanswered link-review files, and two unanswered behavior-review files
covering two cases x two revisions. Reporter-observed counts and sampling
metadata are stored only in the internal evidence packet.

No Java source is imported, built, or executed. No runtime behavior, test
success, or conformance verdict is inferred from a merged PR.

## Exact independent-review work remaining

1. Two independent annotators inspect four requirement-to-code/test pairs,
   recording link/absent/uncertain and cited source lines. A third adjudicates
   disagreements.
2. Independently verify the historical issue's expected outcomes and
   configuration, including the two 50-asset contract definitions.
3. Under separately approved and safe execution conditions, reproduce both
   scenarios on **both pinned revisions** or obtain trusted archived runtime
   logs. Record observed counts, environment, dependencies, and test commands.
4. A third independent adjudicator assigns conformance/violation labels only
   after inspecting the runtime evidence. Missing observations remain null.
5. Repeat on independently selected unseen projects with real behavioral
   requirements, positive and negative outcomes, and transparent denominators.

## Research status

- Six pinned static revision/path objects available for reproducible review.
- Two real bug-report scenarios, four unverified before/after behavior cases.
- Four M20 requirement-to-source/test pairs; two reviewer templates.
- Zero independently adjudicated links or behavioral outcomes.
- Conformance accuracy, violation precision, violation recall, and coverage:
  **NULL**. No ≥95% claim; not a held-out, representative test set.

The historical issue and merged patch are provenance and hypotheses, not an
independent behavioral oracle.
