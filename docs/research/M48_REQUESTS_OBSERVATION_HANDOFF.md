# M48 — Evidence-to-review handoff for Requests #7432 (PENDING, NOT GOLD)

This is a **single bounded workflow improvement**: M47's opt-in human-operated client capture and M45's localhost fixture wire log can now be bundled into a reproducible M44/M20 reviewer-specific evidence attachment. It **does not run Requests**, label behavior, adjudicate, score held-out projects, or create another benchmark gate.

## Reproduce first-party tests

    python -m pytest -q backend/tests/test_m48_requests_observation_handoff.py

After an **approved independent human** has completed the M47 protocol and preserved the client JSON and M45 wire JSONL, prepare an attachment for their existing M44 reviewer packet:

    python -m backend.evaluation.m48_requests_observation_handoff --client /path/to/reviewer_A_before_client.json --wire /path/to/reviewer_A_before_wire.jsonl --reviewer A --out-dir /path/to/reviewer_A_before_evidence

Repeat for each revision and reviewer, using distinct input/output paths. The output contains byte-for-byte copies of both observations and pending_human_review.json with SHA-256 checksums, revision and case binding (REQUESTS_7432_REDIRECT), the wire-event summary and explicit null labels/metrics. Reviewers should reference the raw evidence in their M44 behavior_seed.jsonl / offline workspace and complete M20 link annotations independently. A third independent human adjudicates; the intake tool does not.

**Integrity checks are not authentication.** The tool can verify internal consistency of submitted JSON and pinned provenance fields, but cannot prove the person actually ran the approved upstream code, that the execution was independent, that the environment was trustworthy, or that a behavioral conclusion is correct. The reviewer_supplied field is self-reported. Require reviewer signatures/identity and environment approval out of band. The M45 fixture is not identical to the upstream httpbin environment. If a capture lacks a complete redirect, it may still be a legitimate exception observation, but it is not a violation label.

Source and licensing: [Requests issue #7432](https://github.com/psf/requests/issues/7432), [merged fix #7433](https://github.com/psf/requests/pull/7433); pinned before/after commits and Apache-2.0 Git-blob checks are specified in M44/M47. This case was previously inspected and **is not an untouched held-out project**. No independent reviewer evidence was collected by this PR. All conformance accuracy, violation precision/recall, coverage and held-out performance remain undefined. Do not claim 95% performance.
