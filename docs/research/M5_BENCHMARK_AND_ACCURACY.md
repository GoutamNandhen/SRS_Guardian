# SRS Guardian 2.0 — M5 Research Benchmark, Baselines and Accuracy Audit

**Status: first controlled experiment complete; real-world 95% benchmark NOT achieved.**  
**Scope:** Python/FastAPI requirement-to-code traceability and observed transfer-rejection behavior.  
**Upstream:** M1 evaluator, M2 read-only AST traceability, M3 ASGI execution, M4 operator-approved Docker CLI.

## 1. What was implemented

- `backend/evaluation/m5_research_benchmark.py` compares **two or more** sets of prediction records using M1's evidence validation, metrics, and strict project-aware holdout rules. Outputs per-project error rates, full-denominator accuracy, and paired case-level differences.
- It validates a preregistered SHA-256 lock, detects identical code+revision appearing in different splits, flags near-duplicate requirement texts across splits, and rejects paper-ready claims on synthetic records or insufficiently documented records.
- Claimed `real_adjudicated` records require external source URL, source license, code snapshot fingerprint, two independent annotator IDs, adjudication record, independently established oracle provenance and reproduction instructions. **Populating strings in fields does not prove correctness; independent human audit remains essential.**
- It downgrades even a high M1 score to `BLOCKED_BY_M5_PROVENANCE_OR_LOCK` when provenance or preregistration conditions fail. No reported 95% score may be taken at face value without external assessment.
- `backend/evaluation/m5_controlled_pilot.py` runs HTTP requests against only trusted, author-defined FastAPI fixtures. It does not accept uploaded code, arbitrary hosts, credentials or GitHub repositories.

## 2. Actual controlled pilot — reproduced locally

**20 constructed cases**, five numeric thresholds (₹2,500, ₹5,000, ₹10,000, ₹20,000, ₹45,000), four implementation variants per threshold: conforming, over-permissive range, isolated acceptance hole at `limit+2`, and always-rejecting. All share **one transfer-rule template**; there are zero independently sampled software projects and zero independently adjudicated human labels.

| Probe policy | Inputs per variant | Constructed-case accuracy | Violation recall | Known misses |
|---|---:|---:|---:|---|
| One boundary test | 1 | 75% (15/20) | 50% (5/10) | Every `limit+2` acceptance hole |
| Existing M3 two probes | 2 | 75% (15/20) | 50% (5/10) | Every `limit+2` acceptance hole |
| Exploratory M5 three probes | 3 | 100% (20/20) | 100% (10/10) | None among these deliberately planted defects |

**Result:** The original two-probe M3 oracle can miss narrow failures. Adding a third local probe (`limit+2`) catches all planted defects **on the selected fixture family**. This is a deliberately friendly dataset for the third probe; it is **not** statistically independent validation and does **not** demonstrate 95% on real projects.

Run from root with runtime dependencies installed:

```bash
python -m backend.evaluation.m5_controlled_pilot --out benchmarks/m5/controlled_pilot_results.json
python -m pytest -q backend/tests/test_m5_research_benchmark.py
```

The JSON output contains actual requests, observed FastAPI responses, constructed gold labels and all errors. **Do not replace these with invented screenshots or trained-model accuracy.**

## 3. Benchmark protocol for the research paper

We must evaluate **two distinct tracks**.

### Track A — Requirement-to-code traceability

- Use a real benchmark with linked natural-language requirements and source (e.g. SAFA; Dronology/CoEST benchmarks as appropriate). Do not misrepresent requirement artifact links as executable behavior.
- Compare M2 BM25/lexical retrieval against a documented hybrid or embedding baseline, preserving the same candidate pool, split, retrieval budget and ground-truth links.
- Measure Precision@1, Recall@1, Recall@5, MRR, false links, and project-specific performance.
- Remove training/test overlap at the project and near-duplicate requirement levels.

### Track B — Requirement-conformance behavior

