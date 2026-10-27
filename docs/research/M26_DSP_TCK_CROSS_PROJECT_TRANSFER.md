# M26 — Frozen M25 source retrieval transferred to Eclipse Dataspace TCK

**Status:** external static-source evidence and M20 annotation queue. NOT independent conformance validation.

## Why this project

The [Eclipse Dataspace TCK](https://github.com/eclipse-dataspacetck/dsp-tck) is a separate, externally authored Apache-2.0 project containing real mandatory Java protocol-compliance test implementations. This pilot uses **four README module descriptions** (metadata, catalog, contract negotiation, transfer process) and **five Java compliance-test classes**. They are not normative behavioral requirements and the tests are not the connector implementation. This is a requirement/test-traceability *preparation* step, not an executable conformance experiment.

Source repository is pinned at commit \`61bc3d2d7f81bd5b1eee164621872fd6808eb185\` (2026-10-26). Eight allowlisted static files include README, LICENSE, NOTICE and five Java test classes. Exact expected Git blob hashes are in \`backend/evaluation/m26_dsp_tck_transfer.py\`. The repository's LICENSE and NOTICE declare Apache-2.0, and all five selected Java classes contain Apache-2.0 SPDX headers. The upstream repository is not built or executed.

## Design and scope

The README names the four protocol modules and their verification packages. Their five **documentation-derived package associations** are recorded only as **unverified observations**, not as independently adjudicated trace links. Every one of the 4×5=20 possible module/class pairs is placed into an M20 blinded review queue; two independent reviewer templates are empty. The reviewer artifact contains source URLs and hashes, but no sampling origins, observed-link universe or ranking scores.

The M25 character 3–5gram source-content TF-IDF method is reused unchanged, together with the M7 path-only BM25 and hybrid methods. It was developed on TeaStore, not this project, so the new corpus offers a **limited cross-project transfer check** on documentation-derived associations. It is *not* a valid held-out conformance test or representative retrieval benchmark: project and cohort selection are purposive, and the observed links have not been adjudicated.

## Reproduce

\`\`\`bash
python -m pip install 'pytest==8.4.2' 'scikit-learn==1.7.2'
python -m pytest -q backend/tests/test_m20_annotation_queue.py backend/tests/test_m23_teastore_external.py backend/tests/test_m24_cross_corpus_baseline.py backend/tests/test_m25_source_grounded_teastore.py backend/tests/test_m26_dsp_tck_transfer.py
python -m backend.evaluation.m26_dsp_tck_transfer --out-dir /tmp/m26
\`\`\`

Only pinned static source text is downloaded and parsed; no external Java code runs. The output separates \`reviewers/\` (blind queue, reviewer_A/B templates, source index) from \`internal/\` (unverified association provenance and retrieval scores).

## Independent review and conformance blocker

Two independent reviewers must inspect **all 20 module-to-test associations**, cite exact Java source lines and README text, mark linked/not-linked/uncertain, and have a third person adjudicate disagreements. The reviewer packet must remain separate from internal observations until labels are frozen. These judgments only establish module-to-test links.

For **real requirement-to-code conformance** we additionally need externally authored normative behavioral requirements, pinned connector implementation revisions, independent evidence of compliant and violating behavior, and adjudicated unseen-project labels. No unreviewed or missing link is a negative. Conformance accuracy, violation precision, violation recall and coverage remain **null**; the ≥95%/≥95%/≥90% research thresholds are not established.

The Zenodo EDC RTM at https://zenodo.org/records/17546974 has EARS-style requirements and compliance test references but its exact dataset reuse license, mapping semantics, and implementation snapshots were not confirmed here; it is **not** incorporated as eligible ground truth.
