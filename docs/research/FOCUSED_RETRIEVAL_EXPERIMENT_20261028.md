# Focused recovery experiment — full-repository code retrieval (28 October 2026)

## Purpose

Stop adding incremental infrastructure. The strongest measured engineering limitation is that M42's *actual complete pip first-party source-tree retrieval* placed the historically known fix locus in the top five in only **2/6** correlated development cases (normalized lexical method). All 6 actual behavioral assessments abstained.

This experiment tests **one bounded, predeclared change to ranking**, leaving the M2/M42 baselines unchanged and retaining the historical fix locus **only as a post-ranking diagnostic**. It does not constitute new gold annotation, a held-out evaluation, or validation of 95% accuracy.

## Frozen methods

Source: both exact pinned historical pip revisions from M29, full `src/pip/_internal/**/*.py` Git-blob-verified tree, not a preselected file. Same 3 requirement-like descriptions at both revisions, source AST parsed as inert text, not executed.

Compare:

1. **M2 original:** existing unaltered `m42.rank_case(normalized=False)`.
2. **M42 normalized:** existing unaltered `m42.rank_case(normalized=True)`.
3. **Character TF-IDF:** tokenize source-derived `path + symbol name (twice) + signature + docstring + 1200 characters of source excerpt`, generic camel/snake segmentation, character word-boundary TF-IDF 3–5 grams, max 50,000 features, sublinear TF, cosine similarity, deterministic path/line/name tie-break.
4. **RRF normalized+character:** reciprocal rank fusion of M42 normalized and character TF-IDF top-ten lists with fixed k=60.

Implementation and all parameters were committed before the GitHub Actions real-source run. **No trained thresholds, issue-specific synonym dictionary, target path, `Factory` symbol name, code label, or version's expected behavior enters retrieval.** Only the post-ranking evaluation compares to the known historical source fix locus.

## Reproduction

```bash
python -m pip install 'pytest==8.4.2' 'numpy==2.2.6' 'scikit-learn==1.7.2'
python -m pytest -q backend/tests/test_focused_full_tree_retrieval.py backend/tests/test_m42_pip_first_party_tree_retrieval.py
python -m backend.evaluation.focused_full_tree_retrieval --out-dir /tmp/srs-focused
```

The command downloads static Git-pinned source from the public upstream via M29/M42; upstream Python is **never imported or executed**. Source Git hashes and license must match. Results: `/tmp/srs-focused/focused_retrieval_results.json`.

## Rules for interpreting results

- Report the actual top-1/top-5/top-10 **known fix-locus diagnostic** for all four methods even if new methods perform worse.
- Six observations share three scenarios, one real project and two correlated revisions. No CI count or top-five hit count is a statistical confidence estimate or measured production accuracy.
- The known historical source fix location is **not an independently adjudicated correct requirement-to-code trace link**.
- Conformance accuracy, violation precision/recall and automated decision coverage remain undefined; **95% success is not demonstrated**.
- If the fixed method fails to improve real-source retrieval, reject that algorithmic direction rather than add another benchmark gate or dashboard.
- If it improves this development case, treat it as a hypothesis: freeze the method and evaluate on independent, genuinely unseen, separately annotated projects **before** claiming generalization.

## Next action that cannot be automated away

Two independent reviewers and a separate adjudicator need to label real requirement-to-code and behavior cases, and authorized operator-approved, revision-matched runtime evidence must be collected. Without that, an honest empirical conformance score cannot be computed. The existing reviewer workflow is prepared; do not fabricate it.

**Paper:** The preliminary evidence-audited feasibility manuscript may be written now; do not claim validated 95% real-world conformance. This experiment is a development-only ablation, not a held-out paper result.
