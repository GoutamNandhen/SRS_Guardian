# M22 — Real external corpus availability audit (2026-10-27)

**Purpose:** determine whether a separately authored, potentially usable, non-Dronology requirement-to-source corpus is actually present in a pinned research repository. This is *source discovery*, not a benchmark or model improvement.

## Pinned upstream evidence

- Upstream: https://github.com/WM-SEMERU/Sense-traceability
- Commit: `05daf75800a99e01b9845232cdf373e142e01bcf`
- Repository `LICENSE` blob: `d3ef6b29be3026bcabacbc8eb92f9242420686e6` (Apache-2.0).
- Repository `README.md` blob: `36d6356ae9cb83a9dc8a275e94ded6976f3e7772`.
- **Important:** the repository license does not establish the license or redistribution rights of the bundled third-party project corpora. Do not publish or reuse third-party datasets without verifying their original terms.
- Method: GitHub Git tree metadata only. Every source candidate is identified by Git object hash. No third-party source files were downloaded or executed by this audit.

## CI-observed inventory

GitHub Actions run: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40507339688

| Corpus | Git tree exists | `corpus/req` file objects | `corpus/src` file objects | Mapping candidates |
| --- | --- | ---: | ---: | ---: |
| Albergate | yes | 0 | 0 | 0 |
| EBT | yes | 0 | 0 | 0 |
| eTour | yes | 0 | 0 | 0 |
| iTrust | yes | 0 | 0 | 0 |
| LibEST | yes | 0 | 0 | 0 |
| SMOS | yes | 0 | 0 | 0 |
| Dronology | yes | 58 | 184 | 2 |

**Interpretation:** Six named project trees did not contain artifacts matching the narrowly defined `corpus/req`, `corpus/src`, and `mappings` conventions in this pinned snapshot. That does **not** prove their data are unavailable elsewhere or that those projects lack requirements/source/trace links. Inspect their recorded paths and upstream data packaging before excluding them. Dronology is present, but it was already used in earlier milestones and cannot be counted as a new independent project. Counts are Git file-object counts, **not** adjudicated requirements, trace links, executable code units or behavioral test cases.

## Reproduce

```bash
python -m pip install pytest==8.4.2
python -m pytest -q backend/tests/test_m22_external_corpus_inventory.py
python -m backend.evaluation.m22_external_corpus_inventory --out /tmp/m22-corpus-inventory.json
```

CI verified **5/5 focused tests** and a live pinned metadata inventory. Its downloadable artifact records each project path and Git object ID, including nonmatching files. No metrics are derived from the inventory: conformance accuracy, violation precision/recall and coverage are `null`, independent adjudication count is zero, and `research_95_eligible=false`.

## Exact next research blocker

Obtain **at least one genuinely distinct non-Dronology project** with (a) verified original data/source license, (b) immutable, complete requirement text and source snapshot, (c) reviewable author-declared trace matrix or explicit trace candidates, and (d) independently reviewable behavioral conformance/violation evidence. For the first three, ingest only static files and verify Git/SHA-256 provenance. Use M20 to create blinded, unlabeled reviewer queues. Two independent reviewers must label link candidates without seeing original tags or predictions; a third adjudicator resolves disagreements. A separate review must establish *actual behavioral* conformance/violation labels. Only after these steps should a held-out project be used to compute real conformance accuracy, violation precision, recall, abstentions, coverage and per-project results.

Do not interpret observed trace links, absent links, fixture test outcomes, or repository README summary counts as independent conformance ground truth.
