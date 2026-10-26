# SRS Guardian 2.0 — Milestone 2: Candidate Code Traceability

**Status:** Implemented source indexer, API, Traceability screen, and service tests. **Not** behavior verification or 95% accuracy.

## User workflow

1. In Documents, upload an SRS (PDF/DOCX/TXT) and run analysis so requirements are stored.
2. Open **Traceability** and select the analyzed SRS.
3. Upload a ZIP export of a Python/FastAPI project you are authorized to inspect.
4. Click **Index code**, then **Link requirements**.
5. Expand code candidates to inspect their symbol name, API method/route, source path and line numbers, matching tokens and snippet. All links are **Unverified candidate**, not claims of implementation.

GitHub repositories can be exported to ZIP and uploaded. There is **no direct GitHub repository clone, OAuth or API import** in M2. The server must not fetch arbitrary URLs.

## Backend API

- POST /api/code-traceability/index (multipart form: file ZIP, optional label)
- GET /api/code-traceability/index/{index_id}
- GET /api/code-traceability/documents/{document_id}/links?index_id={id}&offset=0&limit=20&top_k=5

Indexes are content-addressed by SHA-256 and stored under data/code_indexes/; existing SRS requirements are loaded from the application's database. There is no database migration.

## Retrieval methodology

- Inspect ZIP contents; reject oversized, duplicate, traversal and symlink members.
- Parse .py files into Python AST; extract top-level functions, class methods, FastAPI decorators and literal same-file APIRouter prefixes.
- Tokenize identifiers, code comments/docstrings and source excerpts.
- Rank candidates with BM25-style lexical overlap, route overlap and symbol-name boosts.
- Show scores only as **relative, uncalibrated retrieval rankings**.
- No imported application code execution, network cloning, symbolic testing or LLM judgment.
- A missing match does not prove an unimplemented requirement.

## Privacy and engineering limits

Existing SRS Guardian has no per-user authentication/authorization enforcement for these endpoints, and the stored JSON index contains code excerpts. Use locally / behind a private authenticated server only; do not deploy publicly before access control, index ownership, quotas and retention are implemented. Delete data/code_indexes/ entries when unnecessary.

Supported: Python and common declarative FastAPI route decorators. Not supported: Java/JS code indexing, dynamic routing, inter-file router mount resolution, semantic reranking, executable test cases, proof of conformance.

## Tests and validation

Run at repository root with project dependencies installed:

    python -m pytest backend/tests/test_code_traceability.py -q

Service regression tests cover matching, AST execution avoidance, parse failures, ZIP traversal, duplicate paths, id validation, and stable ordering. These tests validate the mechanism but do not establish accuracy on an independent project-held-out corpus.

**Target ≥95% remains unmeasured.** A labeled requirement-to-code test corpus and independent project-level evaluation are prerequisites to any percentage claim. The M1 evaluator remains a separate research artifact until integrated with real traceability labels.

## Next: M3

Add structured test oracles for narrowly supported numerical/business-rule requirements, a restricted test environment, expected/actual evidence, and four states: observed violation, passed available checks, insufficient evidence, and needs human clarification. Never treat source-code retrieval itself as proof of conformance.
