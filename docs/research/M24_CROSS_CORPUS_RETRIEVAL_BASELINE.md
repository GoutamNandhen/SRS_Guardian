# M24 — Measured two-project external observed-link retrieval baseline

**Verified 2026-10-27:** [GitHub Actions run 40525257090](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40525257090) passed: 27 focused tests, real hash-pinned TeaStore static-source fetch, M20 blinded queue generation, two-project ranking, and artifact upload.

This is the first *cross-project exploratory retrieval measurement* in this sequence. It is **not** a behavioral requirement-to-code conformance benchmark. No human-adjudicated links, verified true negatives, conforming/violating revisions, or independent held-out conformance labels exist.

## Source and licenses

- **Dronology:** preexisting M6 fixture `benchmarks/m6/dronology_observed_trace_links.json`, sourced from SAREC-Lab/SAFA-Artifacts (reported MIT upstream), two versions **of one project**. Its Git graph observations can be indirect and incomplete; the full code snapshot is not verified in this evaluation.
- **TeaStore:** M23's pinned ArDoCo ICSE 2024 replication package (MIT) and ArDoCo/TeaStore source (Apache-2.0). M23 downloads and verifies eleven allowlisted static files against exact Git blob hashes and retains license texts. The benchmark is a deliberately selected **3 architecture statements × 5 Java files** subset, with six author/paper-declared links. These are not independently adjudicated. Rights in third-party authored documentation still require review before republishing.

The two methods are preexisting M7 **path-only** BM25 and character/subword hybrid reciprocal-rank fusion. Neither reads Java source bodies, executes code, infers conformance, or receives labels during ranking. M7 was originally developed using Dronology, so these are not clean unseen-project accuracy estimates. TeaStore was purposively selected, so its subset is also not representative.

## Reproducible measured results

Results from the successful CI run, scored **only against published/observed positive links**:

| External project | Cohort | Linked statements | Method | Hit@1 on observed-linked statements | Observed-positive link recall@3 |
|---|---|---:|---|---:|---:|
| Dronology | V0 | 8 | path BM25 | 0.0% | 10.81% |
| Dronology | V0 | 8 | hybrid RRF | 12.5% | 10.81% |
| Dronology | V1 | 10 | path BM25 | 20.0% | 6.45% |
| Dronology | V1 | 10 | hybrid RRF | 30.0% | 8.60% |
| TeaStore | five-file subset | 3 | path BM25 | 66.67% | 66.67% |
| TeaStore | five-file subset | 3 | hybrid RRF | 66.67% | 83.33% |

**Interpretation:** these results are weak and highly variable across projects, even for retrieval of externally observed links. Do **not** call these accuracy, conformance precision, violation recall, or generalization performance. Hit@K asks whether *at least one* externally observed link appears among the first K returned paths. Observed-positive recall@K measures the fraction of all observed links retrieved in the first K. Unobserved links are **unknown**, not negatives. TeaStore has only five candidates, so top-5 results are inherently saturated.

The machine-readable CI artifact contains per-statement rankings' observed-hit counts, retrieval coverage, per-project denominators, source/manifest hashes, and the pending M20 reviewer files.

## Reproduce

From the full feature branch repository root:

```bash
python -m pip install 'pytest==8.4.2' 'scikit-learn==1.7.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m23_teastore_external.py backend/tests/test_m24_cross_corpus_baseline.py
python -m backend.evaluation.m23_teastore_external --out-dir /tmp/m24-teastore
python -m backend.evaluation.m24_cross_corpus_baseline \
  --dronology benchmarks/m6/dronology_observed_trace_links.json \
  --teastore-universe /tmp/m24-teastore/candidate_universe.json \
  --teastore-evidence /tmp/m24-teastore/external_evidence.json \
  --output /tmp/m24-two-project-baseline.json
```

This fetches pinned **static** source text only; it does not build or execute third-party software.

## Exactly what is still missing

1. Give two independent annotators **only** the M20 blinded TeaStore queue and pinned source-file URLs. For all 15 pairs, independently mark linked/not-linked/uncertain with cited source lines. Adjudicate disagreements with a third reviewer. Keep the published mapping and sampling provenance hidden during first-pass review.
2. Collect actual **behavioral** requirements and separately validated conforming and violating code revisions from multiple unseen projects. The TeaStore architecture descriptions and Dronology trace graphs are not execution oracles.
3. Pin full project source snapshots, verify all relevant source and document licenses, and pre-register project-level splits. Do not tune on held-out projects.
4. Only after independent adjudication and genuine executable evidence, report conformance TP/FP/TN/FN, accuracy, violation precision/recall, abstention and coverage **per project**, then assess the ≥95%/≥95%/≥90% targets.

**Current research-grade conformance metrics:** accuracy = null; violation precision = null; violation recall = null; coverage = null. This is a meaningful negative/diagnostic retrieval result, not evidence of the research target.
