# M45 — Controlled, independently operated HTTP 307 behavioral evidence fixture (NOT GOLD)

## Purpose

M44 already supplies two blinded M20 link-review packets and two behavioral revision
cases per reviewer for the Apache-2.0-licensed psf/requests regression
[issue #7432](https://github.com/psf/requests/issues/7432) and
[merged PR #7433](https://github.com/psf/requests/pull/7433).
The remaining bottleneck is independently observed behavior at each exact pinned
revision. M45 adds **a first-party loopback HTTP fixture**, not a new evaluation
gate or a claim of conformance. The fixture is deliberately independent of
Requests: it imports only Python's standard library, never imports or executes
the upstream project, and binds exclusively to 127.0.0.1.

## Frozen scenario and observation

- Requirement: an object that delegates `read` and `tell` to a
  `BytesIO(b"data")` via `__getattr__`, but does not define `__iter__` directly,
  should preserve the POST body across an HTTP 307 redirect.
- The fixture responds to `POST /redirect` with HTTP 307 and
  `Location: /echo`; `POST /echo` responds with a JSON record of the body
  it actually received.
- The fixture records each POST's path, method, body length, SHA-256,
  UTF-8 decoded body and transfer/content-length headers. It accepts
  content-length or chunked request bodies with a 1 MiB cap.
- **Expected wire behavior** is two POSTs, both carrying exactly four bytes
  `data`. This is a proposed expectation, **not an observed result**.
- Upstream source snapshots: before
  `0b401c76b6e80a4eecf3c690085b2553f6e261ca`; after
  `6404f345e562d962abe6700a1c357ec1e7e18232`.
  See M44 for the six independently hash-checked source/license/test Git blobs.
- Source of scenario: the upstream added test
  `test_getattr_proxy_stream_follows_redirect`, with its own httpbin fixture.
  M45's loopback server is **not identical to httpbin**; reviewers must document
  any behavioral differences before treating its observations as corroboration.

## Reproduce first-party fixture without running upstream code

```bash
python -m pytest -q backend/tests/test_m45_redirect_observation_fixture.py
python -m backend.evaluation.m45_redirect_observation_fixture --port 8765 --output /tmp/requests_7432_wire.jsonl
```

The second command starts a local server and saves wire observations on
Ctrl+C. The first command uses only Python standard-library HTTP clients.
Neither command imports or runs Requests.

## Independent human review and approved runtime collection

**Not performed by this automation.** Two independent reviewers, in separately
approved isolated environments, must obtain the two pinned upstream code
snapshots, verify exact commit hashes and license, record Python/dependency
versions, and reproduce the delegated `AttrProxy` stream scenario separately
for each revision. A reviewer-controlled client should POST the proxy body to
the local fixture's `/redirect` endpoint, record response/exception and exact
wire logs, and retain environment and execution provenance. A second trusted
runtime setup (or the original httpbin scenario) should be used to check
fixture-specific effects. Reviewers must not infer success from source text,
the merged PR or a regression test that has not been run.

Each of four reviewer/revision submissions must attach: reviewer identity,
exact upstream commit and code/dependency provenance, approved runner
provenance, timestamp, OS/Python versions, wrapper/client code, request URL,
raw result/exception, full fixture JSONL, fixture SHA-256, any relevant stderr,
and a rationale for `conforms`, `violates`, or `insufficient evidence`.
Leave labels null if evidence is unavailable. A **third independent human**
adjudicates the four submissions and any disagreements in the M20 workflow.
The same reviewers must independently assess M44's two requirement-to-code
candidate links with pinned line citations.

## Limitations and research metrics

This is one previously inspected project and one historical regression; it is
**development evidence, not a held-out benchmark**. Even approved fixture logs
would be observations, not independent adjudication by themselves. No
untrusted upstream code was executed by this automation; no human submissions
or runtime observations were generated. Current independent adjudications: 0.
Conformance accuracy, violation precision/recall and coverage: **not measured**.
Do not claim the >=95% / >=95% / >=90% research targets. After independent
adjudication, freeze the verifier and evaluate untouched external projects.
