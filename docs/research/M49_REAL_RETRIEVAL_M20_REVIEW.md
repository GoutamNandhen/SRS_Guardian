# M49 — Real retrieval predictions handed to M20 review (NOT GOLD)

This step closes a specific evidence gap: the M43 pip experiment reported top-five retrieved source symbols, but those **actual predictions** were not directly packaged as blinded M20 link-annotation cases. M49 uses the unchanged M43 normalized-token baseline over the complete pinned first-party `src/pip/_internal/` Python source tree, then presents exactly those top-five predictions for each of three upstream-derived requirement scenarios at two historical revisions.

**Reproducible first-party commands (no upstream code execution):**

```sh
python -m pip install 'pytest==8.4.2'
python -m pytest -q backend/tests/test_m49_ranked_m20_review.py
python -m backend.evaluation.m49_ranked_m20_review --out-dir m49_evidence
```

The generator downloads immutable pip source archives and Git trees, verifies the MIT license and Git blob hashes through existing M29/M42/M43 functions, parses Python source as inert text, and creates two reviewer-specific JSONL files. The internal ranked manifest is **not for reviewers**. Each reviewer receives 30 pending M20 candidate-link judgments, representing 6 correlated scenario/revision cases x 5 retrieved symbols; the queue includes pinned source-line URLs but excludes rank, score, known fix locus and revision category. Each reviewer must inspect actual code and mark links with source citations independently. A separate human adjudicator must resolve disagreements.

**Boundaries:** These are previously inspected pip development cases, not untouched held-out projects. The top-five-only review sample cannot estimate full-repository link recall. Reviewer annotation is still pending; no human evidence was fabricated. Source structure does not establish runtime conformance. The three scenarios are correlated. The existing M45–M48 Requests capture workflow remains a separate source of *potential* approved behavioral evidence and is not replaced by this link-review step. A reviewer must not infer behavioral labels from code links or upstream fix notes.

**Before any accuracy claim:** Obtain two independent M20 link reviews, independent revision-compatible behavioral observations and third-person adjudication. Freeze the verifier and evaluate previously unseen permissively licensed projects with documented sampling and per-project confusion matrices, coverage, violation precision and recall. Currently: independent labels **0**, approved behavioral observations **0**, held-out project scores **0**; conformance accuracy, violation precision, violation recall and coverage **undefined**. Targets of 95%/95%/90% are unproven.