- Use **source-documented behavior with independently confirmed correct and faulty variants**. The expected behavior must be determined without viewing the system's current output as ground truth.
- Blindly label requirement–implementation pairs with at least two independent annotators and an adjudicator; record disagreement and resolution. Do not count synthetic generated mutations as real defects.
- Report violation precision, recall, F1, decision coverage, full-denominator accuracy including abstentions, Wilson confidence intervals, missed real bugs, and false alarms.
- Stratify by requirement type, application and fault type. Comparing methods against the **same** cases allows paired improvements; treat cases from the same project as correlated.
- Evaluate each additional execution probe under matched compute/request budgets where possible; cost of a probe must be reported.
- Keep the final untouched multi-project test split sealed until methods and thresholds are frozen. Prefer ≥500 labeled conforming/violating cases, at least three unseen projects, at least 50 per class and ≥50 unlinked pairs; those are M1's current acceptance thresholds, not evidence of attainment.

### Candidate publicly available datasets (access and license must be checked)

- SAFA dataset: https://zenodo.org/records/18285767 — real software artifacts, with *partial* natural-language-to-code trace links. Good for Track A, NOT automatic conformance truth. Related paper: https://doi.org/10.1145/3786174.3788354.
- TestExplora: https://www.microsoft.com/en-us/research/publication/testexplora-benchmarking-llms-for-proactive-bug-discovery-via-repository-level-test-generation/ — 2026 proactive bug benchmark based on documentation and fixed/buggy project revisions. Good research comparator but does not naturally match our M3/M4 narrow Python/FastAPI transfer-rule oracle; any adapted subset must be preregistered and documented.
- Dronology/CoEST benchmark families: https://www.mdpi.com/2078-2489/17/6/541 (dataset summary and references). Useful for independent traceability retrieval evaluation, not conformance truth.

## 4. Score comparison CLI

```bash
python -m backend.evaluation.m5_research_benchmark \
  --gold /path/to/verified_gold.jsonl \
  --system candidate=/path/to/candidate_predictions.jsonl \
  --system baseline=/path/to/baseline_predictions.jsonl \
  --evidence candidate=/path/to/candidate_evidence \
  --evidence baseline=/path/to/baseline_evidence \
  --split test \
  --lock PRE_REGISTERED_64_HEX_CANONICAL_GOLD_FINGERPRINT \
  --out /path/to/comparative_report.json
```

The `--lock` is the SHA-256 of canonicalized JSONL record objects as computed by `canonical_digest`, **not** the byte hash of the file. Register it before model selection, not after viewing scores. This tool compares prediction **evidence**; a text-only baseline cannot be declared to have failed merely because it has no executable artifact. For Track A, compare retrieval metrics without requiring runtime test evidence. For Track B, either add comparable evidence gathering to both approaches, or present decisions separately and acknowledge different verification capabilities.

## 5. Known limitations and decision gate

- The controlled pilot intentionally selects a fault at `limit+2` and then adds exactly that input. Its apparent 100% accuracy is *selection-biased* and is **not** evidence of a broadly superior model.
- `always_reject` is conforming **only to the single above-limit rejection requirement**; a fuller banking SRS would additionally require successful permitted transfers, which the current oracle does not infer.
- Independent Docker-backed M4 runs against local images have not been validated in this environment. A Docker image is not cryptographically linked to the source ZIP merely by operator approval.
- `M5_research_benchmark` does not train models, tune thresholds or generate labels; it prepares trustworthy comparison infrastructure. Our 95% project target remains open.
- Do not expose evaluation gold labels to agent-generated predictions or train/test optimization. No full legacy suite or Next.js build was performed solely by this M5 module.

**GO next:** register and label Track A real links; select a defensible real Track B subset, expand supported requirement types with fail-closed oracles, and then compare frozen model versions on untouched projects. **NO-GO:** public 95% claim, arbitrary uploaded-code execution, or paper drafting that uses synthetic results as real validation.
