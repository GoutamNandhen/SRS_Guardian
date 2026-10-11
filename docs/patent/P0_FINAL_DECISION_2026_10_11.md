# SRS Guardian — Patent-first Decision Report
**Date:** 11 October 2026  
**Status:** Internal feasibility screening. **Not** a patent search certification, legal opinion, patent application, or validated novelty claim.  
**Scope:** Existing SRS Guardian; proposed evidence-preserving incremental requirement verification.

## 1. Executive recommendation

**GO** for an **8–12 day, strictly bounded proof-of-concept and invention-disclosure consultation**.  
**NO-GO** for filing the present broad claim about 'AI + incremental verification + graph + formal constraints'.  
**CONDITIONAL GO** for later filing only if an India-qualified patent professional finds a sufficiently specific, novel, non-obvious technical mechanism with eligible subject matter and the project demonstrates it with credible evidence.

The current likely failure mode is not coding difficulty; it is existing intellectual property and incomplete natural-language dependency understanding. Reusing old verification records after an edit can silently hide contradictions. Our separate negative tests reproduce this problem.

## 2. Existing SRS Guardian components actually inspected

Repository: `GoutamNandhen/SRS_Guardian` (private at time inspected). P0 branch: `research/p0-patent-feasibility`. Unchanged production main.

- `backend/app/ml/embeddings.py`: all-MiniLM-L6-v2, SHA-256 text hashes, persistent embedding cache.
- `backend/app/ml/contradictions.py`: BART-large-MNLI model, pair blocking, cached/on-demand verification, optional attribution.
- `backend/app/nlp/numeric_constraints.py`: typed numeric constraint extraction and interval conflicts.
- `backend/app/ml/duplicates.py`: embedding similarity and phrase-level attribution.
- `PROJECT_STATE.md`: version comparisons, human review, Gherkin skeletons, EARS, ISO-oriented checks and reporting.
- `docs/EVALUATION.md`: held-out PROMISE_exp classification accuracy 85.05%, macro F1 84.55% (194 test requirements), ambiguity F1 74.42%, duplicate best F1 86.67%, integrated contradiction F1 73.17%. These metrics measure different problems. No validated system-wide 95% figure.

### Never present existing techniques as novel

NLI verification, embeddings, content hashing, requirement-specific conflict checks, impact graphs, Gherkin generation, formal verification, solver unsatisfiable cores, and generic caching or incremental recomputation already exist.

## 3. Prior-art screening (public records, not exhaustive)

| Source | Overlapping claim/disclosure | Consequence |
|---|---|---|
| US8996339B2 | Incremental formal verification, reuse of valid invariants in a revised model | Blocks generic 'reuse verification results after edits' novelty story. A patent's expired or lapsed status does not remove its published prior-art relevance. |
| US9639450B2 | Formal requirements consistency, errors, contradictory sets, unsatisfiable cores and reanalysis following edits | Blocks generic 'find conflicts, explain them, re-verify changes' claim. |
| US20230281007A1 / US12050906B2 | Program changes relevant to incremental verification; **claims priority to Indian application IN202221012260** | Strong overlap with cheap relevance/invalidation tests, requires Indian family check. |
| CN121412126A | Changed requirement activity diagrams, cross-requirement variables, requirement-test links and selective test reuse | Explicit overlap with changed-entity/scenario/test traceability; translation and legal family require further scrutiny. |
| US20070130561A1 | Automated traceability among software artifacts and change impact | Traceability is long established. |
| US9996451B2 | Inferring test dependencies from requirement changes | Additional overlap. |
| VERIFAI (2025) and requirements traceability survey (2024) | Natural language -> formalization -> verification/traceability, maintenance | Significant non-patent prior art. |

