# M41 — Pinpoint the M40 retrieval bottleneck without new evaluation gates

## One bounded question

M40 found the known upstream pip fix locus at top-1 **0/6** and top-5 **0/6** when its M2 lexical ranker searched both resolver implementation symbols and upstream test functions. Is that failure partly caused by (a) mixing test functions into the implementation candidate pool and (b) basic word-form mismatch ("installing" versus "install")?

## Design

Use the exact six M29 hash-verified, MIT-licensed static pip file/revision objects. Compare three predeclared ranking variants on the same three upstream-authored requirement-like descriptions at the same two revisions:

1. **M40 unchanged:** resolver and test symbols together, original M2 tokenizer and BM25-style ranker.
2. **Code-only:** the same M2 ranker and tokenizer, but exclude upstream test functions from implementation candidates.
3. **Code-only + general inflection normalization:** additionally normalize '-ing' and '-ed' forms on both query and indexed tokens; no case-specific synonym dictionary.

The known historical fix locus is checked **after ranking only**. No source file is executed or imported. The M34 static structural observation and M40 behavioral abstention policy remain unchanged. These ablations are experimental; they do **not** change the deployed production retriever.

**Critical validity limitation:** M29/M40 intentionally fetched only the pip `factory.py` implementation file and one test file, and `factory.py` was already known to contain the fix. Code-only ranking therefore uses an **oracle-preselected source file**, not the full pip repository. Improved top-5 ranks, even 6/6, would be an explanatory diagnostic about candidate contamination and tokenization—not valid whole-repository retrieval performance, traceability accuracy, or conformance verification. The six observations are correlated within one historical development case.

## Reproduce

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m34_pip_source_structure_witness.py backend/tests/test_m40_pip_e2e_feasibility.py backend/tests/test_m41_pip_retrieval_ablation.py
python -m backend.evaluation.m41_pip_retrieval_ablation --out-dir /tmp/m41
```

Outputs: `/tmp/m41/m41_retrieval_ablation.json` and `/tmp/m41/README.md`. The CI workflow repeats the ablation on actual Git-blob-verified static source. First-party tests use constructed snippets.

## Research status and next decision

The real source license, immutable commits, Git-blob hashes, upstream issue and merged fix are inherited from M29 and verified before ranking. None of those constitutes independently adjudicated ground truth.

- Independent link or behavioral adjudications: **0**.
- Trusted revision-matched runtime observations: **0**.
- Independently measured conformance accuracy, violation precision, violation recall, coverage: **not available**.
- Held-out project evaluation: **not performed**.
- All six behavioral outcomes: **insufficient evidence**.

If code-only ranking helps, the next genuinely high-impact task is to test a predeclared implementation-file selection strategy on a **whole repository** rather than an oracle-selected file, then freeze it. If it does not help, revisit representation and retrieval architecture. Neither outcome justifies a behavioral accuracy claim. Independent M20 reviewers, separate adjudicator and approved runtime observations are still required.

No new reviewer UI, benchmark gate, synthetic labels, merges, or changes to main.
