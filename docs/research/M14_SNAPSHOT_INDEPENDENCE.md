# M14 — Prevent project-alias leakage in the 95% research gate

**Status:** Evaluation safeguard, not an accuracy improvement or a real-world benchmark.

## Problem

M1 already rejects a repeated `project_id` across train/test splits. M5 previously counted different `project_id` strings as independent even if two purported real-world projects pointed to **exactly the same source snapshot**. A copied or renamed project could therefore inflate the reported number of independent projects or leak code across train and test.

## Change

For every `real_adjudicated` row, M5 now requires a lowercase, exactly 64-character hexadecimal `code_snapshot_sha256`. It records the first associated `project_id`, split and case ID. Reusing the same source snapshot digest under a *different* project ID creates a critical provenance issue, even within one split. Repeated requirements from one project at the same snapshot are allowed. The audit reports `real_distinct_source_snapshots` separately from the user-supplied `projects` count.

M5's `compare_systems` already blocks publication-grade acceptance whenever the provenance audit has a critical issue. Therefore, the new source-identity failure also blocks any research acceptance claim made through M5. The independent dataset lock and existing 95% accuracy/link/violation/coverage thresholds remain unchanged.

## Annotation protocol for a future real benchmark

1. Preserve each authorized, immutable project snapshot artifact, its provenance and license. Calculate SHA-256 from the **exact retained snapshot bytes**, and store the digest consistently for every row derived from that artifact.
2. Assign project IDs from independently verified upstream projects, not folder names or arbitrary aliases. Keep the artifact and upstream URL available for human audit.
3. Separate entire projects into train, validation and held-out test groups before tuning. Check snapshot hashes and manually inspect forks, mirrors and near-duplicates.
4. Collect requirement↔code labels, conforming/nonconforming decisions, actual execution evidence, independent annotators and adjudication records. Include genuine unlinked pairs and negative outcomes.
5. Preregister and lock gold labels before scoring. Evaluate full-denominator accuracy, link precision/recall, violation precision/recall, abstention coverage, and per-project breakdown. Do not claim 95% without independent provenance and evidence review.

**Limits:** Byte-identical source snapshot hashes can detect only exact reuse. The check does not identify repackaged copies, modified forks, semantically identical projects, fabricated hash strings or dishonest annotator claims. `research_eligible_by_provenance` means only a *structural screening* passed; it is not certification of real provenance. M1's standalone arithmetic acceptance gate is not an independently audited publication claim. No real-world ≥95% accuracy has been established.

## Reproduce

```bash
python -m pytest -q backend/tests/test_m5_research_benchmark.py backend/tests/test_m14_snapshot_independence.py
```
