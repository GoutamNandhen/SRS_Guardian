# SRS Guardian 2.0 — M9 source-content binding audit

**Status:** Implementation submitted for CI validation. No production merge. No claim of ≥95% conformance accuracy.

## Problem

M8 checked the indexed AST symbol/route and a fixed operator-approved Docker image identity, but did not compare the actual Python source executed inside the image with the bytes originally indexed from the reviewed ZIP. A stale image could therefore produce convincing HTTP evidence for a different code revision.

## M9 improvement

1. The M2 ZIP indexer records a SHA-256 digest of the **exact raw bytes of each indexed Python file** on every symbol record (not of a decoded, normalized or truncated excerpt).
2. The isolated M4 worker reads the `.py` file of its imported FastAPI application module inside the approved image and includes its SHA-256 digest in checksummed worker evidence. If the source file cannot be read, the digest is null.
3. The M4 host verifier retrieves the approved symbol's file digest **from the stored index**, not from a client-provided value, and rejects the run when it differs from the worker-reported executed module digest.
4. For legacy M2 indexes without a file digest, the existing M4 flow remains available but reports `source_content_binding = unverified_legacy_index_missing_file_digest`. It must not be represented as source-verified evidence.
5. M8's two real Docker fixture tests now require matching source-file digests. The M9 CI workflow also modifies a source file **inside a controlled test image only**, then checks that the verifier rejects the mismatch.

## Scope and limitations

- **Not cryptographic remote attestation:** the worker runs inside the approved image and reports its own digest. A malicious image or replaced worker could forge the report and checksum. The operator must independently approve the image and build environment.
- **Single-module limitation:** the indexed symbol file must be the same Python source file as the approved FastAPI app module. Projects with a separate application entry point and router module will fail closed until a reviewed multi-module binding protocol is implemented.
- **Not whole-image provenance:** the digest does not cover transitive dependencies, runtime configuration, other source modules, base-image content or dynamic imports. Image identity is still checked by its immutable local ID; source-to-image binding remains operator-attested.
- **Trusted code only:** no user-uploaded ZIP is executed, no new public Docker endpoint is introduced, and Docker continues to run without network access or host mounts.
- **No accuracy implication:** two controlled banking fixtures and a deliberately introduced source drift are engineering/security tests, not independent behavioral-conformance benchmarks. M9 does not advance the measured ≥95% research claim.

## Reproduction

Run from the repository root:

```bash
python -m pytest -q backend/tests/test_m9_source_binding.py
docker build -f examples/m4/Dockerfile -t srs-m8-trusted-banking:ci .
python -m backend.evaluation.m8_docker_e2e --out /tmp/srs-m9-matched.json
```

The workflow `.github/workflows/srs2-m9-source-binding.yml` runs the full focused M1–M9 regression, the positive real-Docker source comparison and a negative real-Docker source-drift check.

## Remaining blockers

Full real-user document-to-code workflow, authentication and CORS security review, multi-module source binding, independently labeled cross-project conformance truth, and blinded evaluation with explicit abstentions and class-specific precision/recall remain unverified. **No ≥95% generalization claim is supported.**
