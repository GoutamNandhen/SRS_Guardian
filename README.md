# SRS Guardian

> **An integrated, explainable AI-assisted requirement review platform combining rule-based analysis, semantic similarity, NLI, standards-oriented checks, AI rewriting, human review, version comparison, and reporting.**

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14_App_Router-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests Passing](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()

---

## 1. Overview & Core Philosophy

**SRS Guardian** is an intelligent assistant designed to help systems engineers, requirements analysts, and project managers audit Software Requirement Specification (SRS) documents. 

Requirements engineering defects—such as subjective wording, hidden duplicates, conflicting numeric constraints, and non-testable statements—account for up to 50% of software project failures and cost orders of magnitude more to correct downstream. SRS Guardian analyzes uploaded documents and automatically surfaces potential defects with **transparent, human-understandable explanations**.

### Non-Negotiable System Principles
1. **Assists, Does Not Replace:** The system surfaces *potential* defects; human engineers retain final authority to accept, reject, or edit findings.
2. **Explainability Over Black Boxes:** Every finding provides exact character spans, deduction rationale, and visual attributions (e.g. SHAP token scores, interval diagrams).
3. **Cost Discipline & Offline Autonomy:** The core analytical pipeline (extraction, classification, ambiguity rules, semantic duplicates, numeric intervals, and quality scoring) is 100% functional on a standard CPU with **zero cloud dependencies or API costs**. Generative LLMs are restricted strictly to optional rewrite assistance and are disabled by default.

---

## 2. Interactive System Architecture

SRS Guardian is structured into a clean decoupled architecture consisting of a Next.js web application, a FastAPI REST gateway, a layered NLP/ML verification pipeline, and relational audit storage.

```
+----------------------------------------------------------------------------------------------------+
|                                    SRS GUARDIAN ARCHITECTURE                                       |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|  [ Browser Client ]  <--->  [ Next.js 14 Web UI ]  <--->  [ FastAPI REST API Gateway ]            |
|                                                                    |                               |
|                                            +-----------------------+-----------------------+       |
|                                            |                                               |       |
|                                            v                                               v       |
|                            [ Ingestion & Extraction ]                          [ Database Store ]  |
|                                  (PyMuPDF, docx)                                (SQLite / Postgres)|
|                                            |                                                       |
|                     +----------------------+----------------------+                                |
|                     |                      |                      |                                |
|                     v                      v                      v                                |
|             [ Classification ]     [ Ambiguity Rules ]   [ Semantic Duplicates ]                   |
|             (TF-IDF + LR + SHAP)    (6 Syntactic Rules)   (MiniLM Cosine Matrix)                   |
|                     |                      |                      |                                |
|                     +----------------------+----------------------+                                |
|                                            |                                                       |
|                     +----------------------+----------------------+                                |
|                     |                      |                      |                                |
|                     v                      v                      v                                |
|             [ Contradictions ]     [ Standards & EARS ]   [ Quality Scoring ]                      |
|             (Numeric & MNLI)       (7 ISO Checks)         (Waterfall Audit Trail)                  |
|                                            |                                                       |
|                                            v                                                       |
|                                 [ Review & Export Engine ]                                         |
|                                  (HTML, CSV, PDF Reports)                                          |
+----------------------------------------------------------------------------------------------------+
```

> **Interactive Visualization:** Explore the full interactive system diagram with runtime path tracing and component inspection in [architecture.html](file:///f:/projects/srs/architecture.html) or [docs/architecture.html](file:///f:/projects/srs/docs/architecture.html).

---

## 3. Core Capabilities

### Ingestion & Layered Requirement Extraction
- Multi-format ingestion supporting `.pdf`, `.docx`, and `.txt` files.
- Layered extraction algorithm identifying requirements via explicit alphanumeric identifiers (e.g. `REQ-001`, `FR-12`), structural bullet delimiters, modal verbs (`shall`, `must`, `will`), and paragraph boundaries.

### Classification with SHAP Explainability
- Fast CPU-based classification separating **Functional Requirements (FR)** from **Non-Functional Requirements (NFR)** using an L2-regularized Logistic Regression pipeline over TF-IDF n-grams.
- Exact word-level attribution via **SHAP LinearExplainer**, displaying positive and negative token impacts for each classification decision.

### Syntactic Ambiguity & Readability Engine
- 6 deterministic machine-checkable syntactic checks:
  1. **Subjective & Weak Terms** (e.g., *user-friendly*, *quickly*, *scalable*).
  2. **Non-Normative Weak Modals** (e.g., *should*, *could*, *might*, *ought to*).
  3. **Missing Quantitative Metrics** (e.g., *high performance*, *low latency* without bounds).
  4. **Vague Pronouns** without local referents (*it*, *this*, *that*).
  5. **Compound Multi-Obligation Clauses** (multiple conjoined *and/or* actions).
  6. **Passive Voice Without Actor** (*"Record shall be updated"*).
- Readability scoring computing Flesch Reading Ease, Gunning Fog Index, clause nesting depth, and passive voice ratio.

### Semantic Duplicate Detection
- Dense sentence embedding via `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors).
- Two-tier candidate blocking using content lemma intersection for large documents.
- Fine-grained similarity attribution extracting noun-chunks and action phrases to explain *why* two requirements are considered duplicates.
- Permanent SHA-256 disk caching ensuring zero re-encoding of known sentences.

### Two-Tier Contradiction Detection
- **Tier 1 (Deterministic Numeric Constraint Engine):** Extracts 5-tuples `(entity, attribute, comparator, value, unit)` and checks for empty mathematical interval intersections ($[l_1, h_1] \cap [l_2, h_2] = \emptyset$). Detects conflicts like `[8, inf)` vs `[6, 6]` characters with 100% precision.
- **Tier 2 (Candidate-Blocked NLI):** Employs a pretrained MNLI model with subject lemma overlap and cosine similarity filtering ($\ge 0.55$) to detect semantic contradictions while strictly bounding CPU compute.

### EARS Syntax Validation & ISO/IEC/IEEE 29148 Checks
- Conformance validation against the 6 Easy Approach to Requirements Syntax (EARS) patterns: Ubiquitous, Event-driven, State-driven, Unwanted behavior, Optional feature, and Complex.
- Selected machine-checkable checks based on **ISO/IEC/IEEE 29148**: Singularity, Non-ambiguity, Verifiability, Syntactic Completeness, Consistent Terminology, Traceability, and Structural Template adherence.

### Deterministic Quality Scoring & Waterfall Breakdown
- Transparent 0–100 quality score derived from configurable penalty weights (`score_weights.yaml`).
- 6 orthogonal sub-scores: *Clarity, Ambiguity, Testability, Readability, Structure, and Consistency*.
- Full waterfall audit trace showing the exact points deducted for each specific defect.

### Human-in-the-Loop Review & Version Diffing
- Review ledger allowing analysts to `Accept`, `Reject`, or `Edit` AI findings with full audit trail history.
- Cross-version semantic diffing matching requirements across document iterations using composite keys and vector similarity, displaying word-level inline diffs (`[-deleted-]`, `[+added+]`), quality score changes, and defect resolution status.

### Test Generation & Reporting
- Rule-based Given/When/Then **Gherkin test skeleton generator** mapped directly from EARS clauses with optional LLM augmentation.
- Automated report generation compiling executive summaries into printable **HTML scorecards**, structured **CSV matrices**, and pure-Python rendered **PDF audit reports**.

---

## 4. Empirical Evaluation Results

The system was evaluated against curated, ground-truth labeled benchmark datasets with **zero fabricated numbers**. Detailed methodology and confusion matrices are documented in [docs/EVALUATION.md](file:///f:/projects/srs/docs/EVALUATION.md).

| Capability | Benchmark Dataset | Sample Count | Primary Metric | Result |
| :--- | :--- | :--- | :--- | :--- |
| **Requirement Classification** | PROMISE_exp (Held-Out Split) | 194 reqs | Accuracy / Macro F1 | **85.05%** / **84.55%** (3.19 ms/req) |
| **Ambiguity Detection** | Hand-Labeled Evaluation Set | 40 reqs | Precision / Recall / F1 | **88.89%** / **64.00%** / **74.42%** |
| **Semantic Duplicates** | Pairwise Paraphrase Benchmark | 36 pairs | Optimal Threshold / F1 | $\theta = \mathbf{0.70}$ / **86.67%** (FPR: 5.0%) |
| **Numeric Contradictions** | Interval Conflict Benchmark | 16 pairs | Precision / Recall / F1 | **100.00%** / **37.50%** / **54.55%** |
| **Semantic Contradictions** | Candidate-Blocked NLI | 16 pairs | Precision / Recall / F1 | **70.00%** / **87.50%** / **77.78%** |
| **Integrated Contradiction** | Combined 2-Tier Pipeline | 32 pairs | Precision / Recall / F1 | **60.00%** / **93.75%** / **73.17%** |

---

## 5. Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Git

### Option A: Local Development Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/GoutamNandhen/SRS_Guardian.git
   cd SRS_Guardian
   ```

2. **Backend Setup:**
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/MacOS:
   source .venv/bin/activate

   # Install dependencies
   pip install -r backend/requirements.txt

   # Download spaCy pipeline
   python -m spacy download en_core_web_sm

   # Start FastAPI server
   uvicorn backend.app.main:app --reload --port 8000
   ```
   The backend API will be available at `http://127.0.0.1:8000` (Swagger docs at `/docs`).

3. **Frontend Setup:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   The web dashboard will be available at `http://localhost:3000`.

### Option B: Docker Compose Deployment

To launch the complete multi-container stack (Next.js frontend, FastAPI backend, and PostgreSQL database):

```bash
docker-compose up --build
```
- Web Application: `http://localhost:3000`
- REST API & Swagger: `http://localhost:8000/docs`
- PostgreSQL Database: `localhost:5432`

---

## 6. Running Tests & Benchmarks

Run backend unit and integration test suites:
```bash
# Run all tests
pytest backend/tests/ -v

# Run Phase 16 empirical evaluation benchmarks
python -m backend.evaluation.run_evaluation
```

Verify frontend build:
```bash
cd frontend
npm run build
```

---

## 7. Project Structure

```
SRS_Guardian/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routers (documents, requirements, issues, etc.)
│   │   ├── core/            # Config, database session, logging
│   │   ├── ml/              # Classifier, embeddings, duplicates, contradictions, clustering
│   │   ├── models/          # SQLAlchemy ORM models (Document, Requirement, Issue, Review)
│   │   ├── nlp/             # Extraction, ambiguity rules, readability, EARS, ISO checks
│   │   ├── schemas/         # Pydantic v2 request/response models
│   │   ├── services/        # Orchestration, report generation, LLM gateway
│   │   └── main.py          # FastAPI application entrypoint
│   ├── evaluation/          # Benchmark evaluation runners
│   └── tests/               # 18 automated test suites (100% pass rate)
├── frontend/
│   ├── app/                 # Next.js 14 App Router pages (Dashboard, Analysis, Compare, etc.)
│   ├── components/          # Reusable UI components & layouts
│   ├── services/            # Typed REST API client
│   └── types/               # TypeScript interfaces
├── data/
│   ├── cache/               # Persistent disk caches (embeddings, NLI, LLM)
│   └── test/                # Curated evaluation benchmark splits
├── docker/                  # Backend & Frontend Dockerfiles
├── docs/                    # Architecture diagrams, specifications, and BUILD_LOG.md
├── docker-compose.yml       # Multi-container orchestration
└── README.md
```

---

## 8. Limitations & Scope Boundaries

In accordance with academic integrity and ethical engineering standards:
- **No Claim of ISO Certification:** SRS Guardian performs *selected machine-checkable checks based on ISO/IEC/IEEE 29148*. Complete standard compliance requires contextual human review.
- **Syntactic Heuristics:** Natural language contains stylistic nuances. Passive voice or compound predicates may be intentionally used in specific engineering domains. The system highlights them as *potential* defects.
- **Dataset Domain Context:** The classifier was trained on the historic PROMISE repository. Emerging paradigms (e.g. quantum algorithms, specialized distributed consensus protocols) should be verified by subject matter experts.

---

## 9. Academic Contribution & Citation

When referencing this project in academic research or reports, cite as:

> *"SRS Guardian: An integrated, explainable AI-assisted requirement review platform combining rule-based analysis, semantic similarity, NLI, standards-oriented checks, AI rewriting, human review, version comparison, and reporting."*

---

## 10. License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
