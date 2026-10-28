"""M36: reconcile independent M35 review exports without inventing gold labels.

No external project code is executed. Agreement is not adjudication.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

PROJECTS = {"edc": (4, 4), "pip": (6, 6)}
MUTABLE = {
    "link_label", "annotation_status", "evidence_notes", "reviewer",
    "conformance_label", "violation_label", "status", "observed_offers",
    "observed_behavior", "approved_runtime_evidence", "reviewer_notes",
    "independent_reviewer_notes",
}
METRICS = ("conformance_accuracy", "violation_precision", "violation_recall", "conformance_coverage")


def load(path: Path, expected: int, reviewer: str, kind: str) -> dict:
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError(f"Missing or oversized reviewer submission: {path}")
    rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]
    if len(rows) != expected:
        raise ValueError(f"Wrong case count in {path}: {len(rows)} != {expected}")
    result = {}
    for row in rows:
        identity = f"reviewer_{reviewer}" if kind == "link" else reviewer
        if not isinstance(row, dict) or row.get("reviewer") != identity:
            raise ValueError(f"Reviewer identity mismatch in {path}")
        key = (row.get("case_id"), row.get("revision") if kind == "behavior" else None)
        if not isinstance(key[0], str) or not key[0] or key in result:
            raise ValueError(f"Invalid or duplicate case in {path}")
        result[key] = row
    return result


def immutable(row: dict) -> dict:
    return {k: v for k, v in row.items() if k not in MUTABLE}


def valid_decision(row: dict, kind: str) -> bool:
    if kind == "link":
        return (row.get("annotation_status") == "reviewed"
                and row.get("link_label") in ("linked", "not_linked")
                and isinstance(row.get("evidence_notes"), str)
                and bool(row["evidence_notes"].strip()))
    label = row.get("conformance_label")
    observed = row.get("observed_offers")
    if observed is None:
        observed = row.get("observed_behavior")
    return (row.get("status") == "reviewed" and type(label) is bool
            and row.get("violation_label") is (not label)
            and bool(str(row.get("approved_runtime_evidence") or "").strip())
            and bool(str(observed if observed is not None else "").strip())
            and bool(str(row.get("reviewer_notes") or row.get("independent_reviewer_notes") or "").strip()))


def reconcile(root: Path) -> tuple[list[dict], dict]:
    tasks = []
    counts = {"pending_or_incomplete": 0, "reviewer_agreement": 0, "reviewer_disagreement": 0}
    for project, (nlinks, nbehavior) in PROJECTS.items():
        for kind, expected in (("link", nlinks), ("behavior", nbehavior)):
            pattern = "reviewer_{}.jsonl" if kind == "link" else "behavior_reviewer_{}.jsonl"
            folder = root / project / "reviewers"
            a = load(folder / pattern.format("A"), expected, "A", kind)
            b = load(folder / pattern.format("B"), expected, "B", kind)
            if a.keys() != b.keys():
                raise ValueError(f"Reviewer case universe mismatch: {project}/{kind}")
            for key in sorted(a):
                left, right = a[key], b[key]
                if immutable(left) != immutable(right):
                    raise ValueError(f"Immutable evidence differs: {project}/{kind}/{key}")
                complete = valid_decision(left, kind) and valid_decision(right, kind)
                label_field = "link_label" if kind == "link" else "conformance_label"
                outcome = ("pending_or_incomplete" if not complete else
                           "reviewer_agreement" if left[label_field] == right[label_field] else
                           "reviewer_disagreement")
                counts[outcome] += 1
                tasks.append({
                    "project": project, "kind": kind, "case_id": key[0], "revision": key[1],
                    "source": immutable(left),
                    "reviewer_A": {k: v for k, v in left.items() if k in MUTABLE},
                    "reviewer_B": {k: v for k, v in right.items() if k in MUTABLE},
                    "comparison": outcome,
                    "adjudicated_label": None, "adjudicator_identity": None,
                    "adjudication_evidence": None, "adjudication_status": "pending",
                })
    manifest = {
        "schema": "m36-independent-adjudication-handoff-1",
        "projects": len(PROJECTS), "tasks": len(tasks), "comparison_counts": counts,
        "independent_adjudications": 0, "held_out_evaluation": False,
        "external_project_code_executed": False,
        "metrics": {name: None for name in METRICS},
        "next_blocker": "Obtain two genuinely independent evidence-backed submissions, "
                        "then a separate human adjudicator's documented decisions and "
                        "version-compatible behavioral execution evidence. Freeze the verifier "
                        "and evaluate on new held-out projects before calculating research metrics.",
    }
    return tasks, manifest


def write_outputs(tasks: list[dict], manifest: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "adjudication_queue.jsonl").write_text(
        "".join(json.dumps(t, ensure_ascii=False, sort_keys=True) + "\n" for t in tasks),
        encoding="utf-8")
    (out_dir / "adjudication_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# M36 — independent adjudicator handoff", "",
             "All labels remain **pending** until a separate human adjudicator records",
             "a sourced judgment. Reviewer agreement is not gold. Never score this queue",
             "or share it with blinded reviewers.", "",
             f"Cases: {manifest['tasks']}; agreements: {manifest['comparison_counts']['reviewer_agreement']};",
             f"disagreements: {manifest['comparison_counts']['reviewer_disagreement']};",
             f"pending/incomplete: {manifest['comparison_counts']['pending_or_incomplete']}.", "",
             "For each case inspect both independent submissions, pinned source, requirement",
             "authority and revision-compatible runtime evidence. Record adjudicator identity,",
             "rationale, source-line evidence, fixture and environment separately.", "",
             "| Project | Kind | Case | Revision | Reviewer comparison | Adjudication |",
             "|---|---|---|---|---|---|"]
    for t in tasks:
        lines.append(f"| {t['project']} | {t['kind']} | {t['case_id']} | "
                     f"{t['revision'] or '—'} | {t['comparison']} | pending |")
    (out_dir / "ADJUDICATOR_HANDOFF.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--review-root", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args(argv)
    tasks, manifest = reconcile(args.review_root)
    write_outputs(tasks, manifest, args.out_dir)
    print(json.dumps({"tasks": len(tasks), "comparison_counts": manifest["comparison_counts"],
                      "independent_adjudications": 0, "metrics": manifest["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
