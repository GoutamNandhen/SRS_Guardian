"""M5: evidence-aware, leakage-checked comparative benchmark analysis.

No AI inference, no arbitrary code execution. Predictions are scored by the M1
verifier; synthetic or insufficiently documented data NEVER certify 95%.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from backend.evaluation.evaluate_conformance import (
    EvaluationError, OUTCOMES, _evidence_ok, evaluate, read_jsonl, validate_gold,
    validate_predictions,
)

REAL_REQUIRED = (
    "public_source_url", "source_license", "code_snapshot_sha256",
    "annotator_1", "annotator_2", "adjudication_record",
    "oracle_provenance", "reproduction_instructions",
)


def canonical_digest(rows: list[dict[str, Any]]) -> str:
    return hashlib.sha256(json.dumps(rows, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", s.casefold()))


def audit_benchmark(gold: list[dict[str, Any]], *, expected_sha256: str | None = None,
                    near_duplicate_threshold: float = .90) -> dict[str, Any]:
    validate_gold(gold)
    benchmark_fingerprint = canonical_digest(gold)
    if expected_sha256 is not None and not (len(expected_sha256) == 64 and benchmark_fingerprint == expected_sha256):
        raise EvaluationError("Benchmark fingerprint does not match the preregistered lock")
    warnings: list[str] = []
    critical: list[str] = []
    seen_codes: dict[tuple[str, str], str] = {}
    split_tokens: dict[str, list[tuple[str, set[str]]]] = defaultdict(list)
    project_split: dict[str, str] = {}
    # Distinct project_id strings are not sufficient evidence of independent
    # software. Forks/aliases can share exactly the same source snapshot.
    real_snapshot_projects: dict[str, tuple[str, str, str]] = {}
    for row in gold:
        cid, split = row["case_id"], row["split"]
        project_split[row["project_id"]] = split
        code_id = (row["source_commit"], row["candidate_code_ref"])
        if code_id in seen_codes and seen_codes[code_id] != split:
            critical.append(f"Same code snapshot and symbol appear in multiple splits: {cid}")
        seen_codes[code_id] = split
        if row["dataset_status"] == "real_adjudicated":
            if row["adjudication_status"] != "adjudicated":
                critical.append(f"{cid}: real-world case must have completed adjudication; draft labels are not accepted")
            for k in REAL_REQUIRED:
                if not isinstance(row.get(k), str) or not row[k].strip():
                    critical.append(f"{cid}: missing real-world provenance field {k}")
            if row.get("annotator_1") == row.get("annotator_2"):
                critical.append(f"{cid}: two independent annotation identities are required")
            snapshot_digest = row.get("code_snapshot_sha256")
            if not isinstance(snapshot_digest, str) or re.fullmatch(r"[0-9a-f]{64}", snapshot_digest) is None:
                critical.append(f"{cid}: code_snapshot_sha256 must be a lowercase 64-hex SHA-256 digest")
            else:
                earlier = real_snapshot_projects.get(snapshot_digest)
                if earlier is not None and earlier[0] != row["project_id"]:
                    previous_project, previous_split, previous_case = earlier
                    critical.append(
                        f"{cid}: identical source snapshot SHA-256 across distinct project IDs "
                        f"({previous_project}/{previous_split}/{previous_case} vs "
                        f"{row['project_id']}/{split}/{cid}); cannot count as independent projects"
                    )
                else:
                    real_snapshot_projects[snapshot_digest] = (row["project_id"], split, cid)
        split_tokens[split].append((cid, _tokens(row["requirement_text"])))
    # Flag near-exact paraphrases crossing splits (a safeguard, not semantic deduplication).
    # Exact overlap is already rejected by the M1 scorer.
    seen_pairs: set[tuple[str, str]] = set()
    splits = sorted(split_tokens)
    for i, one in enumerate(splits):
        for two in splits[i + 1:]:
            for ida, a in split_tokens[one]:
                if len(a) < 4:
                    continue
                for idb, b in split_tokens[two]:
                    if len(b) < 4:
                        continue
                    sim = len(a & b) / len(a | b) if a | b else 0.0
                    if sim >= near_duplicate_threshold and (ida, idb) not in seen_pairs:
                        warnings.append(f"Near-duplicate across splits: {ida}, {idb} (Jaccard={sim:.3f})")
                        seen_pairs.add((ida, idb))
    sources = Counter(r["dataset_status"] for r in gold)
    return {
        "fingerprint_sha256": benchmark_fingerprint,
        "cases": len(gold),
        "projects": len(project_split),
        "real_distinct_source_snapshots": len(real_snapshot_projects),
        "splits": dict(Counter(r["split"] for r in gold)),
        "source_kinds": dict(sources),
        "critical_issues": critical,
        "warnings": warnings[:250],
        "research_eligible_by_provenance": not critical and sources.get("real_adjudicated", 0) == len(gold),
        "note": "Project IDs alone do not establish independent projects. This audit blocks exact source snapshot reuse across distinct real project IDs and rejects draft adjudications. Its fingerprint identifies the canonical gold rows, not a source archive. It cannot detect modified forks, repackaged identical code, or falsified digests. An independent human must verify all provenance claims. No numerical performance claim follows from this audit.",
    }


def _decision_correct(gold: dict[str, Any], pred: dict[str, Any] | None,
                      evidence_root: Path) -> bool:
    if not gold["gold_link"] or pred is None:
        return False
    if pred.get("decision") not in {"conforms", "violates"} or pred.get("predicted_link") is not True:
        return False
    if pred.get("source_commit") != gold["source_commit"]:
        return False
    if not _evidence_ok(pred, gold, evidence_root):
        return False
    return pred["decision"] == gold["gold_conformance"]


def _wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if not n:
        return None
    p = k / n
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    rad = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / den
    return [max(0, center - rad), min(1, center + rad)]


def compare_systems(gold: list[dict[str, Any]], systems: dict[str, list[dict[str, Any]]], *,
                    evidence_roots: dict[str, Path], split: str = "test",
                    benchmark_lock: str | None = None) -> dict[str, Any]:
    if len(systems) < 2:
        raise EvaluationError("Comparison requires at least two real system prediction sets")
    if set(systems) != set(evidence_roots):
        raise EvaluationError("Each system requires an explicit evidence artifact root")
    audit = audit_benchmark(gold, expected_sha256=benchmark_lock)
    # No publication-grade acceptance without an independently registered gold lock
    # and provenance review; M1 alone cannot establish those facts.
    m5_claim_eligible = bool(benchmark_lock) and audit["research_eligible_by_provenance"] and not audit["warnings"] and not audit["critical_issues"]
    results: dict[str, Any] = {}
    lookup: dict[str, dict[str, dict[str, Any]]] = {}
    for name, predictions in sorted(systems.items()):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name):
            raise EvaluationError("Invalid system name")
        pm = validate_predictions(predictions, {r["case_id"] for r in gold})
        lookup[name] = pm
        metrics = evaluate(gold, predictions, split=split, evidence_root=evidence_roots[name])
        acceptance = dict(metrics["acceptance"])
        if not m5_claim_eligible:
            acceptance["m1_raw_status_before_m5_audit"] = acceptance["status"]
            acceptance["eligible"] = False
            acceptance["passed"] = False
            acceptance["status"] = "BLOCKED_BY_M5_PROVENANCE_OR_LOCK"
        results[name] = {
            "conformance": metrics["conformance"],
            "links": metrics["link_pairwise"],
            "acceptance": acceptance,
        }
    selected = [r for r in gold if r["split"] == split and r["gold_link"]]
    strata = {name: {} for name in systems}
    for name in systems:
        for project in sorted({r["project_id"] for r in selected}):
            group = [r for r in selected if r["project_id"] == project]
            correct = sum(_decision_correct(r, lookup[name].get(r["case_id"]), evidence_roots[name]) for r in group)
            strata[name][project] = {"correct": correct, "total": len(group),
                                     "full_denominator_accuracy": correct / len(group),
                                     "wilson_95_interval": _wilson(correct, len(group))}
    # M17: a high micro-accuracy on 500 rows must not hide a tiny or
    # systematically failing independent project. Report full-denominator
    # project accuracy and require minimum label support in EACH project.
    # These checks do not independently authenticate provenance.
    robustness_policy = {
        "minimum_linked_per_project": 50,
        "minimum_unlinked_per_project": 10,
        "minimum_per_conformance_class_per_project": 10,
        "minimum_worst_project_accuracy": 0.90,
        "minimum_project_macro_accuracy": 0.95,
    }
    project_robustness: dict[str, Any] = {}
    for name in systems:
        supports = {}
        accuracies = []
        # M18: enumerate ALL held-out projects, including projects containing
        # only gold-negative candidate pairs. M17's linked-only strata omitted
        # these projects and could hide a lack of link-negative evaluation.
        split_projects = sorted({r["project_id"] for r in gold if r["split"] == split})
        for project in split_projects:
            project_rows = [r for r in gold if r["split"] == split and r["project_id"] == project]
            group = [r for r in project_rows if r["gold_link"]]
            negative_rows = [r for r in project_rows if not r["gold_link"]]
            counts = Counter(r["gold_conformance"] for r in group)
            accuracy = strata[name].get(project, {}).get("full_denominator_accuracy")
            if accuracy is not None:
                accuracies.append(accuracy)
            prediction_map = lookup[name]
            link_decided = sum(
                prediction_map.get(r["case_id"], {}).get("predicted_link") is not None
                for r in project_rows
            )
            negative_correct = sum(
                prediction_map.get(r["case_id"], {}).get("predicted_link") is False
                for r in negative_rows
            )
            false_link_claims = sum(
                prediction_map.get(r["case_id"], {}).get("predicted_link") is True
                for r in negative_rows
            )
            supports[project] = {
                "linked": len(group),
                "unlinked": len(negative_rows),
                "class_counts": {c: counts[c] for c in OUTCOMES},
                "link_prediction_coverage": link_decided / len(project_rows),
                "unlinked_correctly_rejected": negative_correct,
                "unlinked_false_link_claims": false_link_claims,
                "unlinked_rejection_rate": (
                    negative_correct / len(negative_rows) if negative_rows else None
                ),
                "support_sufficient": (
                    len(group) >= robustness_policy["minimum_linked_per_project"]
                    and len(negative_rows) >= robustness_policy["minimum_unlinked_per_project"]
                    and all(counts[c] >= robustness_policy["minimum_per_conformance_class_per_project"]
                            for c in OUTCOMES)
                ),
                "accuracy_full_denominator": accuracy,
            }
        # Do not report a project macro accuracy that silently drops a
        # project with zero conformance-linked cases.
        project_macro = (
            sum(accuracies) / len(supports)
            if supports and len(accuracies) == len(supports) else None
        )
        worst_project = min(accuracies) if len(accuracies) == len(supports) and accuracies else None
        sufficient = bool(supports) and all(x["support_sufficient"] for x in supports.values())
        robust = (
            sufficient
            and project_macro is not None
            and project_macro >= robustness_policy["minimum_project_macro_accuracy"]
            and worst_project is not None
            and worst_project >= robustness_policy["minimum_worst_project_accuracy"]
        )
        project_robustness[name] = {
            "project_macro_accuracy": project_macro,
            "worst_project_accuracy": worst_project,
            "minimum_support_met": sufficient,
            "gate_passed": robust,
            "projects": supports,
        }
        acceptance = results[name]["acceptance"]
        acceptance["m17_project_robustness_passed"] = robust
        if m5_claim_eligible and acceptance["passed"] and not robust:
            acceptance["passed"] = False
            acceptance["status"] = "BLOCKED_BY_M17_PROJECT_ROBUSTNESS"
    names = sorted(systems)
    paired: dict[str, Any] = {}
    for i, a in enumerate(names):
        for b in names[i+1:]:
            both = only_a = only_b = neither = 0
            for r in selected:
                ok_a = _decision_correct(r, lookup[a].get(r["case_id"]), evidence_roots[a])
                ok_b = _decision_correct(r, lookup[b].get(r["case_id"]), evidence_roots[b])
                if ok_a and ok_b:
                    both += 1
                elif ok_a:
                    only_a += 1
                elif ok_b:
                    only_b += 1
                else:
                    neither += 1
            paired[f"{a}__vs__{b}"] = {
                "both_correct": both, "only_first_correct": only_a,
                "only_second_correct": only_b, "neither_correct": neither,
                "delta_full_denominator_accuracy": (only_a-only_b)/len(selected) if selected else None,
                "note": "Paired item difference only. Cases within a software project are correlated; use project-cluster inference for any significance claims.",
            }
    return {
        "status": "COMPARISON_ONLY_NOT_PUBLICATION_READY" if not m5_claim_eligible else "PROVENANCE_SCREEN_PASSED_NOT_INDEPENDENTLY_AUDITED",
        "audit": audit,
        "selected_split": split,
        "systems": results,
        "project_strata": strata,
        "project_robustness_policy": robustness_policy,
        "project_robustness": project_robustness,
        "paired": paired,
        "interpretation": "Synthetic benchmarks and demo evidence are never proof of 95% on unseen real projects. Missing/unsupported cases count against full-denominator accuracy. M17 requires project-balanced accuracy. M18 also enumerates every held-out project and requires negative link examples in each project to prevent hidden gaps in link evaluation.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--system", action="append", required=True,
                        help="name=path/to/predictions.jsonl; supply at least two")
    parser.add_argument("--evidence", action="append", required=True,
                        help="name=path/to/evidence_directory; supply for every system")
    parser.add_argument("--split", choices=("train", "dev", "validation", "test"), default="test")
    parser.add_argument("--lock", help="Pre-registered gold canonical SHA-256")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    def parse_map(items: list[str], *, files: bool) -> dict[str, Any]:
        out = {}
        for item in items:
            name, sep, raw = item.partition("=")
            if not sep or not name or not raw or name in out:
                parser.error(f"Invalid or duplicate mapping: {item}")
            out[name] = read_jsonl(Path(raw)) if files else Path(raw)
        return out

    try:
        report = compare_systems(read_jsonl(args.gold), parse_map(args.system, files=True),
                                 evidence_roots=parse_map(args.evidence, files=False),
                                 split=args.split, benchmark_lock=args.lock)
    except EvaluationError as exc:
        parser.error(str(exc))
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
