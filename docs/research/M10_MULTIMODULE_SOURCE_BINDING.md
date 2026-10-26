# SRS Guardian 2.0 — M10: Source binding for included FastAPI routers

**Scope:** Trusted, operator-approved Python/FastAPI applications only. This is a narrow engineering verification experiment, **not** a ≥95% research-accuracy result.

## Problem addressed

M9 bound the exact bytes of the indexed source file to the FastAPI ASGI entrypoint module. Real applications commonly define routes in separate `APIRouter` modules, then import them into a different `app` module. In that case, M9's source comparison could not succeed even when the approved route handler matched the indexed source.

## Implemented approach

1. Keep M2's read-only ZIP AST index, including the indexed route's qualified symbol, POST path and exact Python source SHA-256.
2. Keep M4's operator-approved, local immutable Docker image ID and explicit route, index and symbol selection.
3. Within the constrained Docker worker, locate the unique FastAPI `APIRoute` matching the approved POST path. Report the actual handler's defining Python module, qualified name and SHA-256 of its source bytes.
4. The host compares the reported handler name and source digest with the indexed symbol. If the handler is in the app entrypoint module, the previous M9 entrypoint digest gate is retained.
5. Test both a correct and deliberately faulty reviewed application where `examples/m10/app_*.py` imports `examples/m10/router_*.py`. The source ZIP contains the *router* file, not the app entrypoint.

The result's `source_content_binding` distinguishes `worker_reported_endpoint_digest_matches_index` from the original M9 `worker_reported_module_digest_matches_index`.

## Reproduction

From the repository root with the focused dependencies installed:

```bash
python -m pytest -q backend/tests/test_m10_multimodule_binding.py
docker build -f examples/m4/Dockerfile -t srs-m8-trusted-banking:ci .
python -m backend.evaluation.m10_multimodule_docker_e2e --out /tmp/m10-multimodule.json
```

The workflow `.github/workflows/srs2-m10-multimodule.yml` executes M1–M10 regression and actual restricted Docker tests in GitHub Actions.

## Boundaries and limitations

- Source-file digests are worker-reported; the checksum is **not a signed attestation**. A malicious reviewed image can forge the evidence. Docker runs only trusted operator-built images, with no network or host mounts.
- Only the exact matched POST route's handler file is checked. The worker does not verify imported dependencies, database state, environment settings, decorators' transitive effects, the entire image or any unrelated routes.
- For new multi-module evidence, a missing handler digest cannot be replaced by the different ASGI entrypoint digest. Legacy M9 single-module evidence remains compatible.
- The M2 indexer recognizes a limited set of static decorator and router-prefix patterns. Dynamic route construction and complex dependency injection remain unsupported.
- The system has **not** established ≥95% behavioral-conformance accuracy, precision or recall on independently labeled unseen projects. Two trusted fixtures do not count as external projects.
- All PRs remain drafts, and `main` is unchanged.
