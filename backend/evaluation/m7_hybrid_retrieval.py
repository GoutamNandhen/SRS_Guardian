"""M7: leak-conscious lexical/subword retrieval evaluation on M6 observed links.

This is a *path-text* retrieval experiment. It is NOT meaning-level code analysis:
there are no source bodies, no true-negative labels, no unseen-project test set.

Run from repository root:
 python -m backend.evaluation.m7_hybrid_retrieval \
   --dataset benchmarks/m6/dronology_observed_trace_links.json \
   --output benchmarks/m7/m7_external_results.json
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.evaluation.m6_external_trace import load_dataset, rank as m6_rank, tokens, wilson

METHODS = ("path_bm25", "filename_bm25", "char_tfidf", "hybrid_rrf")


def normalize_path(path: str) -> str:
    """Use only intrinsic path structure and name; never use gold graph links."""
    return " ".join(tokens(path))


def char_rank(query: str, paths: list[str]) -> list[str]:
    """Fixed CPU character 3–5-gram TF-IDF; candidate-only IDF; deterministic ties."""
    if not paths or not query.strip():
        return []
    corpus = [normalize_path(path) for path in paths]
    if not any(corpus) or not tokens(query):
        return []
    # Fit on candidate path text only, not on ground-truth annotations or test labels.
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                          lowercase=True, sublinear_tf=True, dtype=float)
    matrix = vec.fit_transform(corpus)
    query_vec = vec.transform([" ".join(tokens(query))])
    scores = cosine_similarity(query_vec, matrix).ravel()
    return [paths[i] for i in sorted(range(len(paths)),
            key=lambda j: (-scores[j], paths[j])) if scores[i] > 1e-10]


def rrf_rank(query: str, paths: list[str], k: int = 60) -> list[str]:
    """Predeclared equal-weight reciprocal-rank fusion; no outcome-dependent weights."""
    if k <= 0:
        raise ValueError("k must be positive")
    channels = [m6_rank(query, paths, "path_bm25"),
                m6_rank(query, paths, "filename_bm25"), char_rank(query, paths)]
    scores: Counter[str] = Counter()
    for ranked in channels:
        for i, path in enumerate(ranked, 1):
            scores[path] += 1.0 / (k + i)
    return sorted(scores, key=lambda path: (-scores[path], path))


def rank(query: str, paths: list[str], method: str) -> list[str]:
    if method in ("filename_bm25", "path_bm25"):
        return m6_rank(query, paths, method)
    if method == "char_tfidf":
        return char_rank(query, paths)
    if method == "hybrid_rrf":
        return rrf_rank(query, paths)
    raise ValueError(f"Unsupported M7 method: {method}")


def evaluate_version(version: dict[str, Any], method: str) -> dict[str, Any]:
    candidates = version["candidate_code_paths"]
    cases: list[dict[str, Any]] = []
    for req in version["requirements"]:
        known = set(req["observed_link_paths"])
        if not known:
            continue  # unlabeled, never a negative
        ranked = rank(req["text"], candidates, method)
        first = next((pos for pos, path in enumerate(ranked, 1) if path in known), None)
        cases.append({"requirement_id": req["requirement_id"],
                      "known_positive_links":len(known),
                      "first_positive_rank":first,
                      "top5_positive_recall":round(len(known & set(ranked[:5])) / len(known), 6),
                      "hit_at_1": bool(known & set(ranked[:1])),
                      "hit_at_5": bool(known & set(ranked[:5])),
                      "hit_at_10": bool(known & set(ranked[:10])),
                      "returned_count":len(ranked)})
    n=len(cases)
    successes={k:sum(int(x[f"hit_at_{k}"]) for x in cases) for k in (1,5,10)}
    return {"version":version["version"], "method":method,
            "linked_requirements":n,
            "unobserved_link_requirements":len(version["requirements"])-n,
            "candidate_paths":len(candidates),
            "hit_at_k":{str(k):round(successes[k]/n, 6) if n else None for k in (1,5,10)},
            "hit_at_k_wilson95":{str(k):wilson(successes[k],n) for k in (1,5,10)},
            "mrr_known_positives":round(sum(1/c["first_positive_rank"] if c["first_positive_rank"] else 0 for c in cases)/n,6) if n else None,
            "mean_known_positive_recall_at_5":round(sum(x["top5_positive_recall"] for x in cases)/n,6) if n else None,
            "cases":cases}


def paired_comparison(baseline:dict, candidate:dict) -> dict[str, Any]:
    """Paired changes within a version, not significance on independent projects."""
    if baseline["version"] != candidate["version"]:
        raise ValueError("Cannot pair different versions")
    b={x["requirement_id"]:x for x in baseline["cases"]}
    c={x["requirement_id"]:x for x in candidate["cases"]}
    if set(b)!=set(c):
        raise ValueError("Cannot pair different requirement cohorts")
    improved=[i for i in sorted(b) if c[i]["hit_at_5"] and not b[i]["hit_at_5"]]
    worse=[i for i in sorted(b) if b[i]["hit_at_5"] and not c[i]["hit_at_5"]]
    return {"version":baseline["version"],"baseline":baseline["method"],"candidate":candidate["method"],
            "n":len(b), "improved_hit5_ids":improved,"worsened_hit5_ids":worse,
            "net_hit5_change":len(improved)-len(worse),
            "note":"Exploratory same-project differences; not evidence of cross-project generalization."}


def evaluate_all(dataset:dict[str,Any]) -> dict[str,Any]:
    runs=[evaluate_version(ver,method) for ver in dataset["versions"] for method in METHODS]
    pairs=[]
    for version in ("V0","V1"):
        lookup={r["method"]:r for r in runs if r["version"]==version}
        for baseline in ("path_bm25","filename_bm25"):
            for candidate in ("char_tfidf","hybrid_rrf"):
                pairs.append(paired_comparison(lookup[baseline],lookup[candidate]))
    return {"schema_version":"m7-subword-fusion-v1", "fixture_sha256":dataset["_fixture_sha256"],
            "dataset":"SAREC-Lab/SAFA-Artifacts Dronology observed-positive graph paths",
            "methods":list(METHODS),"hyperparameters_frozen":True,
            "hyperparameters":{"char_ngram_range":[3,5],"rrf_k":60,"rrf_channel_weights":[1,1,1]},
            "independent_projects":1,"has_complete_gold_links":False,"has_true_negatives":False,
            "has_executable_conformance_labels":False,"is_m2_ast_evaluation":False,
            "research_95_eligible":False,
            "limitations":"Java path names only, two versions of same project, observed positive labels may be incomplete. Do not report Hit@K as accuracy, precision, conformance, or independent test validation.",
            "runs":runs,"paired":pairs}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset",type=Path,default=Path("benchmarks/m6/dronology_observed_trace_links.json"))
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=evaluate_all(load_dataset(args.dataset))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"eligible_for_95_claim":result["research_95_eligible"],
          "summary":[{"version":r["version"],"method":r["method"],"n":r["linked_requirements"],
          "hit5":r["hit_at_k"]["5"],"mrr":r["mrr_known_positives"]} for r in result["runs"]]},indent=2))

if __name__=="__main__":
    main()
