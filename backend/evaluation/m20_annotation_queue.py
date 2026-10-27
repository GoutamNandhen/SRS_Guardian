"""M20: reproducible, blinded requirement-to-code annotation queue.

No candidate is presumed linked or unlinked. This is NOT a source of gold labels,
conformance judgments, accuracy claims, or a substitute for human adjudication.
Only explicit project metadata and symbol descriptions are processed; no code runs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

SCHEMA = "m20-candidate-universe-1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class QueueError(ValueError):
    """Invalid or ambiguous annotation universe; fail closed."""


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def _string(value: Any, field: str, *, limit: int = 5000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise QueueError(f"Missing, empty, or oversized {field}")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    value = _string(value, field, limit=128)
    if not ID.fullmatch(value):
        raise QueueError(f"Invalid {field}")
    return value


def _tokens(value: str) -> set[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _validate(data: Any) -> tuple[list[dict], list[dict], set[tuple[str, str]]]:
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA:
        raise QueueError("Unsupported candidate-universe schema")
    _identifier(data.get("project_id"), "project_id")
    if not HEX_COMMIT.fullmatch(str(data.get("source_commit", ""))):
        raise QueueError("source_commit must be 40- or 64-character lowercase hex")
    if not HEX64.fullmatch(str(data.get("code_snapshot_sha256", ""))):
        raise QueueError("code_snapshot_sha256 must be lowercase SHA-256")
    reqs = data.get("requirements")
    symbols = data.get("symbols")
    positives = data.get("observed_links", [])
    if not isinstance(reqs, list) or not 1 <= len(reqs) <= 5000:
        raise QueueError("Expected 1..5000 requirements")
    if not isinstance(symbols, list) or not 2 <= len(symbols) <= 10000:
        raise QueueError("Expected 2..10000 symbols")
    if len(reqs) * len(symbols) > 2_000_000:
        raise QueueError("Candidate universe exceeds 2,000,000 pairs")
    if not isinstance(positives, list):
        raise QueueError("observed_links must be a list")
    parsed_reqs, parsed_symbols = [], []
    req_ids, symbol_ids = set(), set()
    for req in reqs:
        if not isinstance(req, dict):
            raise QueueError("Malformed requirement")
        rid = _identifier(req.get("requirement_id"), "requirement_id")
        if rid in req_ids:
            raise QueueError("Duplicate requirement_id")
        req_ids.add(rid)
        parsed_reqs.append({"requirement_id": rid,
                            "requirement_text": _string(req.get("requirement_text"), "requirement_text")})
    for symbol in symbols:
        if not isinstance(symbol, dict):
            raise QueueError("Malformed symbol")
        sid = _identifier(symbol.get("symbol_id"), "symbol_id")
        if sid in symbol_ids:
            raise QueueError("Duplicate symbol_id")
        symbol_ids.add(sid)
        parsed_symbols.append({"symbol_id": sid,
                               "source_path": _string(symbol.get("source_path"), "source_path", limit=1024),
                               "qualified_name": _string(symbol.get("qualified_name"), "qualified_name", limit=1024),
                               "description": symbol.get("description", "")})
        if not isinstance(parsed_symbols[-1]["description"], str) or len(parsed_symbols[-1]["description"]) > 2000:
            raise QueueError("Invalid symbol description")
    seen = set()
    for link in positives:
        if not isinstance(link, dict):
            raise QueueError("Malformed observed link")
        rid = _identifier(link.get("requirement_id"), "observed requirement_id")
        sid = _identifier(link.get("symbol_id"), "observed symbol_id")
        if rid not in req_ids or sid not in symbol_ids:
            raise QueueError("Observed link points outside the candidate universe")
        if (rid, sid) in seen:
            raise QueueError("Duplicate observed link")
        seen.add((rid, sid))
    return (sorted(parsed_reqs, key=lambda x: x["requirement_id"]),
            sorted(parsed_symbols, key=lambda x: x["symbol_id"]), seen)


def build_queue(data: dict, *, seed: str, hard_per_requirement: int = 2,
                random_per_requirement: int = 2) -> dict:
    """Construct a blinded candidate set; 'observed' links remain unverified.

    Hard candidates are lexical confusables, not verified negatives. The random
    stratum is deterministic seeded SHA-256 ordering of the remaining symbols.
    Neither stratum establishes an unbiased estimate of production link errors.
    """
    reqs, symbols, observed = _validate(data)
    seed = _string(seed, "seed", limit=100)
    if not 0 <= hard_per_requirement <= 20 or not 0 <= random_per_requirement <= 20:
        raise QueueError("Stratum sizes must be integers between 0 and 20")
    if hard_per_requirement + random_per_requirement == 0 and not observed:
        raise QueueError("No candidates would be sampled")
    universe_digest = _digest({"schema_version": SCHEMA,
                               "project_id": data["project_id"],
                               "source_commit": data["source_commit"],
                               "code_snapshot_sha256": data["code_snapshot_sha256"],
                               "requirements": reqs, "symbols": symbols,
                               "observed_links": sorted([list(x) for x in observed])})
    rows, strata = [], []
    for req in reqs:
        rid = req["requirement_id"]
        qtokens = _tokens(req["requirement_text"])
        by_id = {s["symbol_id"]: s for s in symbols}
        observed_ids = sorted(sid for rr, sid in observed if rr == rid)
        remaining = [s for s in symbols if s["symbol_id"] not in observed_ids]

        def similarity(s: dict) -> float:
            words = _tokens(" ".join((s["source_path"], s["qualified_name"], s["description"])))
            return len(qtokens & words) / len(qtokens | words) if qtokens | words else 0.0

        hard = sorted(remaining, key=lambda s: (-similarity(s), s["symbol_id"]))[:hard_per_requirement]
        hard_ids = {s["symbol_id"] for s in hard}
        pool = [s for s in remaining if s["symbol_id"] not in hard_ids]
        random_ranked = sorted(pool, key=lambda s: (
            _digest([seed, universe_digest, rid, s["symbol_id"]]), s["symbol_id"]))
        random_pick = random_ranked[:random_per_requirement]
        selections = ([(sid, "observed_unverified") for sid in observed_ids]
                      + [(s["symbol_id"], "lexical_confusable_unverified") for s in hard]
                      + [(s["symbol_id"], "seeded_random_unverified") for s in random_pick])
        for sid, origin in selections:
            s = by_id[sid]
            case_id = "PAIR-" + _digest([data["project_id"], data["source_commit"], rid, sid])[:24]
            # No origin, link label, gold decision or hint in the blinded queue.
            rows.append({"case_id": case_id, "project_id": data["project_id"],
                         "source_commit": data["source_commit"],
                         "requirement_id": rid, "requirement_text": req["requirement_text"],
                         "symbol_id": sid, "source_path": s["source_path"],
                         "qualified_name": s["qualified_name"],
                         "description": s["description"]})
            strata.append({"case_id": case_id, "origin": origin})
    rows.sort(key=lambda r: r["case_id"])
    strata.sort(key=lambda r: r["case_id"])
    if len({r["case_id"] for r in rows}) != len(rows):
        raise QueueError("Case ID collision")
    queue_digest = _digest(rows)
    manifest = {
        "schema_version": "m20-annotation-manifest-1",
        "project_id": data["project_id"],
        "source_commit": data["source_commit"],
        "code_snapshot_sha256": data["code_snapshot_sha256"],
        "candidate_universe_sha256": universe_digest,
        "blind_queue_sha256": queue_digest,
        "seed": seed,
        "requirements": len(reqs), "symbols": len(symbols),
        "possible_pairs": len(reqs) * len(symbols),
        "sampled_pairs": len(rows),
        "observed_links_in_universe": len(observed),
        "hard_per_requirement": hard_per_requirement,
        "random_per_requirement": random_per_requirement,
        "stratum_counts": {kind: sum(x["origin"] == kind for x in strata) for kind in (
            "observed_unverified", "lexical_confusable_unverified", "seeded_random_unverified")},
        "sampling_provenance": strata,
        "independent_labels_collected": False,
        "research_95_eligible": False,
        "warning": "Sampling is not gold labeling. All selected pairs are UNLABELED; even observed links need independent verification. The purposive lexical stratum biases performance estimates; independently adjudicate and report sampling design before evaluating. The manifest contains selection origins and must be hidden from blinded reviewers.",
    }
    return {"queue": rows, "manifest": manifest}


def write_outputs(result: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    queue, manifest = result["queue"], result["manifest"]
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "blind_queue.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in queue), encoding="utf-8")
    for reviewer in ("reviewer_A", "reviewer_B"):
        # Null is intentionally unanswered, never a guessed gold label.
        (output_dir / f"{reviewer}.jsonl").write_text("".join(json.dumps({
            **row, "reviewer": reviewer, "link_label": None,
            "evidence_notes": None, "annotation_status": "pending",
        }, ensure_ascii=False, sort_keys=True) + "\n" for row in queue), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--hard-per-requirement", type=int, default=2)
    parser.add_argument("--random-per-requirement", type=int, default=2)
    args = parser.parse_args(argv)
    if not args.universe.is_file() or args.universe.stat().st_size > 5_000_000:
        parser.error("Missing or oversized universe JSON (limit 5 MB)")
    try:
        data = json.loads(args.universe.read_text(encoding="utf-8"))
        result = build_queue(data, seed=args.seed,
                             hard_per_requirement=args.hard_per_requirement,
                             random_per_requirement=args.random_per_requirement)
    except (QueueError, ValueError) as exc:
        parser.error(str(exc))
    write_outputs(result, args.out_dir)
    print(json.dumps({k: result["manifest"][k] for k in (
        "project_id", "possible_pairs", "sampled_pairs", "blind_queue_sha256", "research_95_eligible")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
