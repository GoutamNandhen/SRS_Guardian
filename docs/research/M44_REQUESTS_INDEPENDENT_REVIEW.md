# M44 — Requests #7432: fourth external source-grounded review candidate (NOT GOLD)

## Why this step matters

M40–M43 exercised a previously inspected pip regression and did not produce independently
adjudicated behavioral labels. M44 adds a **different, externally authored** requirement
and an upstream issue→merged fix→regression-test chain, without introducing another
verifier, benchmark gate, or reviewer interface. It reuses the existing M20 blinded
annotation queue and M35 offline reviewer UI. This is **not** a scored held-out result:
the regression and patch were examined during candidate selection. Reserve this
project for later evaluation; do not tune the verifier on it.

## Verified upstream source and licensing

- Project: psf/requests; Apache License 2.0 verified from immutable LICENSE files.
- Reporter issue: https://github.com/psf/requests/issues/7432
- Merged PR: https://github.com/psf/requests/pull/7433
- Before commit: 0b401c76b6e80a4eecf3c690085b2553f6e261ca
- After merge commit: 6404f345e562d962abe6700a1c357ec1e7e18232
- LICENSE blob SHA1 at both revisions: 67db8588217f266eb561f75fae738656325deac9
- Source before: src/requests/models.py, Git blob 4142f2a4bbf39820b46b414a15af805a34b1a013
- Source after: src/requests/models.py, Git blob 57e114866da042a866dced7a2f55a8a7da597878
- Tests before: tests/test_requests.py, Git blob 09cd4a388a760ad7d757afe0b9560e486ea4b7c9
- Tests after: tests/test_requests.py, Git blob 571535fe7998dcc7a747266f4461f96fcea3c2d3

All six source/revision objects are fetched as inert bytes and Git-blob-hash checked.
Source inspection anchors are:
[before detection](https://github.com/psf/requests/blob/0b401c76b6e80a4eecf3c690085b2553f6e261ca/src/requests/models.py#L599),
[after detection](https://github.com/psf/requests/blob/6404f345e562d962abe6700a1c357ec1e7e18232/src/requests/models.py#L600),
and [added upstream test](https://github.com/psf/requests/blob/6404f345e562d962abe6700a1c357ec1e7e18232/tests/test_requests.py#L2076).

The reporter expects a delegated file-like stream's request body to survive a 307
redirect. The merged source adds a fallback hasattr check and the upstream PR
adds a test. **Neither is independent proof of behavior at either revision.**

## Reproduce

Run first-party code only, without installing/importing/running upstream Requests:

    python -m pip install 'pytest==8.4.2'
    python -m pytest -q backend/tests/test_m44_requests_independent_review.py
    python -m backend.evaluation.m44_requests_independent_review --out-dir /tmp/m44

Output includes an internal source/provenance manifest and **two independent,
offline reviewer packages**. Each reviewer receives **two unlabeled M20 trace
pairs and two unlabeled revision-specific behavioral cases**, source text,
and the existing M35 browser UI. All fields are pending/null; no labels,
adjudication, behavioral accuracy, precision, recall, or coverage are inferred.

## Exact independent review blocker

1. Two different humans independently assess the two requirement-to-code
   candidates against pinned source lines, preserving their original exports.
2. For each before/after behavior case, collect **approved independent
   execution observations** with exact commit, Python/dependency versions,
   input wrapper, redirect response, request body received, output/exception,
   logs and execution provenance. Do not execute untrusted upstream code in
   this research automation. If no trusted runtime evidence is available,
   mark the behavioral case unknown.
3. A third independent adjudicator records supported labels and disagreements.
4. Freeze the verifier before evaluating genuinely untouched projects. Report
   per-project confusion matrices, abstentions, coverage and confidence
   intervals. Do not include these pre-inspected projects as untouched held-out.

**Current:** 0 independent reviewer submissions, 0 adjudications, 0 trusted
runtime observations, 0 held-out scored cases. All conformance accuracy,
violation precision, violation recall and coverage values are **not measured**.
The >=95% / >=95% / >=90% targets remain unproven.

This is a new evidence candidate, not a research-grade validation result.
