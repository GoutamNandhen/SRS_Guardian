# SRS Guardian 2.0 — M6 external traceability pilot

**Status:** External published artifact-link evaluation foundation. NOT a 95% classification/conformance result and NOT real executable verification. Kept outside production APIs.

## Why these data

**Source:** SAREC-Lab, `SAFA-Artifacts` repository, Dronology safety-case datasets `V0-simplified.json` and `V1-simplified.json`; https://github.com/SAREC-Lab/SAFA-Artifacts . **Note:** This is the **2019 Safety Assurance case FA** artifact project, **NOT** the distinct 2026 SAFA Official Dataset (Dearstyne et al., https://doi.org/10.5281/zenodo.18285767). The identical acronym must not be conflated.

We obtained the JSON from the source project's public GitHub branch. Every normalized record preserves the upstream source blob SHA, requirement ID, text, unique Java file path and traversed requirement → design/environment/package → code reachability. The fixture includes source link and acknowledgement; upstream uses MIT license. Source records are an *artifact graph of reported traceability*, not expert-validated direct natural-language-requirement-to-function pairs.

## Real external data facts (derived from published artifact trees)

| Version | Unique requirement IDs | IDs with an observed Code descendant | Distinct Code file paths | Known positive requirement→path links |
|---|---:|---:|---:|---:|
| V0 | 24 | 8 | 31 | 37 |
| V1 | 25 | 10 | 86 | 93 |

All figures count only `Requirement`, `SafetyRequirement`, and `ProcessRequirement` nodes and traverse nested `children`. These are two snapshots of **one** Java-heavy project; they cannot serve as independent train/test projects. Not every requirement is linked to code. Some published edges are indirect, incomplete, or duplicated. The fixture deduplicates by requirement ID and normalized Java path.

## What M6 evaluates

For requirements with at least one observed linked code path, rank candidate code paths with two transparent **path-only** BM25-style baselines: filename tokens and full-path tokens. Metrics: Hit@1/5/10 (did any *observed known-positive* link appear in top K), MRR for first observed link, mean recall of observed positive links at 5, and Wilson 95% intervals for Hit@K. Requirements without observed links are not negatives and are excluded from hit/mrr denominators, but their count is reported as observed-link coverage.

**What M6 cannot conclude:** precision, true-negative rate, conformance accuracy, actual faulty code detection, M2 AST-indexed retrieval performance (the dataset only includes code-path references here, not AST excerpts), or generalization to unseen projects. Version V0→V1 leakage makes any model training split across versions invalid for an unseen-project result. Performance gaps are research findings, not evidence of defect in the software itself.

## Run

```bash
python -m pytest -q backend/tests/test_m6_external_trace.py
python -m backend.evaluation.m6_external_trace --dataset benchmarks/m6/dronology_observed_trace_links.json --output benchmarks/m6/external_trace_results.json
```

The supplied `dronology_observed_trace_links.json` was generated from the two upstream files; provenance fields include original blob SHAs. Do not overwrite the fixture with a revised version while comparing previous experiments. Do not use this dataset for prompt or model fitting followed by an alleged held-out project evaluation.

## Next: publishable evidence gate

1. **Track A (traceability):** collect at least 3 independently sourced, complete requirements→source labels with actual source bytes; maintain project-held-out splits; independently revalidate annotation coverage and alias/path mapping. E.g. the **2026 SAFA Official Dataset** (DOI above, limited feature coverage), Dronology code releases, iTrust, eTour etc. Human review by ≥2 annotators with disagreement resolution.
2. **Track B (behavior):** select genuine testable requirements with independently reviewed oracles, record known faulty/correct commits, and run M4 with authorized pinned images under restrictive Docker. Faulty variants are **not** interchangeable with naturally occurring historical bugs; report them separately.
3. Record per-project Recall@K, MRR, link precision using only adjudicated negatives, end-to-end violation precision/recall/F1, decision coverage, runtime and calibration; report CI/intervals and paper-ready ablations.
4. Freeze dataset, split, thresholds, method and labels before any final test. Require ≥400–500 independently adjudicated cases across unseen projects before evaluating faculty's ≥95% aspirational target. Even 95% observed accuracy on 500 trials has considerable uncertainty; report full binomial uncertainty and class imbalance.
5. **No 95% claim until Track B is independently evaluated and eligible under M1/M5 gate.** Remain explicit about unsupported/ambiguous requirements.

## Reproducibility and ethics

- License: see https://github.com/SAREC-Lab/SAFA-Artifacts/blob/master/LICENSE (MIT); preserve notice and attribution when distributing subsets.
- The published artifact tree's link paths are **positive-only observed links**; a missing relationship could simply be unannotated.
- JSON files are third-party published artifacts; do not use an unseen full proprietary SRS or customer repository without authorization.
- The Python evaluation operates on text metadata only; it never executes downloaded or uploaded code.
