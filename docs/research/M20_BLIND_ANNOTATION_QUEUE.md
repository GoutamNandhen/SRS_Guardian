# M20 — Reproducible blinded requirement-to-code annotation queue

**Status:** A data-acquisition instrument, not an accuracy improvement or independently labeled benchmark.

## Problem addressed

The M1–M19 acceptance gates need independently adjudicated positive **and negative** requirement-to-code candidate pairs from unseen software projects. Existing Dronology observations cover one project and are positive trace links only. Declaring every unobserved link a negative would contaminate ground truth because missing links are not necessarily false. Selecting only easy random mismatches can also inflate link precision.

M20 generates a **blinded annotation queue**, not gold labels, using three explicitly recorded sampling origins:

1. observed_unverified: previously observed trace links (still require independent confirmation).
2. lexical_confusable_unverified: high lexical-overlap alternatives (hard *candidates*, not assumed negatives).
3. seeded_random_unverified: deterministic seeded SHA-256 ordering of remaining candidates, sampled without replacement.

All origins are recorded in a separate manifest **that must not be shared with reviewers**. Reviewer A and B JSONL files contain the same candidate pairs, with link_label=null, annotation_status=pending, and evidence_notes=null. No link or conformance ground truth is created automatically. Each pair is identified by project ID, source commit, requirement ID and symbol ID; the source snapshot SHA-256 is recorded in the manifest. The full universe and blinded queue have canonical SHA-256 fingerprints. Input order does not affect the selection.

## Reproduction (synthetic fixture only)

Run from the repository root:

    python -m pytest -q backend/tests/test_m20_annotation_queue.py

    python -m backend.evaluation.m20_annotation_queue --universe benchmarks/m20/synthetic_candidate_universe.json --seed preregistered-study-seed-v1 --hard-per-requirement 2 --random-per-requirement 2 --out-dir /tmp/srs-m20-synthetic-annotation

The example has **invented** project metadata and **no real source**. Do not include it in research metrics. The CLI outputs manifest.json, blind_queue.jsonl, reviewer_A.jsonl and reviewer_B.jsonl. manifest.json is restricted to research coordinators because it exposes candidate origins.

## Input contract

The m20-candidate-universe-1 JSON requires project_id, a 40/64-character lowercase hexadecimal source_commit, a 64-character lowercase code_snapshot_sha256, a nonempty requirements list (requirement_id, requirement_text), and a symbols list (symbol_id, source_path, qualified_name, optional description). observed_links may list known-but-unverified (requirement_id, symbol_id) pairs. All observed links must point to elements of this universe. Invalid/duplicate identifiers, malformed digests and more than 2 million possible pairs fail closed. The generator does not fetch source code or execute applications.

## Required real-data workflow

- Use **authorized** project source and pin the exact commit and source archive digest; verify project identity and license. Reserve complete projects for the held-out test split before developing inference methods.
- Pre-register the sampling seed, stratum sizes, full candidate universe, gold lock process and study protocol **before** annotating. Freeze the queue digest and manifest; keep test labels inaccessible to model developers.
- Two **actual independent human annotators** must review source code at the pinned revision and write supporting source/test evidence. The reviewer_A/B names are file templates, **not** evidence of human independence.
- Adjudicate disagreements, preserve individual and final decisions, identify unresolved/uncertain pairs and record selection probabilities or sampling weights where scientifically justified. Never treat absent observed links or unlabeled candidates as gold negatives.
- Independently label conformance (conforms/violates) **only** for verified positive links with executable or reviewed behavioral oracles. Record genuine test evidence and failure types. M20 does not supply conformance labels.
- Audit dataset leakage, snapshot independence, near-duplicate requirements and class/project support with the M1–M19 gates. A purposive hard-negative sample and the random remainder **are not a representative population sample**; report metrics separately by stratum and do not claim population accuracy without a defensible sampling design.

**Research acceptance:** Still unproven. No independent real-world cases, no measured ≥95% accuracy, ≥95% violation precision or ≥90% violation recall result from M20. It only reduces the manual data collection and labeling setup work.
