# SRS Guardian 2.0 — M3 Controlled Executable Verification

**Milestone status:** implemented as a **trusted-app executable demo**, not a production executor for uploaded repositories.

## Capabilities implemented

- Conservative parsing of one supported rule family: mandatory rejection of individual transfers above a single integer threshold.
- Explicit reviewer approval of an endpoint-specific oracle: JSON response field accepted must be false for above-limit transfer amounts.
- N+1 and a second above-limit test. No claim that a transfer at or below the threshold must be approved.
- Real HTTP request/response execution using in-process httpx ASGITransport against two pre-installed FastAPI fixtures: one conforming, one deliberately faulty.
- Observations include request inputs, expected boolean, actual boolean, HTTP status, partial response, test-level result, target revision label and a SHA-256 integrity checksum.
- Conservative outcomes: observed_violation; passed_available_checks; insufficient_evidence; unsupported preview -> needs_human_clarification.
- Backend API routes: POST /api/conformance/preview, POST /api/conformance/demo/run, GET /api/conformance/targets.
- Frontend Verification page linked from the sidebar, with SRS requirement selection, reviewed oracle checkbox and downloadable JSON evidence.
- Optional library-level verify_approved_asgi_app for explicit developer-provisioned, **trusted** ASGI application objects. No arbitrary URLs or uploaded code.

## Safety and research limitations

1. The M2 ZIP archive remains **AST-indexed only**. Neither the public API nor the demo ever executes its source code.
2. The ASGI fixture is synthetic. The current milestone does **not** verify code in a user's uploaded repository or cryptographically link M2 candidates to runtime code.
3. In-process ASGI testing does **not** sandbox an untrusted app. For real customer code, build an isolated worker with authentication, network/FS restrictions, secrets protections, and resource limits.
4. The parser supports only one narrow numeric business-rule family. Ambiguous, conditional, unsupported and multi-value statements must abstain; general natural-language interpretation remains an open research task.
5. Approval of an expected boolean is essential: HTTP status 4xx by itself cannot establish that a business operation was rejected.
6. Passing a finite number of supported tests is not proof of full correctness or full SRS compliance.
7. The evidence hash is an integrity checksum over returned JSON, not a cryptographically signed software attestation.
8. Existing SRS Guardian deployment lacks independent app authentication; do not expose source indexes or verifier through an unprotected internet server.
9. No claim of 95% accuracy is justified by fixed synthetic fixtures. Independent labeled cross-project testing is still required.
10. The isolated M1+M2+M3 tests were run locally. Full legacy-backend regression and a full Next.js production build in the complete repository have not yet been run.

## Verification commands

From the repository root:

    python -m pytest backend/tests/test_evaluate_conformance.py backend/tests/test_code_traceability.py backend/tests/test_conformance_verification.py -q

Start existing backend (with required dependencies such as httpx installed) and frontend, then open Verification in the sidebar. Preview the provided sample requirement, approve the oracle, and select faulty or correct trusted demo target. Download JSON observations.

## Next gate — transition from synthetic to real evidence

- Provide operator-approved FastAPI applications inside a hardened external test worker; never execute ZIPs in the web server.
- Bind requirement -> reviewed code candidate -> specific deployed revision -> approved API contract -> test evidence with immutable identifiers.
- Build cross-project, independently annotated benchmarks; measure link P@K/Recall@K/MRR, violation precision/recall/F1, automatic decision coverage and Wilson intervals.
- Test false-oracle, ambiguity, conditional requirements and known buggy variants. Preserve unknown/unsupported examples in denominators and show abstention rates.
- Do not merge this as a general verification feature until full security and regression checks pass.

## Research scope

Question: Can structured, human-approved requirement-derived test oracles plus observed execution evidence outperform text-only semantic guesses, without suppressing hard cases?

This M3 prototype establishes only the feasibility of producing grounded observations for a narrow supported rule. It does not establish the answer yet.