Source URLs:
- https://patents.google.com/patent/US8996339B2/en
- https://patents.google.com/patent/US9639450B2/en
- https://patents.google.com/patent/US20230281007A1/en
- https://patents.google.com/patent/US12050906B2/en
- https://patents.google.com/patent/CN121412126A/en
- https://patents.google.com/patent/US20070130561A1/en
- https://patents.google.com/patent/US9996451B2/en
- https://arxiv.org/abs/2506.10704
- https://arxiv.org/abs/2405.10845

These are selected examples, NOT a freedom-to-operate search. A complete screening needs Indian family status, examiner citations, claims, priority dates, forward/back citations and unpublished application risk.

## 4. Two actual feasibility experiments

### A. P0 synthetic micro-benchmark (prior phase, independently rerun)

- 8,000 synthetic constraints divided by construction into 2,000 independent scopes.
- Addition/deletion/movement, interpretation version changes, and 120 random edits matched the **same simplistic full verifier**.
- Initial recorded run: 17.87 ms full vs 10.74 ms incremental (about 40% improvement).
- Independent rerun on 11 Oct: 5.89 ms full vs 2.49 ms incremental (about 58% improvement).
- **Interpretation:** Runtime is environment-sensitive; scanning the whole dict creates substantial overhead. The benchmark includes neither realistic NLP/model inference nor Z3 nor unknown cross-scope relations. This establishes feasibility of simple scoped recomputation only; it cannot prove patent novelty or robust correctness.

### B. Additional adversarial negative test (11 Oct)

`p0_adversarial_scope_check.py` was executed locally. **Both intentionally naive cases failed**, as follows:

1. `password length >= 8` and `credential length <= 6`, referring to the same validated concept: the full alias-aware oracle reports a conflict, but separate surface-text scopes miss it.
2. A requirement's constrained entity changes from `username length` to `password length` after an edit: full re-interpretation reports conflict with an existing password requirement, but stale scope reuse misses it.

**Interpretation:** Any selective verifier relying on imperfect NLP-derived scope membership is unsafe if it reuses results without checking newly introduced dependencies. This is a constructed test, not a measured error frequency on real datasets.

## 5. Only candidate worth further investigation

**Candidate working name:** Uncertainty-Gated Evidence Validity for Requirement Revisions.

Question: can we construct a *specific technical implementation* that (a) efficiently discovers previously unseen cross-requirement links, (b) maintains versioned evidence fingerprints including parser and dependency assumptions, and (c) fails closed when completeness cannot be proved, while (d) lowering measured compute/memory versus independent baseline verifiers?

To claim novelty, the answer must be more than 'cache by hash', 'compare semantic similarity', 'draw a dependency graph', 'use Z3', or 'if uncertain, recompute everything'. These general ideas are already known. A narrow non-obvious mechanism with experiments is still missing.

Technical design constraints:
1. Preserve source spans and normalized units/conditions, but treat automatic interpretation as *potentially incorrect*.
2. Maintain a versioned dependency record for every verified result and a mechanism for discovering new cross-scope dependencies.
3. Distinguish **verified underlying constraint consistency** from **unverified interpretation of human language**.
4. Permit incremental reuse only with a justified scope-completeness certificate; otherwise expand or fully recompute.
5. Detect drift when model, parser, alias mapping, unit normalization, solver or data revision changes.
6. Quantify performance costs including checking and fallback, not only solver invocations.

## 6. Experimental plan, bounded to 8–12 working days

**Day 1–2**: Document true inventor contributions and potential previous disclosures; obtain VIT IPR & TT Cell guidance on ownership, disclosure confidentiality, application eligibility, and anticipated filing costs; engage a qualified Indian patent agent for preliminary inventive-step + Section 3(k) opinion.

**Day 3–4**: Create a manually adjudicated 100–300 requirement corpus and versioned edit scenarios. Supplement with SAFA two-version traces and Dronology traceability datasets; note these datasets do not provide ready-made truth labels for contradictions, so curate and disclose added labels.

