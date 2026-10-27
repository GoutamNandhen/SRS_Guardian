# M29 — Independent pip resolver regression candidate (not adjudicated gold)

## High-impact research evidence

This is a **second independent software project** after M28's Eclipse Dataspace Connector, not another retrieval-only safeguard. The upstream pip issue [#12372](https://github.com/pypa/pip/issues/12372) describes a real local-package dependency resolution regression; the merged fix [#12392](https://github.com/pypa/pip/pull/12392) modifies the resolver and adds two functional regression tests. These are historical evidence and candidate behavioral requirements, **not independently reproduced outcomes**.

## Immutable upstream source and licensing

- Project: https://github.com/pypa/pip (MIT license; `LICENSE.txt` Git blob `8e7b65eaf628360e6f32f4140fcdd7ec7c2b7077` at both revisions).
- Before: `9685f64fe8c78e1e39cd9b32e5615f42e0a01f1c` (upstream PR base).
- After: `417ca92b439dba33d707b5da2493358863256bc3` (upstream merge commit).
- Resolver: `src/pip/_internal/resolution/resolvelib/factory.py`, before Git blob `38c199448a18a5dd6c2211384bf752eff819b5a8`, after `4adeb4309ce42ee0f6c428ae6cde11bde4a2e0d1`.
- Functional tests: `tests/functional/test_new_resolver.py`, before Git blob `b5945edf89b0de0d8499972586380fa31391b32a`, after `3ff3f9425c202cb17a8a07eafca1971948d3bf72`.
- **6 revision/path objects** (5 distinct Git blobs) are fetched only as static text and checked against their pinned Git blob hashes. MIT covers pip repository code; the gitlint example and any transitive third-party dependencies have **not** been audited or downloaded.

## Three reviewable behavioral cases, not three observed failures

| Case | Source | Expected behavior | Known outcome |
| --- | --- | --- | --- |
| PIP_ISSUE_12372 | Upstream reporter | Installing local gitlint plus gitlint-core with extra should resolve | Reporter alleges pip 23.3.1 fails; not independently reproduced |
| PIP_DIRECT_LINK_EXTRA | Added upstream test | Local pkg 1.0 wheel with extra and compatible constraint should install | Test source asserts success; no independent execution |
| PIP_INDIRECT_LINK_EXTRA | Added upstream test | Local pkg2 depending on pkg1[ext] plus explicit pkg1[ext] should install | Test source asserts success; no independent execution |

The two new wheel-fixture tests are **not** exact reproductions of the reporter's gitlint environment. They are developer-authored regression test intentions. Their presence in the merged patch is not an independent PASS, and there is no independently established before/after negative or positive label.

## Reproduce without executing upstream code

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m29_pip_historical_regression.py
python -m backend.evaluation.m29_pip_historical_regression --out-dir /tmp/m29
```

The evidence generator only fetches pinned static text, checks hashes and source anchors, and uses M20 to create **3 requirement descriptions × 2 source/test targets = 6 pending link-review pairs**. Two blinded reviewer files and two separate behavior-review files are generated, each behavior file containing **3 scenarios × 2 revisions = 6 pending cases**. Internal upstream allegations and M20 selection origins are excluded from the blinded reviewer package. CI uploads the two packages separately.

## Exact work for independent annotators

1. Two independent reviewers inspect **all six** M20 requirement-to-source/test pairs, cite pinned source lines, and label linked/not-linked/uncertain. A third adjudicates disagreements.
2. Independently verify whether each expected behavior is a legitimate requirement and record its provenance; explicitly distinguish the original gitlint scenario from the two wheel-fixture tests.
3. In an independently approved, isolated environment, reproduce the three scenarios on **both pinned revisions**, or inspect trustworthy archived version-specific execution evidence. Record complete environment, dependency versions, commands, observed installation outcomes and logs. **Do not run external pip or gitlint source in this workflow.**
4. Two independent reviewers assess each of the six revision/scenario behavior cases, and a third adjudicates disagreements. Unsupported outcomes remain null.
5. Evaluate a **separately selected, untouched, representative project-level holdout**, with both conforming and violating cases and explicit per-project denominators. The current two historical defect projects are development evidence, not a statistically representative held-out test set.

## Research status

- Pinned external projects with historical regression candidates: **2 total** (EDC M28 and pip M29).
- New M29 project: 6 pinned file/revision objects; 3 behavioral scenarios; 6 pending M20 links; 6 pending behavior cases per reviewer.
- Independent M29 labels: **0**. No external source code executed.
- Conformance accuracy, violation precision, violation recall, conformance coverage: **NULL**.
- ≥95% conformance accuracy, ≥95% violation precision, ≥90% violation recall: **NOT ESTABLISHED**.
- Do not merge this draft PR; main remains untouched.
