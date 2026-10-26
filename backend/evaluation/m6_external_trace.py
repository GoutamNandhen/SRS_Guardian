"""Evaluate ranking against *observed positive* external trace links.

External Dronology graph paths are NOT verified requirements-to-function pairs,
non-observed links are NOT negatives, and neither source-code behavioral testing
nor cross-project generalization is present here.

Usage:
 python -m backend.evaluation.m6_external_trace --dataset benchmarks/m6/dronology_observed_trace_links.json
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any

SCHEMA = "m6-external-trace-v1"
STOP = frozenset("the a an to from at and by of for in on with as when where its is are be shall must will or if user users system application during each all any into have has that this then given could should".split())
CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*")


class ExternalTraceError(ValueError):
    """Unsupported or untrustworthy benchmark structure."""


def tokens(text: str) -> list[str]:
    split = CAMEL.sub(" ", text.replace("_", " "))
    return [x for x in (t.lower() for t in WORD.findall(split)) if x not in STOP and len(x) > 2]


def basename_tokens(path: str) -> list[str]:
    return tokens(path.rsplit("/", 1)[-1].rsplit(".", 1)[0])


def load_dataset(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    data = json.loads(raw)
    if data.get("schema_version") != SCHEMA or data.get("no_negative_labels") is not True:
        raise ExternalTraceError("Requires observed positive links with explicitly unknown negatives")
    if data.get("not_executable_conformance") is not True or data.get("one_project_two_versions") is not True:
        raise ExternalTraceError("Data provenance / scope flags missing")
    versions = data.get("versions")
    if not isinstance(versions, list) or {v.get("version") for v in versions} != {"V0", "V1"}:
        raise ExternalTraceError("Expected both pinned Dronology versions")
    for ver in versions:
        candidates = ver.get("candidate_code_paths")
        requirements = ver.get("requirements")
        if not isinstance(candidates, list) or not candidates or len(candidates) != len(set(candidates)):
            raise ExternalTraceError("Invalid unique code candidate list")
        if not isinstance(requirements, list) or not requirements:
            raise ExternalTraceError("Missing requirements")
        candidate_set = set(candidates)
        req_ids = set()
        for req in requirements:
            rid = req.get("requirement_id")
            if not isinstance(rid, str) or not rid or rid in req_ids:
                raise ExternalTraceError("Duplicate or malformed requirement ID")
            req_ids.add(rid)
            if not isinstance(req.get("text"), str) or not req["text"].strip():
                raise ExternalTraceError("Missing requirement text")
            linked = req.get("observed_link_paths")
            if not isinstance(linked, list) or len(linked) != len(set(linked)):
                raise ExternalTraceError("Malformed link list")
            if not set(linked).issubset(candidate_set):
                raise ExternalTraceError("Known positive points outside candidate universe")
        if not re.fullmatch("[0-9a-f]{40}", ver.get("source_blob_sha", "")):
            raise ExternalTraceError("Missing source revision identity")
    data["_fixture_sha256"] = sha256(raw).hexdigest()
    return data


def bm25_scores(query: str, docs: list[list[str]]) -> list[float]:
    q = set(tokens(query))
    n = len(docs)
    lengths = [max(1, len(doc)) for doc in docs]
    avg = sum(lengths) / n
    df = Counter(t for doc in docs for t in set(doc))
    scores = []
    for doc, length in zip(docs, lengths):
        tf = Counter(doc)
        score = 0.0
        for word in q:
            if word not in tf:
                continue
            idf = math.log1p((n - df[word] + 0.5) / (df[word] + 0.5))
            score += idf * tf[word] * 2.2 / (tf[word] + 1.2 * (0.25 + 0.75 * length / avg))
        scores.append(score)
    return scores


def rank(query: str, paths: list[str], method: str) -> list[str]:
    if method == "path_bm25":
        doc_tokens = [tokens(p) for p in paths]
    elif method == "filename_bm25":
        doc_tokens = [basename_tokens(p) for p in paths]
    else:
        raise ExternalTraceError(f"Unrecognized retrieval baseline: {method}")
    scores = bm25_scores(query, doc_tokens)
    # For zero-overlap queries, do NOT count a predictable alphabetical ordering as a ranking.
    return [paths[i] for i in sorted(range(len(paths)), key=lambda i: (-scores[i], paths[i])) if scores[i] > 0]


def wilson(successes: int, total: int, z: float = 1.96) -> list[float] | None:
    if total == 0:
        return None
    p = successes / total
    z2 = z * z
    denom = 1 + z2 / total
    center = (p + z2 / (2 * total)) / denom
    half = z / denom * math.sqrt(p * (1-p)/total + z2/(4*total*total))
    return [round(max(0.0, center-half), 4), round(min(1.0, center+half), 4)]


def evaluate_version(version: dict[str, Any], method: str) -> dict[str, Any]:
    records = []
    for req in version["requirements"]:
        positives = set(req["observed_link_paths"])
        if not positives:
            continue  # no known positive; NOT a negative example
        ranking = rank(req["text"], version["candidate_code_paths"], method)
        first_rank = next((i for i,p in enumerate(ranking, 1) if p in positives), None)
        hits = {str(k): bool(set(ranking[:k]) & positives) for k in (1,5,10)}
        recall5 = len(set(ranking[:5]) & positives)/len(positives)
        records.append({"requirement_id":req["requirement_id"],"known_positive_count":len(positives),
                        "first_observed_link_rank": first_rank,
                        "top5_observed_link_recall":round(recall5, 4),"hit_at":hits,
                        "retrieved_candidates":len(ranking)})
    size = len(records)
    successes = {str(k):sum(int(r["hit_at"][str(k)]) for r in records) for k in (1,5,10)}
    return {"version":version["version"], "method":method,
            "total_requirements":len(version["requirements"]),
            "requirements_with_observed_code_link":size,
            "code_candidate_paths":len(version["candidate_code_paths"]),
            "observed_positive_links":sum(len(r["observed_link_paths"]) for r in version["requirements"]),
            "scope":"single-project observed positive transitive trace links; non-links not assumed negative",
            "hit_at_k":{k:round(v/size,4) if size else None for k,v in successes.items()},
            "hit_at_k_wilson_95":{k:wilson(v,size) for k,v in successes.items()},
            "mrr_known_positive":round(sum(1/r["first_observed_link_rank"] if r["first_observed_link_rank"] else 0 for r in records)/size,4) if size else None,
            "mean_observed_positive_recall_at_5":round(sum(r["top5_observed_link_recall"] for r in records)/size,4) if size else None,
            "observed_link_coverage":round(size/len(version["requirements"]),4),
            "cases":records}


def evaluate_all(data: dict[str,Any]) -> dict[str,Any]:
    runs = []
    for v in data["versions"]:
        for method in ("filename_bm25", "path_bm25"):
            runs.append(evaluate_version(v,method))
    return {"dataset_name":data["dataset_name"],"upstream_repository":data["upstream_repository"],
            "fixture_sha256":data["_fixture_sha256"],
            "research_95_eligible":False,"has_true_negatives":False,"independent_projects":1,
            "has_executable_conformance_labels":False,
            "warning":"Do not interpret Hit@K as accuracy, precision or conformance. Small, linked-only, same-project dataset with potentially incomplete observed links.",
            "runs":runs}


def main() -> None:
    p=argparse.ArgumentParser(description="Observed positive trace link retrieval on external Dronology safety case artifacts")
    p.add_argument("--dataset",type=Path,default=Path("benchmarks/m6/dronology_observed_trace_links.json"))
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=evaluate_all(load_dataset(args.dataset))
    output=json.dumps(result,indent=2,ensure_ascii=False)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output,encoding="utf-8")
    print(json.dumps({"research_95_eligible":result["research_95_eligible"],
                      "metrics":[{"version":r["version"],"method":r["method"],
                                  "linked_requirements":r["requirements_with_observed_code_link"],
                                  "hit_at_5":r["hit_at_k"]["5"],"mrr":r["mrr_known_positive"]} for r in result["runs"]]},indent=2))

if __name__ == "__main__":
    main()
