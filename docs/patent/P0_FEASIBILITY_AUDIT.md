# SRS Guardian — Phase P0 Patent Novelty and Technical Feasibility Audit

**Status:** PRELIMINARY / NOT A PATENTABILITY OPINION  
**Date:** 10 October 2026  
**Repository branch:** `research/p0-patent-feasibility`  
**Decision:** **CONDITIONAL GO for a controlled feasibility prototype; NO-GO for immediate patent filing.**

> CONFIDENTIALITY: This is a working internal research note in a private repository. Do not publish proposed claim details, source code, screenshots, or an enabling description before institutional IP guidance.

## 1. Existing system — examined, not hypothetical

The baseline system already implements:

- Multi-format requirement extraction and classification (TF-IDF + Logistic Regression).
- Ambiguity, readability, EARS and selected ISO/IEC/IEEE 29148-derived checks.
- Semantic duplicates using all-MiniLM-L6-v2, with content-hash embeddings cache.
- Numeric 5-tuple constraint extraction and interval-conflict analysis, plus `facebook/bart-large-mnli` candidate verification.
- SHA-256 cached NLI and on-demand verification.
- Document version comparison, review decisions, annotated output, and Gherkin test skeletons.

Relevant existing code: `backend/app/nlp/numeric_constraints.py`, `backend/app/ml/contradictions.py`, `backend/app/ml/embeddings.py`, `backend/app/ml/duplicates.py`, `PROJECT_STATE.md`, and `docs/EVALUATION.md`.

**Do not claim as invention:** embedding caching, requirement classification, numeric interval checking, NLI-on-demand, traceability in general, Z3, SMT/unsat cores, impact graphs in general, or the concept of incremental verification.

Baseline classification: **85.05% accuracy, 84.55% macro F1** on the 194-item PROMISE_exp test set. This is a separate academic improvement target, not an indicator of patentability.

## 2. Closest prior art — initial claim-oriented screen

| Reference | Relevant disclosure | Material overlap | Initial assessment |
|---|---|---|---|
| **US8996339B2** — Incremental formal verification | Reuses invariants and parts of proof between changed verification models, while validating reuse | Safe proof reuse / resource savings | **Very high risk** for broad “reuse verification evidence” claims |
| **US9639450B2** — Scalable methods for analyzing formalized requirements and localizing errors | Finds conflicting requirements, explains errors, accepts edited requirements and repeats checks | Formal requirement conflict verification / explanation / rechecks | **Very high risk** |
| **US20230281007A1** — Relevant changes for incremental verification of evolving software | Determines whether changed code statements affect verification properties using value-influencing variable analysis | Selective invalidation concept | **High risk**, although centered on program code/properties |
| **US20240028327A1** (later US12481497B2) — SDLC knowledge fabric | NLP/graphs correlate requirements, tests, changes, impact | NLP+graph+test traceability | **High risk** for broad graph/traceability combinations |
| **CN121412126A** — Embedded system integration test case reuse | Requirement→scenario→test trace chain with classified changes and reuse decisions | Incremental linked-test updates | **High risk** for change-driven test reuse |
| **2012–2025 academic literature** | Provenance-aware requirements verification traceability, semantic requirement change impact, incremental checking | Known non-patent technical ideas relevant to inventive step | **High research overlap** |

**Primary links:**
- https://patents.google.com/patent/US8996339B2/en
- https://patents.google.com/patent/US9639450B2/en
- https://patents.google.com/patent/US20230281007A1/en
- https://patents.google.com/patent/US20240028327A1/en
- https://patents.google.com/patent/CN121412126A/en
- https://www.mdpi.com/2079-9292/10/8/983
- https://onlinelibrary.wiley.com/doi/10.1155/je/2296387

**Limitations:** This is a targeted public-source screen, NOT a comprehensive patentability search, validity opinion, freedom-to-operate analysis, or assessment of Indian family members/claim status. Filing families, claim scope, prosecution history, publication dates, jurisdiction, unpublished applications, and non-patent literature require a qualified patent search and opinion.

## 3. Narrow differentiation hypothesis (UNPROVEN)

**Working name:** *Versioned Evidence Validity for Natural-Language Requirement Verification*.

**Research hypothesis:** A validation system can conservatively reuse natural-language-derived verification evidence after requirement edits by recording the complete dependency and interpretation provenance of each verification result, with explicit fallback to broader revalidation whenever new or uncertain relationships could undermine reuse.

Proposed *testable* distinctions, NOT established novelty:

1. A typed, versioned source→interpretation→constraint→verification-evidence dependency record.
2. Explicit invalidation caused by changes to interpretation/parser version, model version, solver semantics, source text or cross-scope dependencies—not just source-text hashes.
3. A fail-closed rule: when semantic scope boundaries or dependency completeness cannot be trusted, run full or expanded recomputation rather than reusing stale evidence.
4. Reproducible per-finding validity certificate: precise input fingerprints and human-validated interpretation assumptions linked to the computed verdict.
5. Comparison with strict baselines on *soundness of reuse* as well as total computation.

**Major concern:** Each item may already be known individually or in combination. Merely combining them may be obvious. A distinct mechanism, not terminology, is needed before any patent recommendation.

## 4. Technical specification for a limited experimental implementation

### Versioned data model

```
RequirementRevision:
  req_id, revision_id, source_hash, text_span
  interpreted_scope_ids, interpretation_id, interpretation_confidence
  normalized_typed_constraints[], parser_model_fingerprint

VerificationRecord:
  record_id, source_requirement_revisions[]
  declared_scope_dependencies[], assumption_ids[]
  constraint_digest, engine_fingerprint, policy_fingerprint
  verdict (consistent | inconsistent | unknown)
  conflict_evidence / solver core (if supported)
  validity_status (valid | invalid | needs-review)
```

