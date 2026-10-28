# M34 — Pinned pip source-structural requirement witness (not behavioral gold)

## Bounded contribution

The existing M29 pip regression candidate has a source change but no verifier result. M34 adds a **first-party AST-only source-path witness** for pip's `Factory._make_requirements_from_install_req`. It examines the exact pinned before/after MIT-licensed resolver code and verifies the structure of the link-plus-extras success path. It does **not** import, install or execute upstream pip.

Under the explicit **syntactic path assumptions** that requirement markers match, a link is present, extras are nonempty and candidate creation succeeds, the before-fix source has **one successful requirement-yield site** (an extras-bearing link candidate); the after-fix source has **two** (a base link candidate built with extras removed, plus an extras candidate yielded under `if ireq.extras`). These are source-level AST observations, **not observed runtime yields, resolution success, violation labels or measured conformance accuracy**.

## Provenance

Source repository: https://github.com/pypa/pip (MIT `LICENSE.txt` at both pinned revisions). Issue https://github.com/pypa/pip/issues/12372; merged fix https://github.com/pypa/pip/pull/12392. Before `9685f64fe8c78e1e39cd9b32e5615f42e0a01f1c`, after `417ca92b439dba33d707b5da2493358863256bc3`. M29 verifies six pinned file/revision objects by Git blob hash, the MIT license, and the changed resolver and test sources. M34 fails closed if the AST control flow or expected expressions differ, and records source-line URLs for each observation.

## Reproduce (first-party Python only)

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m29_pip_historical_regression.py backend/tests/test_m34_pip_source_structure_witness.py
python -m backend.evaluation.m34_pip_source_structure_witness --out-dir /tmp/m34
```

The internal `m34_source_structure.json` contains the source-level observations and explicit null research metrics. The M20 `reviewers/` packet contains **six unlabeled requirement-to-code/test pairs and six pending behavior/revision cases per reviewer**. Do not disclose internal source-structure predictions or M20 sampling provenance to blinded reviewers.

## Exact independent-review blocker

Two independent annotators must verify the legitimacy of each of the three pip behavior requirements, inspect all six trace links, and independently assess each of the six revision/scenario outcomes from approved version-matched runtime evidence or trustworthy archived logs. The reporter's gitlint scenario is **not identical** to the two upstream wheel-fixture tests. A separate adjudicator resolves disagreements. Until then all behavioral conformance and violation labels remain null. Finally freeze the verifier and measure conformance accuracy, violation precision/recall and transparent coverage on independently adjudicated unseen projects, with per-project denominators. This historical candidate is not a held-out benchmark.

**No external project code executed. No fabricated scores. No merge into main.**
