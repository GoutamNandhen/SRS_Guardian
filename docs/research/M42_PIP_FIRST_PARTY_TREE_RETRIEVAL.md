# M42 — Remove the oracle file selection from the real pip retrieval experiment

## Research uncertainty

M41 improved the rank of the known pip fix locus from 0/6 to 6/6 within top five **only after restricting retrieval to the known fix-containing factory.py file**. That is an oracle file scope. M42 tests whether that diagnostic survives a realistic candidate pool.

## Predeclared experiment

At the **same two immutable pip revisions** from M29, retrieve the upstream Git commit tree and ZIP snapshot. Enumerate **every** first-party Python file under `src/pip/_internal/` from the Git tree. Verify each archive file's exact Git blob SHA-1 against the tree before indexing. Independently reverify the pinned MIT license, original resolver and upstream test evidence using M29. Do not execute, import or install any upstream source.

Parse each verified first-party Python file as inert AST text. Rank the **complete first-party implementation symbol pool**, without preselecting `factory.py`, using (a) the original M2 lexical ranker and (b) the M41 generic inflection normalization. Neither variant uses the known fix symbol, upstream labels, or test assertion in ranking. Check the historical fix location **only after** ranking. Record per-revision file/symbol counts and top-ten ranked source citations for each of three issue/test-derived scenarios at both revisions.

## Validity boundaries

- **Development experiment only:** one previously inspected pip historical issue and three correlated scenarios at two revisions.
- **No oracle fix file selection**, but the source scope is pip's complete first-party `_internal` Python implementation tree, not all vendored libraries or test code.
- The known fix locus is a post-hoc historical diagnostic, **not** independently adjudicated traceability gold.
- No behavioral runtime observation, independent annotation, or held-out project evaluation. All six conformance decisions abstain.
- **No conformance accuracy, violation precision, violation recall, or independent coverage is computed.** Even a high top-five score would not be conformance accuracy.
- No source execution, synthetic-as-real results, new reviewer UI, or changes to main.

## Reproduction

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m40_pip_e2e_feasibility.py backend/tests/test_m41_pip_retrieval_ablation.py backend/tests/test_m42_pip_first_party_tree_retrieval.py
python -m backend.evaluation.m42_pip_first_party_tree_retrieval --out-dir /tmp/m42
```

Requires public HTTPS access to GitHub's API, codeload and raw static files. Produces `/tmp/m42/m42_first_party_tree_retrieval.json` and `/tmp/m42/README.md`. CI uploads the artifacts and independently checks the abstention/metric-null contract.

## Next decisive blocker

Obtain independently reviewed M20 labels and trusted revision-compatible behavioral observations, then freeze the verifier and evaluate on **untouched projects**. Do not tune to these already-inspected pip cases and present them as held-out.
