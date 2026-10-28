# M47 — Opt-in pinned Requests client capture for independent reviewers (NOT GOLD)

## Research step

M44 prepared source/license-verified M20 reviewer packets; M45 added a first-party
HTTP 307 fixture. M47 removes the remaining ad-hoc client scripting step by
providing a **single explicitly opt-in, first-party reviewer client** that
checks the requested Git revision and three pinned Git blobs *before* importing
Requests. The client captures a machine-readable response/exception record.
No upstream code is imported or executed in M47 CI, and no human observations
or independent adjudications are claimed.

This is a previously inspected development regression, **not** a held-out
evaluation or an independent conformance benchmark.

## External source and frozen scenario

- Project: psf/requests, Apache-2.0; issue:
  https://github.com/psf/requests/issues/7432
- Fix: https://github.com/psf/requests/pull/7433
- Before: `0b401c76b6e80a4eecf3c690085b2553f6e261ca`
- After: `6404f345e562d962abe6700a1c357ec1e7e18232`
- Three blobs checked per revision: LICENSE, src/requests/models.py,
  tests/test_requests.py. See M44 for immutable hashes and source-line anchors.
- Input: an AttrProxy wrapping BytesIO(b"data"), forwarding methods through
  __getattr__. POST to a loopback /redirect endpoint that returns 307 and
  redirects to /echo. Expected preservation of four bytes is a hypothesis,
  **not a measured result**.

## Safe first-party checks (do not import or execute Requests)

```bash
python -m pytest -q backend/tests/test_m47_requests_approved_reviewer_capture.py
python -m pytest -q backend/tests/test_m45_redirect_observation_fixture.py
```

## Independent reviewer-only protocol (requires explicit approval)

**The following is for two real, separately operating, authorized human
reviewers, not for automated CI or this research agent.** Reviewers must use
separate approved isolated environments with dependencies installed from
reviewed/pinned sources and record their full dependency provenance.

1. Obtain a clean upstream Requests checkout in each environment and detach
   to one of the two commits above. Review the code and approve its execution
   independently. Verify that no tracked or untracked working-tree changes
   exist. Repeat for the other revision in a separate clean checkout.
2. Start M45 fixture with a fresh output path, e.g.:
   `python -m backend.evaluation.m45_redirect_observation_fixture --port 8765 --output /tmp/requests_before_wire.jsonl`
3. From a separate terminal, run the **approved upstream client** only after
   reviewing this first-party capture script:

   ```bash
   python -m backend.evaluation.m47_requests_approved_reviewer_capture \
     --checkout /absolute/path/to/approved/requests-before \
     --revision before \
     --fixture-url http://127.0.0.1:8765/redirect \
     --out /tmp/requests_before_client.json
   ```

4. Stop M45 server using Ctrl+C so that the JSONL observations are written.
   Save the client JSON, its printed SHA-256, the full fixture JSONL and its
   SHA-256, and a signed reviewer note documenting identity, timestamp,
   approval, OS/Python/dependency versions, source checkout and any errors.
5. Repeat steps 2–4 with the **after** revision, fresh output files, and
   `--revision after`. Repeat independently for reviewer B.
6. Both reviewers independently complete the existing M44/M20 link and
   behavioral review packets. An independent third person compares both
   reviewers' signed evidence, checks revision-to-observation correspondence,
   and adjudicates disagreements. Unknown/unsupported cases remain null.

The capture script refuses non-loopback URLs and existing output files.
Its imported Requests module must resolve inside the supplied pinned checkout.
It records *observations only*; it does not generate a conformance verdict,
infer a violation from a historical patch, or calculate research metrics.
Fixture behavior differs from upstream httpbin; independent reviewers must
consider this when interpreting evidence.

## Status and blocker

No reviewer has been recruited or authenticated by this step. No approved
upstream execution, independent labels, adjudication, or held-out evaluation
has occurred. Conformance accuracy, violation precision, violation recall
and coverage remain **undefined**. Do not claim >=95% accuracy, >=95%
violation precision or >=90% violation recall. The next substantive action
is actual independent reviewer execution and adjudication, followed by a
frozen verifier on genuinely untouched external projects.
