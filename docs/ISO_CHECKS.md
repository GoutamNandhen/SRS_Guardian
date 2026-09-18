# Selected Machine-Checkable Checks Based on ISO/IEC/IEEE 29148

> [!NOTE]
> **Honest Engineering Notice**: SRS Guardian does **not** certify or claim compliance with the ISO/IEC/IEEE 29148 standard. It provides an automated, rule-based audit covering **selected machine-checkable checks based on ISO/IEC/IEEE 29148** requirements quality characteristics. All findings are labeled as *potential issues* to assist human requirements engineers.

---

## Overview of Machine-Checkable Characteristics

ISO/IEC/IEEE 29148 specifies quality characteristics for individual requirements and requirements sets. While many characteristics require domain expertise or stakeholder validation (such as "Feasible" or "Necessary"), several structural and linguistic properties can be checked deterministically using Natural Language Processing (NLP).

SRS Guardian implements **7 machine-checkable checks**:

| Check ID | Characteristic | Inspects | Primary Method | Subscore Impact |
| :--- | :--- | :--- | :--- | :--- |
| `ISO-SINGULAR` | Singular | Exactly one requirement per statement | Dependency parse & coordinating conjunctions | Structure (-10.0) |
| `ISO-UNAMBIGUOUS` | Unambiguous | Absence of vague/subjective vocabulary | Lexicon matching & POS tagging | Ambiguity / Clarity (-15.0 to -20.0) |
| `ISO-VERIFIABLE` | Verifiable | Measurable, testable criteria | Numeric constraint & quantity extraction | Testability (-15.0) |
| `ISO-COMPLETE` | Complete | Syntactic presence of actor, modal, action, and object | Dependency tree parsing | Structure / Clarity (-10.0) |
| `ISO-CONSISTENT` | Consistent | Uniform terminology across requirements | Lemma overlap & synonym drift detection | Consistency (-10.0) |
| `ISO-TRACEABLE` | Traceable | Explicit identifier and structural lineage | Pattern matching & extraction metadata | Structure (-5.0) |
| `ISO-STRUCTURE` | Conforming Structure | Standardized syntax pattern (e.g. EARS template) | EARS pattern matching engine | Structure (-5.0) |

---

## Detailed Check Specifications

### 1. `ISO-SINGULAR` (Singularity)
- **What it inspects**: Whether a statement specifies only one distinct capability, condition, or constraint.
- **Evaluation Method**:
  - Detects multiple normative modal verbs (e.g., `"shall ... and shall ..."` or `"must ... and must ..."`).
  - Detects coordinating conjunctions (`"and"`, `"as well as"`, `"along with"`) joining two distinct verb phrases or independent clauses.
- **Scoring Impact**: Deducts 10.0 points from the `Structure` sub-score.
- **Limitations**: Conjoined direct objects (e.g., `"download statements and receipts"`) are valid single requirements and are disambiguated by checking if the conjoined token is a noun phrase rather than a predicate verb phrase.

---

### 2. `ISO-UNAMBIGUOUS` (Unambiguity)
- **What it inspects**: Whether the statement can be interpreted with only one meaning.
- **Evaluation Method**:
  - Reuses the Phase 5 Ambiguity Engine: flags subjective terms (from `weak_terms.yaml`), weak modals (`"should"`, `"may"`, `"could"`), vague pronouns (`"it"`, `"this"`, `"they"` without local antecedent), and unanchored passive voice.
- **Scoring Impact**: Reuses Phase 5 ambiguity deductions (10.0 to 20.0 points) affecting `Ambiguity`, `Clarity`, and `Testability` sub-scores without double-penalizing.
- **Limitations**: Context-dependent words that are acceptable in specific engineering domains may be flagged as subjective unless customized in `weak_terms.yaml`.

---

