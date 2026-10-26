# M15 — Gold-lock fingerprint and annotation-finality integrity

**Status:** Research evaluation integrity fix; no model-accuracy improvement or independent benchmark.

## Findings

M14 introduced a variable-shadowing regression in `audit_benchmark`. It computed the canonical SHA-256 digest of all gold rows, then overwrote the local `digest` variable with each real project's source snapshot digest. The preregistered lock check used the correct original digest, but the returned `fingerprint_sha256` could misleadingly report the **last source snapshot hash** instead of the benchmark fingerprint. That breaks audit-trail consistency even when a valid gold lock was supplied.

Separately, M5 allowed `dataset_status=real_adjudicated` rows whose `adjudication_status=draft` to pass the *structural provenance* screen when the other metadata fields were filled. The M1 scorer rejects draft rows on the selected split, but a draft row in another split could still be included in an otherwise accepted M5 provenance audit.

## Corrections

- Preserve `benchmark_fingerprint` from `canonical_digest(gold)` through both lock comparison and report output.
- Use a distinct `snapshot_digest` variable exclusively for detecting identical source snapshots under different project IDs.
- Treat **any** real-claimed draft label, regardless of split, as a critical provenance issue; keep M1's existing selected-split check.
- Add six fabricated-only regression tests, including a locked two-project gold set, a changed gold row, a draft training label paired with an adjudicated test label, and an unchanged valid structural case.
- Run all M1–M15 focused regressions, real restricted-Docker positive/negative controls, and a Next.js production build in CI.

## Reproduction

```bash
python -m pytest -q backend/tests/test_m5_research_benchmark.py backend/tests/test_m14_snapshot_independence.py backend/tests/test_m15_provenance_lock_integrity.py
```

**Research limitations:** A matching SHA-256 lock proves byte-level consistency only with the *submitted* gold rows; it does not prove that the lock was independently preregistered, labels were independently adjudicated, snapshots were authentic, or that 95% real-world accuracy was achieved. This change intentionally does not relax any numerical acceptance thresholds or merge into `main`.