**Day 5–7**: Implement a small offline typed-constraint and dependency prototype, including new-link discovery, scope moves, entity aliases, conditional scope changes, model-version changes and conservative fallback. Keep production code unchanged. Add explicit `unknown` outcome rather than hiding unresolved requirements.

**Day 8–9**: Compare three baselines on the SAME documents/edits: (i) full verification, (ii) hash-only caching, (iii) dependency-aware candidate. Evaluate exact agreement with full parsed verifier, recall on manually labeled real-world conflicts, false negatives, precision of invalidation, runtime, CPU, peak RSS and solver/model invocation counts.

**Day 10–12**: Review results and claim mapping with VIT IPR Cell / patent practitioner. Produce a high-level invention disclosure, diagrams and measured data. **Do not submit a patent application solely on this prototype.**

Suggested research sources:
- https://github.com/SAREC-Lab/SAFA-Artifacts (two versions; hazards, requirements, assumptions, design/code/tests and trace links)
- https://dronology.info/datasets/ (engineering artifacts and manually curated trace links)

Decision gates:
- Safety: 0 stale results on the constructed/manual test suite, including unseen relationships. No claims of universal soundness.
- Performance: consistent improvement over full and hash-only baselines, with overhead included and repeatable across multiple edit magnitudes.
- IP: a patent professional identifies a credible non-obvious technical claim distinct from key references.
- Institutional: VIT confirms applicant ownership, inventors, and disclosure procedure.

If the IP gate fails, **do not force a patent**. Submit a research paper based on the comparative tests; continue model improvements separately for the faculty's 95% requested metric.

## 7. India patent and VIT procedure

- Indian Patents Act Section 3(k) excludes a mathematical method, business method, computer programme per se, or algorithm; technical effect may matter under the 2025 CRI Guidelines but does not cure lack of novelty/inventive step. https://ipindia.gov.in/acts/patent-act-1970/section-3 and https://ipindia.gov.in/resource/patents-resources-guidelines
- Patents Act Section 9: a complete specification normally must follow a provisional within 12 months. https://ipindia.gov.in/acts/patent-act-1970/section-9
- VIT IPR & TT Cell: https://vit.ac.in/iprcell ; IDF-B requires prior patents/publications, invention gap, detailed working principle and experimental validation. VIT's IP policy explicitly includes student work, recognizes direct intellectual contributors in institute filings, and assigns institute-supported IP to VIT subject to contractual and institutional provisions. https://vit.ac.in/files/IPR-and-Technology-Transfer-Policy.pdf
- VIT IP portal instructions refer to forms A+B (PDF uploads). https://vit.ac.in/wp-content/uploads/2025/04/IPR-Cell-Steps-wise-procedure.pdf
- Official India filing forms and fee schedule: https://ipindia.gov.in/patents-before-you-apply-forms-official-fees
- Discuss faculty contribution and co-inventorship honestly; being the project guide is not automatically the same as contributing inventively. Record who conceived what.
- A private repository helps control access but is not an ironclad legal confidentiality guarantee. Verify prior presentations/disclosures and avoid public code, diagrams and online presentations of the *new* candidate before advice.

## 8. Final answer for student

**Do now:** Within 48 hours, contact VIT's IPR & TT Cell with a *high-level, non-enabling* request for a confidential preliminary discussion, including your department, project, collaborator/faculty details, and whether you can file as a student. Ask them which inventor ownership and approval steps apply. **Then run the bounded 8–12 day novelty-focused prototype, not a full SRS Guardian rewrite.**

**Do not now:** Change the project title to claim patent novelty; build an entire graph-and-SMT dashboard; claim 95% 'overall accuracy'; publicly publish detailed source or invention diagrams; self-file a vague provisional solely for a college certificate.

**Go/no-go date:** after the bounded prototype and VIT/agent opinion. Conditional patent filing only if a clearly distinguishable technical claim survives. Otherwise choose a defensible research paper—your faculty accepts both.