### 3. `ISO-VERIFIABLE` (Verifiability)
- **What it inspects**: Whether the requirement has quantifiable, testable criteria allowing finite verification by inspection, test, demonstration, or analysis.
- **Evaluation Method**:
  - Flags performance, speed, capacity, or time-related terms (e.g. `"fast"`, `"quickly"`, `"high capacity"`, `"instant"`) that lack explicit numeric quantities or units.
  - Verifies presence of a concrete acceptance condition, numeric constraint (`>=`, `<=`, `==`), or clear deterministic binary outcome.
- **Scoring Impact**: Deducts 15.0 points from the `Testability` sub-score.
- **Limitations**: Qualitative requirements (e.g. boolean capabilities like `"allow users to download"`) are verifiable via functional testing without numeric metrics; only statements involving performance or quantity require numeric units.

---

### 4. `ISO-COMPLETE` (Completeness)
- **What it inspects**: Whether the requirement statement contains all mandatory syntactic parts: Subject (Actor/System), Normative Modal Verb, Main Action Verb, and Object/Target.
- **Evaluation Method**:
  - Evaluates the spaCy dependency parse tree:
    - Subject: `nsubj` or `nsubjpass` pointing to an identifiable actor or system.
    - Modal: Aux verb matching `"shall"`, `"must"`, `"should"`, or `"will"`.
    - Predicate: Head verb (`ROOT`) representing the system action.
    - Object/Complement: Direct object (`dobj`), prepositional object (`pobj`), or clausal complement.
- **Scoring Impact**: Deducts 10.0 points from `Structure` and `Clarity` sub-scores.
- **Limitations**: Does not evaluate domain completeness (whether a required business feature was forgotten in the document). It checks syntactic and structural completeness.

---

### 5. `ISO-CONSISTENT` (Document Consistency)
- **What it inspects**: Whether identical concepts, entities, or actions are described using uniform terminology across the document.
- **Evaluation Method**:
  - Detects synonym drift and terminology inconsistency across the document:
    - Example 1: Referring to system actors alternately as `"user"`, `"customer"`, `"client"`, or `"account holder"`.
    - Example 2: Referring to identical workflows with differing phrases (e.g., `"reset password"` in REQ-002 vs `"recover forgotten passwords"` in REQ-003).
- **Scoring Impact**: Deducts 10.0 points from `Consistency`.
- **Limitations**: Some variation may be intentional synonyms; the AI flags potential inconsistencies for human engineering review.

---

### 6. `ISO-TRACEABLE` (Traceability)
- **What it inspects**: Whether the requirement possesses a unique, persistent identifier and identifiable document provenance.
- **Evaluation Method**:
  - Checks if the requirement has an explicit standard identifier (e.g., `REQ-001`, `FR-12`, `NFR-03`, `R-1.1`).
  - Verifies that `source_layer` is known (`layer1_explicit_id`, `layer2_structural_cue`, or `layer3_modal_sentence`).
- **Scoring Impact**: Deducts 5.0 points from `Structure`.
- **Limitations**: Pure text requirements without explicit IDs can still function, but lack formal traceability.

---

### 7. `ISO-STRUCTURE` (Appropriate Structure / EARS Conformance)
- **What it inspects**: Whether the requirement follows a recognized, structured requirements syntax pattern.
- **Evaluation Method**:
  - Runs the EARS pattern matcher (`backend/app/nlp/ears.py`).
  - Conforms if the statement matches one of the 6 EARS templates:
    1. **Ubiquitous**: `THE <system> SHALL <response>`
    2. **Event-driven**: `WHEN <trigger>, THE <system> SHALL <response>`
    3. **State-driven**: `WHILE <state>, THE <system> SHALL <response>`
    4. **Unwanted behavior**: `IF <condition>, THEN THE <system> SHALL <response>`
    5. **Optional feature**: `WHERE <feature>, THE <system> SHALL <response>`
    6. **Complex**: Valid combination of trigger, state, feature, and condition clauses.
  - Flags non-conforming sentences with missing elements (e.g. missing trigger, missing system actor, or inverted syntax).
- **Scoring Impact**: Deducts 5.0 points from `Structure` if non-conforming.
- **Limitations**: A requirement can be valid plain English without strictly following EARS; the deduction is minor and intended to encourage standardized syntax.
