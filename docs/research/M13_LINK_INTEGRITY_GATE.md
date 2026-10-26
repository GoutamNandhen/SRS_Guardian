# SRS Guardian 2.0 — M13 link-integrity acceptance safeguard

**Scope:** research evaluator scoring only. No new inference model, external dataset, untrusted code execution, or new claim of real-world accuracy.

## Defect addressed

The M1 evaluator previously treated every `predicted_link=true` for a gold-linked candidate pair as a true positive, **even if the prediction named a different `candidate_code_ref` or `source_commit`**. The 95% acceptance gate also ignored link precision/recall. Consequently a system could report perfect conformance on the linked cases yet falsely link every unlinked pair and still receive `PASSED`.

This is a **benchmark-validity defect**, not an observed defect in the deployed retrieval algorithm.

## M13 behavior

1. A true-positive link requires `predicted_link=true` **and** exact equality with the gold candidate's `candidate_code_ref` and `source_commit`. A mismatch on a gold-linked candidate counts as a false negative, and is reported separately in `reference_mismatch_count`. Unlinked candidates predicted as linked remain false positives.
2. Research acceptance now additionally requires **link precision ≥0.95 and link recall ≥0.95**, alongside full-denominator conformance accuracy ≥0.95, violation precision ≥0.95, violation recall ≥0.90, and decision coverage ≥0.70.
3. The existing minimum test-size, project-count, class balance, real-data status and evidence requirements remain in place. The M5 benchmark lock and independent provenance review are still needed before publication.
4. Existing conformance accuracy is intentionally unchanged. Link retrieval and executable conformance are distinct tracks and both must be measured.

## Regression design and limitations

`backend/tests/test_m13_link_integrity_gate.py` includes adversarial **mock** examples: two perfectly verified linked candidates plus two unlinked candidates falsely marked linked. The mock has 100% conformance accuracy but only 50% link precision; M13 must reject its 95% acceptance. It also tests wrong symbol and wrong revision references. A control with correct links passes **only mocked gate arithmetic**; it is not a measured model result. Small-sample thresholds are lowered inside these unit tests exclusively.

Run:

```bash
python -m pytest -q backend/tests/test_evaluate_conformance.py backend/tests/test_m13_link_integrity_gate.py
```

The M13 GitHub Actions workflow additionally runs the M1–M13 focused regression, reviewed Docker positive/negative controls and the Next.js production build.

**Research status:** No independent real-world 95% accuracy has been demonstrated. Next: build a genuinely labeled, preregistered multi-project conformance benchmark and report all missed/incorrect links and abstentions. **Do not merge into main without review.**
