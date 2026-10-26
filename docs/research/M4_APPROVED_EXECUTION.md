# SRS Guardian 2.0 — M4 operator-approved isolated execution gate

**Status:** CLI-only security-gated runner implementation. **Docker execution against a real, operator-built image has not yet been performed in the ChatGPT environment** (Docker unavailable). This is not yet production-ready; no claim of 95% accuracy.

## User value / vertical slice

Unlike the M3 preinstalled correct/faulty FastAPI fixtures, the M4 workflow accepts a **developer-built and reviewed FastAPI Docker image** and a **human-approved binding** between a previously indexed Python function and a test route. It then executes boundary cases inside a constrained container without exposing the Docker daemon to the public web API or executing the source ZIP uploaded to M2.

Sequence:

1. Analyze an SRS normally. Upload an authorized Python project ZIP to M2's **read-only code index** to retrieve its SHA-256 `index_id and ranked endpoint `symbol_id.
2. Independently build, inspect and approve a Docker image from that reviewed code revision. **Uploaded ZIPs are never turned into images automatically**.
3. An operator writes a local manifest containing source index ID, exact symbol ID, POST route, approved image **ID** (`sha256:...), module, app attribute and revision label. This manifest is **not** uploaded to the public API and must not contain secrets. Each mapping is a human attestation; the application does not independently prove that the image binary corresponds to the indexed source archive.
4. Run the CLI with a specific requirement statement and `--approve-oracle. The verifier supports the narrow M3 requirement family: mandatory rejection of transfers strictly above one integer threshold.
5. The host first verifies that the indexed symbol defines the approved route. It checks the local Docker image identity; it then runs a CLI-only container with restricted privileges/network and no host mounts. Inside the image, M4 loads the approved ASGI app and uses the M3 HTTP verifier to produce request/response evidence.
6. Return a provenance record that includes requirement text digest, source index ID, symbol, route, approved image ID, revision label and worker evidence checksum.

## Operator example (use only trusted, privately owned code)

From the complete SRS Guardian repository root:

```bash
# Build local image; verify Docker daemon is local and the source is approved.
docker build -f examples/m4/Dockerfile -t srs-m4-banking:local .
docker image inspect --format '{{.Id}}' srs-m4-banking:local

# Create ZIP of the reviewed app source and index via existing M2 endpoint/UI.
# Copy its exact 64-hex index_id and endpoint symbol_id into a private copy of:
# examples/m4/approved_targets.example.json

python -m backend.app.research.approved_runner \
  --manifest data/operator/approved_targets.json \
  --index-dir data/code_indexes \
  --target-id approved-local-bank-v1 \
  --index-id YOUR_EXACT_INDEX_ID \
  --symbol-id YOUR_EXACT_SYMBOL_ID \
  --req-key REQ-TRANSFER-LIMIT \
  --requirement 'The system shall reject transfers exceeding 10000 rupees.' \
  --approve-oracle
```

The example API is under `examples/m4/banking_api.py. Build its Docker image only after reviewing the source and dependencies. If you zip this Python file alone for indexing, its M2 route is `POST /payments/transfer.

## Security boundary and remaining risk

- **NO HTTP endpoint** runs Docker. CLI is invoked by an authorized operator only, not by a remote user.
- Docker commands use an argv list with `shell=False, without user-defined command lines or arbitrary host URLs.
- Runtime flags include `--network none, `--read-only, `--user 65534:65534, `--cap-drop ALL, `no-new-privileges, CPU/RAM/PID limits and a small `/tmp tmpfs; **no host source, data, or Docker socket mounts**.
- The container's base image should be pinned by digest and rebuilt/patched under the institution's security policy. Docker hardening reduces risk but does not guarantee isolation from hostile code. Run only reviewed or trusted apps until dedicated sandbox and operational security testing is complete.
- The indexed ZIP SHA-256 is a digest of the *submitted archive*, not cryptographic proof that it matches the Docker image. The manifest states an **operator-attested binding**, and the evidence makes that limitation explicit.
- If Docker is unavailable, the runner fails closed. Do not bypass this by importing arbitrary app code into the FastAPI web server.
- The SRS Guardian API currently has permissive CORS and inadequate authentication for exposing sensitive source indexes: do not deploy it publicly until those issues are fixed.
- The worker output SHA-256 is an integrity checksum, not a signed attestation from an adversarial target.

## Accuracy and paper readiness

M4 tests the mechanism, not the performance claim. The proposed **95%+** goal remains unverified. Before any publication evaluate labeled, unseen applications and compare text-only matching, rule-only inference and execution-backed decisions. Record *TP/FP/TN/FN, macro F1, violation precision/recall, coverage, abstentions, and time/cost*; don't train on test projects.

## Reproducibility

```bash
python -m pytest -q backend/tests/test_m4_approved_runner.py
# Also run legacy M1–M3 and Next.js production build before merging PRs.
```