### Conservative invalidation pseudocode

```
on_document_revision(old_state, new_state):
  changed = changed/added/deleted requirements AND changed models/policies/assumptions
  scopes = union(old_scope, new_scope) for each changed requirement
  if any missing or uncertain relation, model/policy change, or untrusted dependency index:
      expand scope conservatively (possibly entire document)
  invalidate every record dependent on affected sources/scopes/assumptions
  recompute affected records; compare with full verifier in validation experiments
  do not label output “verified” if natural-language constraint interpretation is unreviewed
```

**Key failure modes to test:** a sentence moves scope; hidden shared variables; a newly added requirement introduces a previously unknown conflict pair; cross-scope implicit dependencies; model-version changes; deleted source rows; false confidence from an incorrect parser; contradictory constraints under alternate units or conditions.

**Critical soundness boundary:** Equivalence with a full deterministic verifier only proves the invalidation strategy matches that verifier on the test domain. It does not establish that the original natural-language interpretation is correct, nor formal soundness for arbitrary requirements.

## 5. P0 executable synthetic micro-benchmark — run 10 Oct 2026

An isolated Python proof-of-concept was executed using **8,000 synthetic numeric constraints** arranged into **2,000 independent verification scopes**; no NLP, real SRS data, Z3 or transformer inference was involved. Scopes were *trusted by construction*, and unknown cross-scope dependencies explicitly triggered full recomputation.

- One local numeric edit: **2,000 full checks vs 1 selective check**, with exactly matching evidence maps.
- Added, removed and changed-scope requirements: matching outputs (scope move recomputed 2 scopes).
- Interpretation or verification-engine version changed: **all 2,000 scopes recomputed**, matching full output.
- Unknown cross-scope dependencies: conservative full recomputation.
- **120 seeded randomized single-requirement edits**: identical evidence versus full recomputation.
- Sample median runtime (10 runs, environment-specific): full **17.87 ms**, selective **10.74 ms**, approximately **40% shorter**. This **does NOT reach the tentative 50% runtime-reduction goal**; diff scanning alone incurs work. The timing is not a real-system performance claim.

This verifies only that a simple conservative dependency approach can be implemented and passes basic synthetic consistency checks. Incremental verification is established prior art; these observations do **not** demonstrate inventiveness or patent eligibility.

## 6. Stop/go gates for Phase P0

**G1 — Prior-art differentiation (not met):** A patent professional can describe a specific, non-obvious technical method that the closest disclosures do not teach or make obvious.

**G2 — Complete dependency safety (not met):** Tests cover newly introduced cross-scope relationships, parser uncertainty, changes to interpretation, and hidden links; no stale results on the labeled evaluation suite.

**G3 — Technical improvement (not met on realistic workloads):** Demonstrable improvement over full recompute AND text-hash-only caching on representative, changing SRS files. Measure overall wall time, peak RAM, model/solver calls, correctness. Prespecified speed targets must not be presented as achieved.

**G4 — Reproducible evidence (partial):** Small synthetic demonstration passes; need realistic datasets, ablations, independent labels, repeated timing and real ML/SMT integration.

**G5 — Legal and institutional pathway (pending):** VIT IPR & Technology Transfer Cell reviews disclosure, inventor contributions, ownership and publication restrictions; Indian patent counsel reviews Section 3(k), novelty and inventive step.

If G1 fails: **NO patent filing for this candidate**; consider another technical invention or research paper. If G2 or G3 fails: revise and retest before filing.

## 7. Phase P0 follow-on experiments (10–14 days, not automatically started)

1. Obtain VIT IPR policy, internal submission pathway, and an inventor contribution record; review disclosure risk.
2. Expand prior-art screen: patent families, claims, forward/backward citations, closest journals/conferences and Indian applications.
3. Develop a change-event journal and validated dependency index; address the observed diff-scanning overhead without trusting unverified hints.
4. Compare three baselines: full verification, hash-only reuse, conservative dependency-aware reuse.
5. Build a 100–300 requirement *manually checked* test corpus across multiple domains; generate explicit edit families and independent ground-truth dependency labels.
6. Integrate a small typed constraint parser and Z3 *outside the current production pipeline*; mark unsupported statements as unknown.
7. Conduct ablations and calibrate confidence / fallback policies.
8. Present evidence and the closest-claim mapping to the VIT IPR Cell and a qualified Indian patent professional.

## 8. India-specific screening

India's Section 3(k) lists mathematical methods, business methods, algorithms, and computer programs *per se* as excluded categories. The 2025 CRI guidelines discuss the need to identify a credible technical effect beyond incidental general computation, and emphasize assessing the substance of the claim.

Official guidelines: https://ipindia.gov.in/frontend/pdf/patents/guidelines/GUIDELINES%20FOR%20EXAMINATION%20OF%20COMPUTER%20RELATED%20INVENTIONS%20%28CRIs%29%20-%202025.pdf

VIT IPR & TT Cell: https://vit.ac.in/iprcell (Invention Disclosure Form for Patents, institutional IP policy and portal).

**Do not disclose details publicly or submit patent claims based solely on this report.**

## 9. Honest status

- Technical feasibility of a narrowly scoped prototype: **YES**.
- Independent real-world performance advantage: **NOT YET SHOWN**.
- Sufficient novelty/inventive step: **NOT ESTABLISHED; HIGH PRIOR-ART RISK**.
- Section 3(k) eligibility: **REQUIRES PROFESSIONAL ASSESSMENT**.
- Recommendation: **Continue P0 research privately. Do not file yet.**
