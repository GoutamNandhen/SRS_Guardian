# M40 — Real-source end-to-end feasibility, not another evaluation gate

## Research uncertainty

Can the **existing** SRS Guardian M2 Python AST/BM25 retriever locate the known
upstream fix locus from independently authored requirement-like issue/test
statements, and can the existing M34 source inspector produce a useful,
source-linked structural observation without pretending to verify runtime
behavior?

This is a **single exploratory development experiment**, not a held-out
evaluation. It changes no model, ranking weights, evaluation thresholds,
annotation interface, or benchmark gate.

## Experiment

1. Fetch the existing M29 pinned before/after MIT-licensed pip source, tests,
   and license; verify six exact Git blobs. Download static text only.
2. Index both Python source files with the **existing M2 AST indexer** and
   rank candidate symbols with its unchanged lexical BM25-style method. Do
   not inject the upstream fix locus, labels, or test results into the query.
3. Compare ranked candidates **after retrieval** against the known
   historical fix locus `Factory._make_requirements_from_install_req`.
   Report top-1/top-5 **diagnostic retrieval counts**, not traceability
   accuracy or independently validated links.
4. Run the **existing M34 AST structural inspection** on the exact pinned
   source. It distinguishes one combined requirement-yield site before the
   fix from a separate extras-free base and optional extras yield afterward.
   This is a source-structure observation, not an installation outcome.
5. For all three requirement scenarios and both revisions, output
   `insufficient_evidence` for **behavioral conformance**. Report
   the source links, retrieval ranks, and exact missing evidence.

## Reproduce

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m34_pip_source_structure_witness.py backend/tests/test_m40_pip_e2e_feasibility.py
python -m backend.evaluation.m40_pip_e2e_feasibility --out-dir /tmp/m40
```

Outputs: `/tmp/m40/pip_e2e_feasibility.json` and `/tmp/m40/README.md`.
The CI workflow repeats the experiment on actual Git-blob-verified upstream
source. Local tests use constructed snippets and are engineering tests only.

## What would change the approach?

- If the real M2 ranker fails to retrieve the known fix locus in top-5,
  prioritize retrieval diagnosis rather than more annotation interfaces.
- If the locus is retrieved but behavioral outcomes remain unknown, do
  not improve retrieval to claim conformance: the bottleneck is **runtime
  evidence and independent labels**, not retrieval.
- Even when the M34 source property is present, never infer successful
  dependency installation. Source syntax alone cannot establish it.

## Research integrity and next blocker

The pip issue and post-fix tests are **not independent gold**. All six
behavioral cases abstain; independent adjudications: **0**; conformance
accuracy, violation precision/recall, and coverage: **null**. This known
historical project has already been examined; it is not a held-out project.

Reuse the existing **M20/M35/M39** packets, not new reviewer infrastructure.
Two independent reviewers must assess the six candidate requirement-to-code
links and six behavior/revision cases each. For behavioral cases they need
approved version-compatible execution logs or independently reproduced
observations, environment/fixture provenance, and explicit abstentions when
the evidence is inadequate. A separate adjudicator records final decisions.
Only after that should a frozen verifier be evaluated on genuinely unseen
projects. Do not execute upstream pip here.

This branch is stacked on M39, remains draft/unmerged, and does not touch main.
