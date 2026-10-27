# M7: Subword + lexical retrieval experiment (external observed links)

**Status:** Predeclared exploratory ranking comparison. **Not a 95% result.**

## Task and evidence boundary

SRS Guardian's M2 indexes Python source AST, whereas the external Dronology fixture used in M6 has published **Java file path names** and incomplete *observed positive* requirement-to-path links. M7 intentionally evaluates only path-name retrieval, not Python AST matching or actual code behavior.

The source is `benchmarks/m6/dronology_observed_trace_links.json`, derived with attribution and original MIT license from SAREC-Lab/SAFA-Artifacts. It comprises two versions of the **same project** and therefore is not a valid independent-project generalization benchmark. Missing artifact links are not negatives. No false-positive rate, pairwise accuracy, full conformance or '95%' claims follow from the numbers.

## Fixed configurations (not tuned to the outcome)

- `filename_bm25`: M6 filename-token baseline.
- `path_bm25`: M6 full-path token baseline.
- `char_tfidf`: scikit-learn TF-IDF character word-boundary n-grams 3–5, normalized candidate path tokens, cosine similarity. No model checkpoint or external API.
- `hybrid_rrf`: equal-weight reciprocal rank fusion of path BM25 + filename BM25 + char TF-IDF, `k=60`. All weights are predetermined and outcome-independent.

Ranking rejects queries with no matching subwords rather than filling results alphabetically. No gold link fields enter the query representations, vocabulary fit, or ranking calculation. Dataset links are only used after rankings are produced to calculate metrics.

## Metrics and comparison

Report Hit@1, Hit@5, Hit@10 (retrieval of **at least one observed known-positive** path), MRR for first known-positive, and mean known-positive recall@5. Include the number of unobserved-link requirements excluded from the scored numerator and denominator, per-version Wil­son intervals, and paired hit@5 gains and regressions.

Both V0 and V1 are exploratory; even if V1 is chosen after inspecting V0, it does **not** provide an unseen-project test. No tuning is permitted on these artifacts to certify a research accuracy target. CI checks that `research_95_eligible` always remains false.

## Reproduce

```bash
python -m pip install scikit-learn pytest
python -m pytest -q backend/tests/test_m6_external_trace.py backend/tests/test_m7_hybrid_retrieval.py
python -m backend.evaluation.m7_hybrid_retrieval \
  --dataset benchmarks/m6/dronology_observed_trace_links.json \
  --output /tmp/m7_external_results.json
```

The JSON output preserves per-requirement results for methodological audit. No datasets or run outputs in this milestone may support a paper claim about 95% executable conformance.

## Exit criteria toward research paper

1. Acquire at least three distinct, licensed source repositories with requirement→actual implementation mappings. Annotate missing links and negative candidate pairs independently; track annotator agreement.
2. Evaluate the actual **M2 Python AST** ranker against reviewed Python repositories, together with real code-aware embeddings and structural traceability features.
3. Establish deployed-revision identity and executable behavioral tests through M4, with legitimate expected-response oracles and independent bug labels.
4. Split train/validation/test by **project** and freeze the test set. Report precision, recall, F1, accuracy, macro per-project values, abstention coverage and uncertainty, and no leakage.
5. If reported 95% is reached only on a narrow class, state scope and coverage plainly; do not generalize to arbitrary SRS verification.
