# M23 — External TeaStore architecture-to-code review pilot

**Scope:** replace synthetic-only candidate preparation with an independently authored, non-Dronology research corpus containing real architecture documentation, Java source files, and published SAD-to-code links. This is a **static, reproducible five-file subset** and is **not** an independent behavioral-conformance benchmark.

## Two pinned upstream sources

1. ArDoCo ICSE 2024 replication package: `ArDoCo/Replication-Package-ICSE24_Recovering-Trace-Links-Between-Software-Documentation-And-Code` at `a4b221733fb43938f130636db8d5434bd30ec28d`. Its `LICENSE.md` Git blob is `9178636db5328bbf687ec0cb85f95406c7f725cb` (MIT). The selected SAD sentences and published mapping CSV are pinned by exact Git blob IDs in `backend/evaluation/m23_teastore_external.py`.
2. Original TeaStore source mirror used by the study: `ArDoCo/TeaStore` at `bdc49020a55cfa97eaabbb25744fefbc2697defa`, explicitly referenced in the replication package's `data/README.md`. Its `LICENSE` Git blob is `8dada3edaf50dbc082c9a125058f25def75e625a` (Apache-2.0). The five selected Java files are individually pinned by Git blob hashes.

Source references:
- https://github.com/ArDoCo/Replication-Package-ICSE24_Recovering-Trace-Links-Between-Software-Documentation-And-Code/blob/a4b221733fb43938f130636db8d5434bd30ec28d/data/README.md
- https://github.com/ArDoCo/TeaStore/tree/bdc49020a55cfa97eaabbb25744fefbc2697defa
- https://github.com/ArDoCo/Replication-Package-ICSE24_Recovering-Trace-Links-Between-Software-Documentation-And-Code/blob/a4b221733fb43938f130636db8d5434bd30ec28d/data/SAD-Code-goldstandards/goldstandard-teastore.csv

The MIT and Apache license texts are preserved with the evidence artifact. The repository licenses and hashes are verified; provenance/reuse rights of any separately contributed text must still be checked before redistributing the full benchmark.

## What the reproducible script actually prepares

- 3 real TeaStore architecture-documentation sentences (IDs 1, 27, 28).
- 5 pinned Java files from registry, recommender and authentication components, including one deliberately **unlabeled** confusable candidate.
- 6 *paper-declared* links **not** treated as independent gold.
- 15 possible pairs, all included in an M20 blinded review queue, with reviewer A/B templates whose labels remain `null`.
- Per-file source URL, Git blob SHA-1 and SHA-256; path-delimited SHA-256 of the five-file **subset**. No claim that this is the full deployable source snapshot.
- 0 independently adjudicated link labels, 0 behavioral conformance labels, and **no valid conformance accuracy/precision/recall/coverage metrics**.

The paper calls its mapping a gold standard, but for this research project it is **an observed external reference only**. It must not be used as a substitute for our own independent adjudication. The project was selected purposively and is not a statistically representative sample.

## Reproduce

```bash
python -m pip install pytest==8.4.2
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m23_teastore_external.py
python -m backend.evaluation.m23_teastore_external --out-dir /tmp/m23-teastore
```

The command downloads **only** eleven fixed, hash-pinned static text files from the two repositories and fails closed on drift. It never imports, builds, or executes third-party code. CI uploads the complete manifest, licenses, blinded M20 queue and pending reviewer templates.

## Independent review handoff

Give reviewers only `annotation/blind_queue.jsonl`, their individual `annotation/reviewer_*.jsonl`, and the source URLs in `external_evidence.json`. **Do not show them** `candidate_universe.json`, `annotation/manifest.json`, the paper's mapping CSV, or the other reviewer's judgments until adjudication. Each reviewer must inspect the pinned source text, decide whether the file implements the architecture sentence, and cite source lines; disagreements go to a third adjudicator. Unknown is a valid outcome.

For the research target, a separate effort must collect **real behavioral requirement oracles**, independently established conforming/violating code versions, and complete project snapshots. SAD-to-code trace links alone cannot tell whether an application conforms to a requirement. Do not compute >=95% conformance accuracy, >=95% violation precision or >=90% violation recall from these unlabeled candidates.

**Next engineering action:** after human link review, run a fixed, preregistered held-out retrieval baseline against adjudicated links and publish per-project retrieval metrics; separately obtain real behavioral labels before reporting conformance metrics.
