# From Trace Links to Behavioral Claims: An Evidence-Grounded Feasibility Study of Requirement-to-Code Verification

**Status:** Working research manuscript, 28 October 2026. **Not submission-ready.** This is a bounded, evidence-audited preliminary study, not a report of independently validated conformance accuracy. No authorship, affiliations, approval, or peer review are implied.

## Abstract

Automatic requirements-to-code traceability is often mistaken for verification that an implementation satisfies a natural-language requirement. We investigate this distinction in SRS Guardian 2.0 through a reproducible, source-only feasibility study of a real historical regression in the MIT-licensed pip project. The existing Python abstract-syntax-tree (AST) indexer and BM25-style ranker, without retraining or tuning, were applied to three externally derived requirement-like scenarios across two pinned source revisions. We compare retrieved symbols with the known upstream fix locus solely as an exploratory diagnostic. The known fix locus was ranked first in **0/6** cases and within the first five in **0/6** cases. A separate AST-based source inspection identified the expected structural change between the revisions, but no upstream application code was executed. Accordingly, all **6/6** behavioral decisions were recorded as **insufficient evidence**. There are **zero independently adjudicated labels**, no untouched held-out projects, and **no measured conformance accuracy, violation precision, violation recall, or coverage estimate from independently labeled data**. We present this negative feasibility result, distinguish structural evidence from behavioral proof, and specify the minimum independent evidence required for a defensible future evaluation. The findings are limited to this deliberately selected development case and do not establish generalization or a novel verification algorithm.

**Keywords:** requirements engineering; source-code traceability; conformance verification; abstention; empirical software engineering; evidence provenance.

## 1. Introduction

A natural-language software requirement describes an intended property; a trace link identifies potentially relevant implementation code; a conformance claim asserts that the implementation actually satisfies that property. These are different statements. A file can be correctly linked to a requirement yet contain a defect, and a code snapshot can exhibit the expected syntax without establishing the behavior of a deployed system. Conflating the tasks risks presenting similarity rankings or static observations as verification results.

SRS Guardian began as an SRS document review tool and was extended with source indexing, lexical requirement-to-code retrieval, pinned external evidence, historical regression analysis, and independent-review handoff. The key unanswered question is not whether the tool can produce an attractive report or a reproducible evidence packet. It is whether the pipeline can recover implementation evidence and support a correct, independently verified behavioral verdict.

This working manuscript records the first narrow, real-source feasibility experiment from milestone M40 and audits what can and cannot be concluded. It does not claim that the observed retrieval failure represents the broader population of requirements, nor that the absence of runtime evidence proves the program nonconformant.

### Research questions

**RQ1 (retrieval feasibility).** When applied unchanged to externally authored issue/test-derived requirement-like statements, does the existing lexical retriever place the known historical fix locus among its highest-ranked symbols in the pinned pip development case?

**RQ2 (evidence sufficiency).** Which source-structure observations can be supported by the pinned code snapshots, and which behavioral conformance claims require independent runtime or equivalent trusted evidence?

**RQ3 (research readiness).** What independent labels, coverage definitions, frozen-baseline comparisons, and untouched projects are missing before claims about conformance accuracy, violation precision, and violation recall can be evaluated?

## 2. Related work and novelty boundary

Requirements traceability is an established research area, and retrieving candidate links is not a new contribution by itself. Guo et al. survey NLP for requirements traceability [1]. Keim et al. report trace-link recovery between architecture documentation and code using intermediate models, with results on five projects [2]. The 2026 R2Code preprint develops semantic alignment, self-reflective consistency checking, and adaptive retrieval for requirements-to-code *traceability* [3]. The 2026 industrial experience report by Zhou et al. explicitly addresses static checking of natural-language requirements against implementation using structured rules and LLM-based auditing [4]. The ARDoCo tool landscape also provides established interfaces for traceability workflows [5].

Consequently, neither 'retrieval + explanation' nor 'static code inspection against requirements' can responsibly be claimed as unique here. A potentially defensible future research contribution would be an independently evaluated, **evidence-calibrated, abstention-aware** distinction between (i) trace-link recovery, (ii) structural source evidence, and (iii) verified behavioral conformance. This remains a *hypothesis about a possible contribution*, not an established novel algorithm or demonstrated improvement.

The present manuscript is best characterized as a **reproducible preliminary/negative feasibility study**. It is not yet a strong full research-paper submission: it lacks an independent ground-truth benchmark, broad comparisons, and evidence of generalization.

## 3. Materials and provenance

### 3.1 Development case: pip

