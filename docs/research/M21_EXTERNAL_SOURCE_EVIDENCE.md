# M21 — Verified external source evidence, not gold or conformance accuracy

## Upstream and license
- **Repository:** https://github.com/flashtrace/flashtrace
- **Immutable commit:** `834276e6ca543ba505f2455dd460b0b5195a6241`
- **Fixture:** `examples/polyglot-web` (3 requirements, 6 implementation tags in 4 source files, one unit-test file).
- **License:** Apache-2.0, independently checked in upstream `LICENSE` at that commit. Its Git blob SHA-1 is `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`.
- **Caveat:** This is an **authored trace-parser test fixture**. Its README explicitly says the languages do not form a sensible integrated application. It is **not** a held-out real production project, and does **not** provide executable conformance labels.

The script downloads exactly seven fixed files (license, spec, four source files and one unit-test file) by immutable commit and checks each file's Git blob ID. It does not execute or import any third-party code. The output includes per-file SHA-256, a length-delimited code/test snapshot SHA-256, the source commit, and the license proof. We do not vendor upstream code into this repository. Preserve upstream attribution and the Apache-2.0 license if redistributing the downloaded sources.

## Reproduce

From repository root with Python 3.11 and network access:

```bash
python -m pip install pytest==8.4.2
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m21_external_fixture.py
python -m backend.evaluation.m21_external_fixture --out-dir /tmp/m21-external
```

For a verified local checkout of the **exact upstream commit**, supply `--source-dir /path/to/flashtrace` to avoid the network. Each file is still hash-checked. The M21 GitHub Actions workflow publishes a 30-day artifact with `external_evidence.json`, `candidate_universe.json`, M20 `annotation/manifest.json`, `blind_queue.jsonl`, and two reviewer files.

## What is and is not measured

The author declared six requirement-to-implementation needs in the Markdown spec, corresponding to six source tags. Those six **observed** links are not independent gold. M20 creates a deterministic **12-pair** annotation sample from three requirements and six implementation components, combining observed, lexical-confusable and seeded-random candidates. The sample is deliberately *not* treated as a representative population estimate.

- **Available:** externally sourced immutable requirement texts, source paths, code component snippets, developer-declared trace links, file-level hash evidence, two blank reviewer templates.
- **Unavailable:** independent link adjudication, independently validated incorrect links, runnable requirement behavior, fault/conformance labels, per-project conformance accuracy, violation precision/recall, and coverage. These remain `null` in evidence; `research_95_eligible=false`.
- **Leakage caution:** M20 hides the *selection stratum* and M21 omits explicit tag IDs from candidate descriptions. However, original source files contain developer trace tags and source paths are meaningful. Reviewers must use a tag-masked source view and avoid seeing the coordinator manifest, author-declared links, or model predictions before submitting decisions.

## Exact independent review work remaining

1. Two independent annotators, blinded to author-declared links and model predictions, inspect all 12 pairs with requirement text and **tag-masked** source fragments, and record `link_label` plus file/line and rationale.
2. A separate adjudicator resolves disagreements; preserve raw reviewer labels and inter-annotator agreement. Do not infer negatives from absent upstream links.
3. Obtain multiple **genuinely different** permissively licensed real projects with requirements, fixed full source snapshots, and independently reviewed links. Two versions of Dronology are still **one project**, not two independent projects.
4. For each real project, create executable or otherwise independently validated conformance/violation cases with explicit expected behavior. Freeze the evaluation split before tuning.
5. Only then compute conformance TP/FP/TN/FN, ≥95% accuracy, ≥95% violation precision, ≥90% violation recall, abstentions, coverage and per-project results. A parser fixture cannot establish these targets.

**Why this milestone:** M20 previously produced only a synthetic annotation queue. M21 now exercises the same workflow on actual, pinned third-party source artifacts with verified license and source hashes. It intentionally does not add another accuracy gate or claim research completion.
