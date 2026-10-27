# M25 — Source-grounded TeaStore retrieval and blinded review packet

This is exploratory **trace-link retrieval**, NOT requirement-to-code behavioral conformance. M24 measured source-path matching only. M25 reads five pinned Java source bodies and compares source-content character 3–5gram TF-IDF with M7 path BM25 and hybrid RRF. Ranking never sees observed links; scoring uses six published, unverified links over three selected architecture statements.

## Pinned external provenance

- Documentation and published links: ArDoCo/Replication-Package-ICSE24_Recovering-Trace-Links-Between-Software-Documentation-And-Code at a4b221733fb43938f130636db8d5434bd30ec28d; pinned package MIT license.
- Java source: ArDoCo/TeaStore at bdc49020a55cfa97eaabbb25744fefbc2697defa; pinned Apache-2.0 license.
- M23 verifies exact Git blob hashes of eleven static files, including both licenses. M25 adds SHA-256, source-line counts, and pinned GitHub URLs to the reviewer-only source index.
- Rights in third-party architecture documentation have not been fully cleared. Do not redistribute that documentation beyond authorized review without resolving rights.

## Reproduce from the M25 feature branch

~~~bash
python -m pip install 'pytest==8.4.2' 'scikit-learn==1.7.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m23_teastore_external.py backend/tests/test_m24_cross_corpus_baseline.py backend/tests/test_m25_source_grounded_teastore.py
python -m backend.evaluation.m25_source_grounded_teastore --out-dir /tmp/m25
~~~

This downloads and parses only hash-pinned static text. No third-party code is imported, built or executed. CI uploads separate reviewer-only and internal evidence artifacts.

## Human review protocol

The reviewer-only artifact contains blind_queue.jsonl, reviewer_A.jsonl, reviewer_B.jsonl, source_index.json and README.txt. It excludes published-link origin, M20 sampling provenance and ranking scores.

**All 15 pairs remain pending.** Two independent annotators must inspect the exact pinned architecture sentence and Java source, record linked/not-linked/uncertain with specific cited code lines, and a third adjudicator must resolve disagreements. Unpublished links are UNKNOWN, not presumed negatives. Do not expose the internal artifact to reviewers before their first decisions.

## Interpretation

Hit@K is the share of three observed-linked architecture statements with at least one published link retrieved in the first K. Observed-positive recall@K is the share of six published links retrieved in the first K. The five-file candidate universe saturates at K=5. These are not conformance metrics.

The source-content method was designed after inspecting M24 TeaStore results. This is a **development-set** experiment, not independent held-out validation, even if measured retrieval improves. No adjudicated true negatives, executable behavioral requirements, conforming/violating code revisions or independent project-level conformance labels exist. Conformance accuracy, violation precision, violation recall and coverage remain NULL.

## Next blocker

Independently adjudicate the 15 links, then acquire real behavioral requirements and independently verified conforming/violating revisions from multiple distinct unseen projects. Freeze methods before project-held-out scoring and report per-project TP/FP/TN/FN, abstentions, accuracy, violation precision/recall and coverage.

**Future source candidate:** The [Eclipse Dataspace Connector requirements-to-test matrix](https://zenodo.org/records/17546974) contains EARS-style requirements and compliance test references, and [Eclipse Dataspace TCK](https://projects.eclipse.org/projects/technology.dataspacetck) is an Apache-2.0 project. The matrix's specific reuse rights, exact code/test revisions and mapping semantics have not been established. It cannot yet be treated as licensed independent conformance ground truth.