The case is the real, historical pip issue [#12372](https://github.com/pypa/pip/issues/12372) and corresponding upstream fix [#12392](https://github.com/pypa/pip/pull/12392). The M29 pipeline pins a pre-fix commit `9685f64fe8c78e1e39cd9b32e5615f42e0a01f1c` and a post-fix commit `417ca92b439dba33d707b5da2493358863256bc3`. It fetches and checks six exact Git-blob file/revision objects, including the MIT license, resolver source, and upstream tests. These snapshots were obtained as static text; the project itself was not imported, installed, or executed.

The requirement-like input consists of three scenario descriptions derived from upstream issue/test intent, each paired with both revisions (six retrieval queries). They are not an independently sampled population of SRS clauses. The upstream fix location, `Factory._make_requirements_from_install_req`, is used for **post-ranking diagnostics only**. A merged fix and upstream tests are credible historical artifacts but do not by themselves provide independently reproduced before/after runtime labels.

### 3.2 Other development evidence, not held out

Two further external projects are prepared for independent human review:

| Project | Public upstream historical evidence | Source license | Current evidence |
| --- | --- | --- | --- |
| Eclipse EDC | [Issue #2493](https://github.com/eclipse-edc/Connector/issues/2493), [fix #2494](https://github.com/eclipse-edc/Connector/pull/2494) | Apache-2.0 | Pinned Java before/after text; conditional pagination model; no independently reproduced runtime labels |
| pip | [Issue #12372](https://github.com/pypa/pip/issues/12372), [fix #12392](https://github.com/pypa/pip/pull/12392) | MIT | Pinned Python before/after text; structural AST witness; M40 retrieval diagnostic; no independent runtime labels |
| Werkzeug | [Issue #2422](https://github.com/pallets/werkzeug/issues/2422), [fix #2442](https://github.com/pallets/werkzeug/pull/2442) | BSD-3-Clause | Pinned parser/consumer/test text; independent-review seeds; no independent runtime labels |

The license claims are supported by the pinned license checks in the repository's M28, M29 and M37 tooling, not by an assertion that every transitive dependency has been audited. The three projects were all explored during development. **None is a genuinely untouched held-out project**, including Werkzeug.

### 3.3 Blinded review handoff

The M20 workflow creates candidate link judgments without inferring positive or negative labels from link existence, similarity, or sampling origin. M35/M38 generate reviewer-specific offline workspaces, and M39 prepares a third-party adjudicator handoff. The M39 evidence set contains **30 pending tasks**: 16 candidate links and 14 revision-specific behavioral cases, partitioned across EDC (8), pip (12), and Werkzeug (10). These are **review tasks, not labeled examples or confirmed violations**. No independent reviewer A/B submissions, independent runtime observations, or separate adjudicator decisions have been established in the verified artifacts.

## 4. Method

### 4.1 Frozen exploratory baseline

For the pip feasibility slice, the M2 Python AST indexer parses the pinned resolver and test source as inert text and extracts code symbols. The existing lexical BM25-style ranker receives each requirement-like scenario and returns a ranked list of symbols. No scenario ID, upstream fix location, post-fix label, or test assertion is inserted into the ranking query. The known fix locus is compared with the ranked output only after retrieval.

For each of the three scenarios and each of the two revisions, we record whether that locus appears at rank 1 or within the first five. **This is not trace-link accuracy**: the known fix locus is a historical diagnostic anchor, not a gold-standard exhaustive set of implementing code elements. The selected scenario family and repeated before/after revisions also mean the six observations are not independent projects or independent samples.

### 4.2 Static structural inspection

The existing M34 AST inspection analyzes the same pinned resolver function and checks for two structural elements: an explicit extras-free base requirement and a separate optional-extras requirement. The observed structural property is absent in the pre-fix revision and present in the post-fix revision. This is a property of source syntax and control-flow sites under the specified inspection, **not proof of dependency resolution, installation success, or general requirement satisfaction**.

The earlier EDC M30 model similarly makes conditional predictions from Java source-expression anchors for two pagination scenarios, but it does not execute Java. Its outputs are not runtime observations or adjudicated labels and are excluded from any accuracy calculation.

### 4.3 Behavioral decision policy

The three possible outputs are **conforms**, **violates**, and **insufficient evidence**. In the absence of approved, version-compatible behavioral observations or another sound proof method, the M40 pilot records **insufficient evidence** for all six requirement/revision pairs. This is an evidence-status decision, not a prediction that the code is correct or incorrect. No behavioral labels are inferred from issue descriptions, fix commits, static models, or reviewer seed files.

## 5. Verified results

The following values are taken from the successful first-party GitHub Actions job for the M40 branch, not from a new independent reproduction in this manuscript:

| Item | Result | Interpretation |
| --- | ---: | --- |
| External project in M40 feasibility experiment | 1 (pip) | Deliberately selected development case |
| Requirement-like scenarios | 3 | Issue/test-derived, not independent SRS sample |
| Requirement × revision cases | 6 | Three scenarios evaluated at two revisions |
| Git-blob-verified static file/revision objects | 6 | License, source, test text across revisions |
| Known fix locus at rank 1 | **0/6** | Exploratory retrieval diagnostic only |
| Known fix locus in top 5 | **0/6** | Exploratory retrieval diagnostic only |
| Source structural property | Absent before; present after | AST observation, not runtime proof |
| Behavioral conformance decisions | **0/6** | No evidence-backed conform/violate verdicts |
| Behavioral abstentions | **6/6** | All cases marked insufficient evidence |
| Independent adjudicated labels | **0** | No gold-standard outcome |
| Independently measured conformance accuracy | **Not measured** | Undefined, not zero and not 95% |
| Independently measured violation precision/recall | **Not measured** | Undefined |
| Independently validated conformance coverage | **Not measured** | No independently labeled denominator |
| First-party CI tests | **10 passed** | Engineering checks, not statistical accuracy |

The verified job is [GitHub Actions run 40646797570](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40646797570), associated with [draft PR #39](https://github.com/GoutamNandhen/SRS_Guardian/pull/39). The diagnostic artifact is [m40-pip-real-source-feasibility-NOT-GOLD](https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40646797570/artifacts/12798336237).

The result directly answers RQ1 for this limited setting: the unchanged retriever did not recover the known historical fix locus in its top five for any of the six queries. This is evidence of a **retrieval bottleneck in this selected case**, not evidence that all retrieval methods fail or that the code violates the requirements. RQ2 is answered only at the level of source structure and justified abstention. RQ3 remains an explicit research blocker.

## 6. Interpretation and limitations

**Construct validity.** A known historical fix location is not equivalent to an independently adjudicated set of valid requirement-to-code links. The scenario descriptions are requirement-like upstream statements, not a random sample of formal requirements. Static AST properties do not prove runtime conformance.

**External validity.** Only one selected project was evaluated with the unchanged retrieval baseline in M40. The same three scenario families appear at two revisions, so six cases must not be presented as six independent observations or a multi-project generalization.

**Ground-truth validity.** No two independent reviewers and separate adjudicator have produced verified labels. No version-matched approved runtime outcomes were supplied. Consequently, any numeric behavioral conformance accuracy, violation precision, or recall would be fabricated.

**Selection and leakage.** EDC, pip, and Werkzeug historical defects and fixes have already been inspected during development. None can serve as an untouched held-out test after method tuning. A new test-project split must be frozen before source or outcome inspection.

**Implementation scope.** The M40 baseline is an AST/BM25-style lexical retriever plus a separate source-structure witness. It is not a general semantic verifier, an execution-backed test generator, or an independently validated end-to-end verification model. Passing 10 first-party tests establishes only that the tested code paths and assertions passed in CI.

**Novelty.** Closely related 2024–2026 research already covers traceability recovery, semantic alignment, static requirement-aware code auditing, and developer interfaces [1–5]. This pilot does not demonstrate a new state-of-the-art method or improvement over those systems.

## 7. Independent evaluation protocol (future work; NOT completed)

1. **Choose a narrow eligible requirement class** before looking at new test projects: explicit, input/output-observable behavioral rules with a specified environment, fixture, and revision. Exclude broad nonfunctional claims unless independently verifiable.
2. **Recruit two independent reviewers and a separate adjudicator.** Reviewers examine blinded candidate links and evidence, with identity, timestamps, rationale, and exact pinned citations preserved. For behavior, require trusted revision-compatible execution records or a sound independent proof. Allow unknown labels.
3. **Freeze the verifier and baseline before accessing final projects.** Record source commit, retrieval configuration, rule extraction method, evidence thresholds, and output policy. Keep all development projects and their derivatives out of final testing.
4. **Acquire genuinely untouched permissively licensed projects** with independent requirement statements, pinned implementation snapshots, trace evidence, and authorized reproducible behavioral observations. Verify licenses and blob hashes. Do not execute third-party code in this workflow.
5. **Compare** lexical BM25, a predeclared semantic-retrieval baseline, and the proposed evidence-aware verifier under identical source and review conditions. Run an ablation without evidence checks or abstention. A comparison is meaningful only after the new method is implemented and frozen.
6. **Report project-level and pooled confusion matrices, abstentions, confidence intervals, and coverage.** Define positive as 'violation'. TP = predicted violation with gold violation; FP = predicted violation with gold conformance; FN = predicted conformance with gold violation; TN = predicted conformance with gold conformance. Keep gold-unknown cases outside scored denominators but report their count. Report *selective accuracy* on decided, gold-known cases and *coverage* as decided/gold-known cases; separately report full-population correct-decision rate where abstentions do not count as correct. Report conditional violation recall on decided cases and operational recall counting abstained gold violations as undetected, so abstention cannot inflate recall. Include per-project macro averages and uncertainty.
7. **Treat the desired thresholds as hypotheses:** >=95% conformance accuracy, >=95% violation precision, >=90% violation recall. Do not declare success from a small selected sample, an uncalibrated ranking, synthetic cases, or conditional static predictions.

The existing M20/M39 infrastructure is sufficient for the review handoff. Additional interfaces, benchmark gates, and visual dashboards are not justified until actual human review and trusted behavioral evidence arrive.

## 8. Research decision

**MODIFY / CONDITIONAL GO FOR WRITING; NO-GO FOR SUBMISSION AS A VALIDATED CONFORMANCE PAPER.**

A truthful preliminary manuscript can be drafted now, as this document demonstrates. A full paper claiming a novel high-accuracy requirement-to-code verifier **cannot** be supported by the current evidence. The most useful next empirical step is not another infrastructure milestone: it is independent adjudication and approved behavioral observation, followed by a frozen evaluation on genuinely unseen projects. A focused retrieval improvement on the already inspected pip development case may be attempted before freezing, but must be compared against the unchanged M40 baseline and cannot substitute for independent evaluation.

### Explicit publication boundary

Do not submit this draft as a completed accuracy or generalizable verification study. Its current scientific value is a reproducible negative feasibility result and an evidence-integrity analysis. Whether that is suitable for a particular workshop, experience report, or short-paper venue requires a separate venue-specific assessment and likely additional empirical evidence.

## 9. Reproducibility

Read [M40 experiment specification](M40_PIP_E2E_FEASIBILITY.md) and [M39 human handoff](M39_THREE_PROJECT_ADJUDICATOR_WORKBENCH.md). At commit `32aa390215e85ba0c6fdbbbb003646bb633742e0` (M40 head), with Python 3.11 and first-party tooling:

```bash
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m34_pip_source_structure_witness.py backend/tests/test_m40_pip_e2e_feasibility.py
python -m backend.evaluation.m40_pip_e2e_feasibility --out-dir /tmp/m40
```

The final command downloads **static pinned source text**, verifies Git-blob identity and license, and runs first-party parsing/ranking/inspection only. It does not execute upstream pip code. Network access is required for the pinned GitHub source fetch. The generated `/tmp/m40/pip_e2e_feasibility.json` contains per-case ranked candidates, source links, abstentions, and explicit null metrics. The CI run cited above is the currently verified execution record. This manuscript-only branch adds no new algorithm, dataset, or evaluation result.

## References

[1] J. L. C. Guo, J.-P. Steghöfer, A. Vogelsang, and J. Cleland-Huang, “Natural Language Processing for Requirements Traceability,” arXiv:2405.10845, 2024. https://arxiv.org/abs/2405.10845

[2] J. Keim et al., “Recovering Trace Links Between Software Documentation And Code,” *ICSE 2024*, DOI: 10.1145/3597503.3639130. https://ardoco.de/c/icse24

[3] Y. Wang et al., “R2Code: A Self-Reflective LLM Framework for Requirements-to-Code Traceability,” arXiv:2604.22432, 2026. https://arxiv.org/abs/2604.22432

[4] Z. Q. Zhou, D. Towey, and T. Y. Chen, “LLM-Based Static Verification of Code Against Natural-Language Requirements: An Industrial Experience Report,” arXiv:2605.17926, 2026. https://arxiv.org/abs/2605.17926

[5] J. Keim et al., “The ARDoCo Tool Landscape: REST API, TraceView, and TraceViz for Architecture Traceability,” *ASE 2026* Tools and Datasets Track. https://ardoco.de/c/ase26-tools

[6] pip upstream regression: https://github.com/pypa/pip/issues/12372 and https://github.com/pypa/pip/pull/12392

[7] Eclipse EDC upstream pagination regression: https://github.com/eclipse-edc/Connector/issues/2493 and https://github.com/eclipse-edc/Connector/pull/2494

[8] Werkzeug upstream parsing regression: https://github.com/pallets/werkzeug/issues/2422 and https://github.com/pallets/werkzeug/pull/2442

[9] SRS Guardian M40 code, test and CI: https://github.com/GoutamNandhen/SRS_Guardian/pull/39 and https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40646797570
