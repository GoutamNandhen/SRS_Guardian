# M37 — Reserve a third real-world regression for independent held-out review

**Scope:** One bounded acquisition and annotation handoff. **No accuracy result, no inferred gold, no third-party code execution.** This is a new project not used in M28–M36 development demonstrations; it is reserved as a **held-out candidate**, not yet a valid held-out test set. Do not tune any verifier against its source, tests, predictions, or reviewer decisions. Freeze a verifier and the split before any scored evaluation.

## Upstream provenance verified

- Project: [Pallets Werkzeug](https://github.com/pallets/werkzeug), permissive **BSD-3-Clause** license. The pinned [LICENSE.rst](https://github.com/pallets/werkzeug/blob/f488ea16cd2f9b81cf4602c257e7963421b40156/LICENSE.rst) contains all three redistribution/non-endorsement conditions and the disclaimer.
- Reporter requirement: [issue #2422](https://github.com/pallets/werkzeug/issues/2422), opened 2022-05-29. It alleges that multipart `fileName` is treated as a form field instead of a file. The reporter references RFC 6266; this is **not** an independent normative interpretation or runtime verification.
- Merged fix: [PR #2442](https://github.com/pallets/werkzeug/pull/2442), merge commit `f488ea16cd2f9b81cf4602c257e7963421b40156`, first parent `446afc9dc21b786531b1171d14ca31adf4f084a3`.
- Pinned implementation: [before parser](https://github.com/pallets/werkzeug/blob/446afc9dc21b786531b1171d14ca31adf4f084a3/src/werkzeug/http.py#L443) uses `unquote_header_value(option)`; [after parser](https://github.com/pallets/werkzeug/blob/f488ea16cd2f9b81cf4602c257e7963421b40156/src/werkzeug/http.py#L446) adds `.lower()`.
- Pinned caller: [multipart decoder](https://github.com/pallets/werkzeug/blob/f488ea16cd2f9b81cf4602c257e7963421b40156/src/werkzeug/sansio/multipart.py#L180) uses `extra.get("filename")`, unchanged between revisions.
- Upstream post-fix [unit test](https://github.com/pallets/werkzeug/blob/f488ea16cd2f9b81cf4602c257e7963421b40156/tests/test_http.py#L361) checks that `fileName` is parsed as `filename`. This is **not** an end-to-end multipart execution record.

The program pins and verifies **8 file/revision objects** (license, parser, multipart caller and unit tests at both revisions) by exact Git blob SHA-1, records each file's SHA-256, and rejects mismatches. Six unique blobs are expected because the license and caller are unchanged. These hashes attest to immutable Git content, not to independent correctness.

## Reproduce (static text acquisition only)

From repository root:

```sh
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m37_werkzeug_holdout.py
python -m backend.evaluation.m37_werkzeug_holdout --out-dir /tmp/m37
```

The CLI downloads **only four allowlisted text paths at two immutable commits**. It never imports, installs, or executes Werkzeug. Internet access to raw.githubusercontent.com is needed for fetching the pinned text. No other external hosts are contacted by the acquisition script.

The **internal** directory contains verified source provenance and the M20 sampling manifest (including selection origins). The **reviewers** directory contains a separate blinded M20 queue, reviewer A/B link seeds, and two revision-specific behavioral seeds per scenario. Never send internal selection provenance to reviewers.

## Exact independent review workload

Each of **two independent reviewers** must assess **6 requirement-to-code candidate pairs** (2 reporter-derived requirements × 3 source/test symbols) and **4 behavioral cases** (2 scenarios × before/after). The two behavior questions are (1) mixed-case `fileName` parsing and (2) whether the multipart consumer classifies a file correctly. The latter must not be inferred from the unit test of the former.

For every link, provide a pinned source-line citation and an explicit linked/not-linked/uncertain decision. For every behavior, provide approved version-compatible runtime logs or equivalent independent execution evidence with revision, environment, input and observed output. A separate human adjudicator must resolve decisions, with unresolved cases excluded transparently. Do not infer violations from pre-fix source or conformance from merged post-fix tests.

**Not yet done:** independent reviewer submissions (0), adjudications (0), frozen-verifier evaluation (0), independently measured conformance accuracy/violation precision/recall/coverage (all null). This historical case is purposively selected, so even after adjudication it cannot alone support generalization or a 95% population-level claim. Use an untouched project-level split, report per-project denominators and abstentions, and preserve all individual reviewer records.

**Next blocker:** obtain real independent A/B reviews and approved before/after execution evidence. Do not add more benchmark gates until that happens.
