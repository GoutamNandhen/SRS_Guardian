# Codex task — produce SRS Guardian 2.0 IEEE-style research-paper package
**Date:** 28 October 2026
**Status:** Execution task for Codex. This file is a specification; the paper must actually be authored and built by Codex. Do not say it is finished until build and evidence checks complete.
**Working branch:** \`feature/srs-guardian-paper-codex-20261028\`
**Repository:** GoutamNandhen/SRS_Guardian (private)

## Objective — execute, do not just plan

Create a coherent, publication-style **preliminary empirical feasibility paper** based strictly on the repository's reproducible evidence. Use the existing 28-Oct manuscript as the primary authorial source; check its claims against CI and experiments; compose and compile a properly typeset IEEE two-column PDF, with genuine diagrams and valid citations. Finish a research-paper artifact TODAY. It is *not* academically honest to claim this project achieved the originally desired >=95% accuracy: no independent adjudications or untouched held-out behavioral scores are available.

Recommended title (retain unless evidence justifies a better one):
**From Trace Links to Behavioral Claims: An Evidence-Grounded Feasibility Study of Requirement-to-Code Verification**

Framing: bounded negative-results / feasibility / evidence-calibration empirical study. Distinguish **link retrieval**, **source structural witnesses**, **trusted behavioral observations**, and **independent conformance labels**. The primary contribution is an auditable experimental pipeline and a clear evidence sufficiency result, **not** a novel general-purpose semantic retriever or proven 95% classifier.

## Must-read, ground-truth repository files, in this order

1. \`docs/research/SRS_GUARDIAN_PRELIMINARY_MANUSCRIPT_20261028.md\` — complete working draft + M41–M45 correction appendix. Preserve its defensible facts, limitations, problem formulation, cited sources, research questions.
2. \`docs/research/M40_PIP_E2E_FEASIBILITY.md\`, \`backend/evaluation/m40_pip_e2e_feasibility.py\`, and its tests — frozen selected-case baseline, 0/6 historical known fix locus among top five, 6/6 behavioral abstentions (the historical fix locus is **not** independently adjudicated gold).
3. \`docs/research/M41_PIP_RETRIEVAL_ABLATION.md\` (if present; search exact M41 docs), \`docs/research/M42_PIP_FIRST_PARTY_TREE_RETRIEVAL.md\`, \`docs/research/M43_RETRIEVAL_GATED_WITNESS.md\`; distinguish M41's **oracle-selected file** success (6/6 top-five only inside preselected file) from actual M42 **whole-tree** normalized retrieval (2/6 top-five, top-one 0/6) and M43 2/6 static witnesses, all behavioral abstentions.
4. \`docs/research/M6_EXTERNAL_DATASET_VALIDATION.md\`, \`benchmarks/m6/observed_metrics_summary.json\` and \`docs/research/M7_HYBRID_RETRIEVAL.md\` — external Dronology artifact-graph known-positive link retrieval, *not* link-classification accuracy and not executable conformance. M6 V0/V1 only 8/10 linked requirement IDs. M7 path/character retrieval ablation on the same one-project dataset. If used, report Hit@5 with exact provenance and caveats.
5. \`docs/research/M4_APPROVED_EXECUTION.md\` plus \`backend/app/research/approved_runner.py\`, \`backend/app/research/m4_worker.py\`, \`backend/evaluation/m8_docker_e2e.py\` — approved trusted Docker target demonstration, *not* upstream project conformance.
6. \`docs/research/M28_HISTORICAL_PAGINATION_REGRESSION.md\` or search the exact M28 docs; M29 pip, M34, M37–M39 — selected source review and pending adjudication artifacts only.
7. \`docs/research/M44_REQUESTS_INDEPENDENT_REVIEW.md\`, \`M45_REQUESTS_INDEPENDENT_BEHAVIOR_PROTOCOL.md\`, \`M47_APPROVED_REQUESTS_REVIEWER_CAPTURE.md\`, \`M48_REQUESTS_OBSERVATION_HANDOFF.md\` — requests pinned issue review and offline observation pipeline. **M47/M48 first-party tests use synthetic/stubbed observations. No actual approved upstream Requests run, human submission, or adjudicated case is reported.**
8. \`docs/research/M1_EVALUATION_PROTOCOL.md\`, \`docs/EVALUATION.md\` — original SRS text-quality benchmark scores, **different tasks** from M40/M43 or conformance, never aggregate these numbers into 2.0 accuracy.

If a listed document filename is not present, find the corresponding M-number's actual docs with \`git ls-files docs/research\`; record the resolved path. Do not quietly substitute unsupported claims.

## Evidence table that MUST be correctly interpreted

| Study | Confirmed observation | Exact restriction |
|---|---|---|
| M6 published Dronology artifact graph | V0 known-link Hit@5 full-path BM25 37.5%; V1 40.0% | One project in two versions, Java file paths, positive-only observed links; no TN/precision/conformance |
| M7 char n-gram subword experiment | V0 Hit@5 50%; V1 60% | Same observed-positive Dronology corpus, small linked counts; not M2 Python AST or behavior |
| M8 approved synthetic Docker E2E | Conforming and deliberately buggy trusted FastAPI fixtures classified as expected; frontend build passed | Fixed development fixture, not independent real-project conformance |
| M40 selected pip development case | Known fix locus top-5 0/6, top-1 0/6; behavior abstained 6/6 | 3 correlated requirement-like scenarios x 2 pinned revisions; not independent annotations |
| M41 restricted file | With source-only and general inflection normalization top-5 fix locus 6/6 | Preselected fix-containing file (oracle-restricted scope); no generalization |
| M42 pip complete source tree | Whole-tree normalized top-5 2/6 and top-1 0/6 | Real pinned pip source; 6 correlated inspected development cases, not held-out |
| M43 retrieval-gated static witness | Source-pattern witness on 2/6, 6/6 behavioral abstentions | Static structural finding is not executed behavioral proof |
| M44–M48 Requests reviewer workflow | Pinned source/fixture/hand-off; latest first-party M48 11 tests passed | **0** approved independent upstream runtime observations; **0** human reviews; **0** adjudications |
| Independent conformance accuracy / violation precision / recall / coverage | **Undefined / not measured** | Never print 0% or 100% as substitute; desired 95% accuracy remains an unachieved target |

Verification examples (inspect current code/CI for exact run and source claims):
- M40: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40646797570
- M41: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40653203716
- M42: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40660538656
- M43: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40668241565
- M44: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40675475047
- M45: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40683594611
- M47: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40691470280
- M48: https://github.com/GoutamNandhen/SRS_Guardian/actions/runs/40701092905

## Paper scope and mandatory content

Produce a technically coherent **6–9 page target** in IEEE two-column format (page count is a layout target, not license to pad or fabricate). A strong outline:
1. Abstract (structured with the verified negative result, explicit abstention and no accuracy claims)
2. Introduction and problem statement; differentiate trace existence vs actual conformance
3. Related work and novelty boundary (traceability, static verification, evidence-based assessment); verify each bibliographic record
4. SRS Guardian 2.0 workflow and threat/evidence model (requirements extraction, candidate retrieval, human review, static witness, approved isolated behavior, source/evidence provenance)
5. Research questions and precise evaluation protocol (dataset, pinned versions, observable outcomes, partial labels, no false negatives invented)
6. Real external evidence and frozen experiments (M6/M7 and focused M40–M43); **separate their tasks in figures and tables**
7. Qualitative case analysis of retrieval failure and correctness of abstention policy
8. Evaluation limits, threats to validity, research ethics, scientific decision
9. Reproducibility and next steps: independent reviews, cross-project heldout tests
10. Conclusion (negative bounded feasibility result; no claimed 95%).

Include useful artifacts:
- 1 **original source-derived architecture pipeline diagram** (TikZ/vector) showing the actual boundaries and what is implemented.
- 1 **evidence-gate / decision flow** showing candidate, source witness, execution, evidence, unsupported/abstain.
- 2–4 **compact tables** with genuine metric values and explicitly separate task categories.
- Optional bar chart built only from measured non-comparable Hit@5 retrieval results, clearly labeled as *different retrieval experiments*.
- No invented UI screenshots, generated screenshots pretending to be implementation, fake system accuracy, fabricated data/images, fake survey answers or fake quotes.
- No duplicate material, large whitespace gaps, cut-off tables, or tiny unreadable captions.

## Output files (all required)

Write into \`paper/srs_guardian_feasibility_20261028/\`:
- \`main.tex\` — complete IEEEtran conference-style LaTeX source, no "TODO" or unfilled references
- \`references.bib\` — **verified** bib entries with actual bibliographic metadata; use official publisher/arXiv/GitHub links; omit unverified references
- \`figures/architecture.tex\`, \`figures/evidence_gate.tex\` — vector TikZ diagrams integrated in paper, fit columns
- \`paper.pdf\` — successfully rendered final PDF, if TeX engine available in Codex environment
- \`EVIDENCE_AUDIT.md\` — claim-to-actual-file/test/CI link matrix, status labels VERIFIED / QUALIFIED / UNSUPPORTED; no unsupported claims in paper
- \`BUILD.md\` — precise reproducible build command (e.g. \`latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex\`); report whether TeX actually ran
- \`MANUSCRIPT_REVIEW.md\` — remaining academic limitations, citation verification status, suitability verdict, page count if built, all build warnings.

If LaTeX is unavailable, **still create all source files**, report failed/missing engine accurately and DO NOT invent the PDF. If feasible, install/use an allowed local TeX engine, and compile. Do not substitute a PNG for the editable diagram. Never mark a PDF built unless its file exists and opens.

## Hard scientific rules

- Zero invented measurements or confidence intervals. Avoid made-up respondents, authors, institutions, datasets, tables, figures, p-values and citations.
- **Do not manufacture independent labels.** Human adjudications currently zero. Historical commits and issue reporters are *development hints*, not gold.
- No merging into main. Work only in this dedicated paper branch.
- Do not execute historical or untrusted external projects to create apparent evidence. First-party tests and verification of existing CI are allowed.
- Preserve the "NO-GO for claimed >=95% conformance verification" boundary. The manuscript can be complete as a *preliminary feasibility study* while not satisfying a full empirical-accuracy publication claim.
- Academic integrity: use original prose from our actual project evidence, distinguish prior research and cite it; do not promise any Turnitin AI percentage or try to disguise authorship.
- If authors/affiliations have not been explicitly specified in the repo, use normal **anonymous submission mode**; do not invent authors. No placeholder emails or school names.
- Claims such as "statistically significant", "robust", "automated end-to-end real-project conformance" require real evidence; otherwise remove.
- Ensure equations reflect implemented algorithms, label any conceptual extensions as proposed, not implemented.
- Preserve source revision and branch provenance; do not use today as an experiment date for older run data.
- Run lint/build checks; inspect produced PDF for overfull hboxes, missing glyphs, citations, clipping, and figure/table placement. Correct issues.

## Execution protocol — Codex must do this in this session

1. Inspect git status/branch and source/evidence inventory. If branch dirty, avoid overwriting unrelated work.
2. Read source manuscript and exact evidence files. Construct a compact claim registry with primary file/CI link and interpretation.
3. Verify only the bibliography entries actually used (do not trust manuscript's references blindly). Keep publication claims conservative.
4. Write complete paper and original vector diagrams; compile locally if TeX available. Repair errors, avoid unnecessary page padding.
5. Record an unambiguous **GO/NO-GO decision**: GO for evidence-audited preliminary manuscript draft; NO-GO for full-paper submission claiming >=95% independently validated conformance.
6. Commit outputs to the paper branch with a clear message. **Do not merge**.
7. In final response, give exact paths, PDF presence or absence, number of pages if generated, source links, any citations not verified, and outstanding evidence blockers. Do not reply with only an outline or a promise.

## Final acceptance test

The final manuscript must be scientifically defensible **even if reviewers reject any claim that requirements-to-code matching demonstrates runtime conformance**. If a sentence only works when an unjustified accuracy claim is assumed, delete or qualify it. A correct negative result is a stronger paper than a fabricated success claim.
