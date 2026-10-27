# M16 — Correct link precision when the predicted source symbol/revision is wrong

**Status:** Scoring-integrity fix only. No improvement to retrieval, source matching, or real-world conformance accuracy is claimed.

## Failure mode

In the previous M13–M15 evaluator, a predicted positive link on a gold-positive requirement-to-code pair was counted as a **false negative only** when its `candidate_code_ref` or `source_commit` differed from the gold edge. This correctly reduced recall, but **did not penalize precision** for the incorrect link that was asserted. A system predicting only wrong code symbols could therefore report undefined precision (no true-positive predictions counted) instead of the meaningful zero precision for its claimed false links; a mixed system could report misleadingly perfect precision.

## Correction

A positive claim to the wrong source reference or revision contributes **one false positive for the asserted wrong edge and one false negative for the missed gold edge**. `reference_mismatch_count` remains the number of mismatched positive claims, not the sum of FP and FN.

For one correct and one wrong positive claim, with one correctly rejected unlinked candidate, link counts become TP=1, FP=1, FN=1, TN=1, precision=0.5 and recall=0.5. For two wrong positive claims, TP=0, FP=2, FN=2 and precision=recall=0. This follows exact-edge evaluation; it is not an estimate of ranking quality across an unrestricted source-code corpus.

## Verification

The M16 CI workflow runs the consolidated M1–M16 test suite (including wrong-symbol and wrong-revision adversarial cases), restricted real-Docker positive and negative controls, TypeScript validation, and Next.js production build.

```bash
python -m pytest -q backend/tests/test_m13_link_integrity_gate.py backend/tests/test_m16_wrong_link_precision.py
```

**Research limitations:** All M16 unit-test labels and evidence are fabricated. The change tightens the scoring of future experiments; it does not create independently adjudicated projects, prove source/image attestation, or substantiate ≥95% accuracy. The full research acceptance process still requires independent project-level ground truth, external provenance verification, and audited executable evidence. Keep the change in a draft PR until CI and review pass.
