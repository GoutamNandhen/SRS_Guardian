# Requirement Quality Scoring Specification

This document defines the mathematical formulation, rule weights, sub-score dimensions, and aggregation methodology implemented in **SRS Guardian**.

---

## 1. Overview & Objectives

SRS Guardian provides a deterministic, transparent, and reproducible quality scoring framework for software requirements. 

- **Deterministic**: The exact same requirement with the exact same findings produces the exact same score.
- **Explainable**: Every point deducted is tied directly to an identified defect rule with a specific character span and provenance.
- **No LLM in Scoring**: The calculation uses a closed-form formula without generative hallucination or token-cost overhead.

---

## 2. Mathematical Formulation

### 2.1 Overall Quality Score
Each requirement begins with a perfect base score of $S_{\text{base}} = 100.0$. For each active finding $f \in \mathcal{F}$ detected by the analysis pipeline, a calibrated penalty weight $W(f)$ is subtracted:

$$S_{\text{raw}} = S_{\text{base}} - \sum_{f \in \mathcal{F}} W(f)$$

The overall quality score is clamped to the range $[0.0, 100.0]$:

$$S_{\text{overall}} = \max\left(0.0, \min\left(100.0, S_{\text{raw}}\right)\right)$$

### 2.2 Penalty Weights & Justifications

All penalty weights are externalized in `backend/app/nlp/rules/score_weights.yaml`:

| Rule ID | Category | Deduction | Justification |
| :--- | :--- | :---: | :--- |
| `CHECK_A_WEAK_TERM` | Ambiguity | **-20.0** | Subjective adjectives/adverbs (e.g. *quickly*, *user-friendly*, *robust*) lack objective acceptance criteria and directly prevent verifiable acceptance testing. |
| `CHECK_B_WEAK_MODAL` | Ambiguity | **-15.0** | Non-normative modals (e.g. *should*, *may*, *could*) make obligations legally or procedurally non-binding under requirement standards. |
| `CHECK_C_MISSING_METRIC` | Testability | **-15.0** | Mentions a measurable dimension (*latency*, *capacity*, *availability*) without stating numeric bounds or units, leaving performance unverifiable. |
| `SEMANTIC_DUPLICATE` | Consistency | **-15.0** | Semantic similarity $\ge 0.80$ to another requirement indicates functional redundancy and bloated specification. |
| `CHECK_D_VAGUE_PRONOUN` | Clarity | **-10.0** | Subject pronouns (*it*, *this*, *they*) without explicit preceding noun antecedents cause misinterpretation during implementation. |
| `CHECK_E_COMPOUND_REQ` | Structure | **-10.0** | Joins multiple independent obligations into one sentence, violating requirement singularity and complicating traceability. |
| `CHECK_F_PASSIVE_VOICE` | Structure | **-10.0** | Passive voice without an agent hides the responsible system actor, obscuring accountability. |
| `READABILITY_HIGH_GUNNING_FOG` | Readability | **-10.0** | Gunning Fog index $> 14.0$ indicates academic or convoluted prose that increases implementation errors. |
| `READABILITY_HIGH_PASSIVE` | Readability | **-5.0** | Passive clause ratio $> 0.40$ reduces sentence dynamism and clarity. |

---

## 3. Sub-Score Dimensions

To give engineering teams targeted feedback across multiple quality axes, SRS Guardian computes 6 orthogonal sub-scores, each scaled from $0.0$ to $100.0$:

1. **Clarity ($S_{\text{clarity}}$)**: Measures readability and precision of wording.
   - Base 100, penalized by subjective terms (`-30`), vague pronouns (`-25`), and extreme reading difficulty (`-25`).
2. **Ambiguity ($S_{\text{ambiguity}}$)**: Measures the degree of certainty and determinism in the requirement statement.
   - Base 100, penalized by subjective terms (`-35`), weak modal verbs (`-35`), and unquantified measurable metrics (`-30`).
3. **Testability ($S_{\text{testability}}$)**: Measures whether verification and validation engineers can formulate automated acceptance tests.
   - Base 100, penalized by missing metric thresholds (`-40`), weak non-binding modals (`-30`), and subjective terms (`-30`).
4. **Readability ($S_{\text{readability}}$)**: Objective prose analysis derived from structural linguistic indicators.
   - Starts at 100. Decrements based on Flesch Reading Ease score below 50, Gunning Fog index above 14, and sentence length exceeding 35 words.
5. **Structure ($S_{\text{structure}}$)**: Evaluates structural syntax and sentence singularity.
   - Base 100, penalized by compound clauses (`-40`), passive voice without agent (`-35`), and high passive ratio (`-25`).
6. **Consistency ($S_{\text{consistency}}$)**: Evaluates semantic alignment and absence of duplication across the specification.
   - Base 100, penalized by candidate semantic duplicate findings (`-50`).

---

## 4. Score Waterfall Breakdown

The score waterfall is an ordered list of transitions documenting every point deducted from the baseline:

$$\left(S_0, \Delta_0, \text{Step}_0\right) \longrightarrow \left(S_1, \Delta_1, \text{Step}_1\right) \longrightarrow \dots \longrightarrow \left(S_k, \Delta_k, \text{Step}_k\right)$$

### Worked Example: REQ-001
- **Requirement**: *"The system should respond quickly when the user checks the account balance."*
- **Waterfall Trace**:
  1. Base Score: `100.0`
  2. Step 1: Weak Modal Verb (*should*) $\rightarrow$ Deduct `-15.0` $\implies$ Score: `85.0`
  3. Step 2: Subjective Term (*quickly*) $\rightarrow$ Deduct `-20.0` $\implies$ Score: `65.0`
  4. Final Overall Score: `65.0 / 100.0`
- **Sub-scores**:
  - Clarity: `70.0`
  - Ambiguity: `30.0`
  - Testability: `40.0`
  - Readability: `95.0`
  - Structure: `100.0`
  - Consistency: `100.0`

---

## 5. Document-Level Aggregates

For multi-requirement SRS documents, the platform calculates summary statistics:
- **Mean Score**: $\mu = \frac{1}{N} \sum_{i=1}^{N} S_i$
- **Median Score**: Central tendency across all requirements.
- **Score Distribution Bins**:
  - `90-100` (Excellent)
  - `70-89` (Acceptable / Minor defects)
  - `50-69` (Needs Revision)
  - `<50` (Critically Defective)
- **Worst Requirements**: Top $k$ lowest-scoring requirements requiring immediate human review.
- **Issue Counts**: Aggregate breakdown of active findings grouped by rule and severity.

---

## 6. Standards Alignment & Disclaimer

The checks and penalty weights in SRS Guardian are selected machine-checkable heuristics informed by guidelines in **ISO/IEC/IEEE 29148:2018** (Requirements Engineering) and **INCOSE Guide for Writing Requirements**. 

SRS Guardian **does not claim official ISO certification or complete standard compliance**. The quality score is an automated advisory metric designed to assist human requirements engineers, not replace them.
