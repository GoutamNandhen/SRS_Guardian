# M11 — Third boundary probe for isolated transfer-acceptance defects

**Status:** CI validation pending. **Scope:** fixed, reviewer-approved integer transfer rejection only; not general requirement verification.

## Problem observed in M5

The original M3/M4 oracle sent two above-limit transfer amounts: `limit+1` and a distant probe (approximately `limit+10%`). M5's controlled pilot contained a deliberately faulty application that accepted *only* `limit+2` beyond the approved threshold. Both old probes passed, incorrectly yielding `passed_available_checks`. This is a **constructed known miss**, not a discovered production bug.

## M11 change

The verifier now generates three distinct above-limit requests: `limit+1`, `limit+2`, and a farther probe (or `limit+3` if the far probe duplicates `limit+2` for small thresholds). Every request expects a 2xx JSON body with `accepted: false`. Non-2xx or malformed responses remain inconclusive. The host validates the exact approved test plan and checksum against the Docker worker evidence, so an image cannot silently omit the third observation without failing the protocol.

The CI adds a reviewed FastAPI fixture that rejects all amounts above 10,000 **except 10,002**, plus actual restricted Docker checks of that fixture and the existing conforming and faulty single-/multi-module apps.

## Reproduction

```bash
python -m pytest -q backend/tests/test_conformance_verification.py backend/tests/test_m4_approved_runner.py
docker build -f examples/m4/Dockerfile -t srs-m8-trusted-banking:ci .
python -m backend.evaluation.m8_docker_e2e --out /tmp/m11-single-module.json
python -m backend.evaluation.m10_multimodule_docker_e2e --out /tmp/m11-multimodule.json
```

## Research interpretation and limits

The M5 controlled pilot previously reported 15/20 cases correctly classified with the old two-probe strategy and 20/20 with the three-probe strategy, on deliberately selected fixtures. **Those figures are not external accuracy**; adding a probe specifically for a known fault can inflate apparent improvement. M11 implements the already-studied three-probe strategy in the actual M3/M4 execution path. Future blind tests must evaluate it on unseen independently labeled projects without tuning the probes to the test cases.

The feature remains CLI-gated for reviewed Docker images; it never executes an uploaded ZIP. Even a passing result means only *passed the available checks*, not that the full requirement or application is correct. More probes cost more execution time, and many possible faulty amounts remain untested.

**95% independent conformance accuracy: not established.**
