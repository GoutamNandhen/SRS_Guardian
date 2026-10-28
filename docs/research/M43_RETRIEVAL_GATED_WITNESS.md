# M43 — Retrieval-gated source witness (development feasibility, NOT GOLD)

## Decisive uncertainty

M40 inspected the known historical pip fix location even when lexical retrieval failed. M42 established that, across all 147 first-party Python implementation files, the normalized ranker found the known fix locus in the top five in only 2/6 correlated development cases. A verifier cannot silently inspect the oracle fix file after retrieval misses it.

## Bounded implementation

M43 connects **M42 whole-first-party-tree retrieval** to the existing **M34 specialist AST source-pattern witness**. It attempts that witness only if the normalized ranker retrieves the predeclared resolver symbol in the top five. The known symbol is not inserted into the query or ranking. Both before/after AST patterns are attempted without passing the actual revision label to the recognizer. Source citations use the actual pinned revision after structural recognition.

If retrieval fails or the AST pattern cannot be recognized, no source witness is emitted. In every case, behavioral conformance **abstains**, because source syntax does not establish actual package installation.

This is a previously inspected pip regression and a deliberately **bug-specific source checker**, not general-purpose requirement verification. No external code is executed.

## Reproduction

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m34_pip_source_structure_witness.py backend/tests/test_m40_pip_e2e_feasibility.py backend/tests/test_m41_pip_retrieval_ablation.py backend/tests/test_m42_pip_first_party_tree_retrieval.py backend/tests/test_m43_pip_retrieval_gated_witness.py
python -m backend.evaluation.m43_pip_retrieval_gated_witness --out-dir /tmp/m43
```

The command fetches only pinned static GitHub source files/ZIPs and verifies source hashes and the MIT license before AST parsing. The artifact includes a per-case ranked top-five list, source-pattern witness status, exact pinned citations and explicit abstentions.

## Scientific interpretation

Report **source-witness cases out of six** as an exploratory development diagnostic, not conformance accuracy, violation precision, recall, or independent coverage. The three scenario families across two revisions are correlated and already exposed. The M20 requirement-code links and behavioral cases remain unadjudicated.

## Exact independent review blocker

Two independent human reviewers must assess legitimate behavioral requirements, evidence-backed trace links and revision-compatible behavior for each case using approved observations; a separate adjudicator must reconcile decisions. Freeze the verifier and obtain genuinely untouched external projects before measuring conformance accuracy, violation precision, violation recall and coverage. Do not submit a 95% performance claim without that evidence.
