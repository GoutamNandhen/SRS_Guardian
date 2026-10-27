"""M25: source-content retrieval and a source-grounded, blinded TeaStore review packet.

Uses eleven immutable, hash-verified third-party *static files* from M23.
Never imports, builds, or executes third-party Java. The six published links
are unverified observations, NOT independently adjudicated gold. The three
architecture sentences are NOT behavioral conformance requirements.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.evaluation.m20_annotation_queue import write_outputs
from backend.evaluation.m23_teastore_external import (
    CODE_COMMIT, CODE_FILES, CODE_REPO, DOC_COMMIT, DOC_FILES, DOC_REPO,
    REQ_IDS, build_evidence, fetch_pinned, git_blob_id,
)
from backend.evaluation.m24_cross_corpus_baseline import _teastore_cohort, NO_CONFORMANCE
from backend.evaluation.m7_hybrid_retrieval import rank as path_rank

METHODS = ("path_bm25", "hybrid_rrf", "source_char_tfidf")
K_VALUES = (1, 3, 5)


class EvidenceError(ValueError):
    """Unverified external source, malformed cohort, or leaked labels."""


def _normalize(text: str) -> str:
    """Split Java camelCase identifiers without executing or parsing Java."""
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)


def rank_source(query: str, sources: dict[str, bytes]) -> list[str]:
    """Frozen character 3-5gram TF-IDF on source *bodies*, not trace links.

    No gold link information, observed candidate origin, or evaluation result
    is passed to this function. Zero-similarity candidates are not returned.
    """
    if not isinstance(query, str) or not query.strip() or not sources:
        return []
    paths = sorted(sources)
    texts = []
    for path in paths:
        if not path.endswith(".java") or not isinstance(sources[path], bytes):
            raise EvidenceError("Expected static Java source bytes only")
        try:
            texts.append(_normalize(sources[path].decode("utf-8")))
        except UnicodeDecodeError as exc:
            raise EvidenceError("Invalid UTF-8 source") from exc
    if not any(t.strip() for t in texts):
        return []
    vectorizer = TfidfVectorizer(
        analyzer="char_wb", ngram_range=(3, 5), lowercase=True, sublinear_tf=True
    )
    matrix = vectorizer.fit_transform(texts)
    query_vec = vectorizer.transform([_normalize(query)])
    scores = cosine_similarity(query_vec, matrix).ravel()
    return [paths[i] for i in sorted(
        range(len(paths)), key=lambda j: (-scores[j], paths[j])
    ) if scores[i] > 1e-10]


def score_ranked(ranked: list[str], known: set[str], candidate_paths: set[str]) -> dict:
    """Score *observed positives only* after ranking. Never infer negatives."""
    if len(ranked) != len(set(ranked)) or not set(ranked).issubset(candidate_paths):
        raise EvidenceError("Invalid candidate ranking")
    if not known.issubset(candidate_paths):
        raise EvidenceError("Observed link outside candidate universe")
    return {
        "returned_candidate_count": len(ranked),
        "first_observed_positive_rank": next(
            (i for i, path in enumerate(ranked, 1) if path in known), None
        ),
        "observed_positive_hits_at_k": {
            str(k): len(set(ranked[:k]) & known) for k in K_VALUES
        },
        "ranked_paths": ranked,
    }


def evaluate_cohort(requirements: list[dict], source_bytes: dict[str, bytes]) -> dict:
    """Compare frozen M7 path-only methods with source-content ranking."""
    paths = sorted(source_bytes)
    if not paths or len({r["id"] for r in requirements}) != len(requirements):
        raise EvidenceError("Empty sources or duplicate requirements")
    if not requirements:
        raise EvidenceError("Empty requirement cohort")
    runs = []
    for method in METHODS:
        cases = []
        for req in sorted(requirements, key=lambda r: r["id"]):
            ranked = (rank_source(req["text"], source_bytes)
                      if method == "source_char_tfidf"
                      else path_rank(req["text"], paths, method))
            known = set(req["observed_paths"])
            case = score_ranked(ranked, known, set(paths))
            cases.append({
                "requirement_id": req["id"],
                "observed_positive_count_unverified": len(known),
                **case,
            })
        linked = [case for case in cases if case["observed_positive_count_unverified"]]
        observed = sum(c["observed_positive_count_unverified"] for c in linked)
        runs.append({
            "method": method,
            "linked_statement_count": len(linked),
            "total_statement_count": len(cases),
            "observed_positive_links_unverified": observed,
            "hit_at_k_on_observed_linked_statements": {
                str(k): round(sum(
                    c["observed_positive_hits_at_k"][str(k)] > 0 for c in linked
                ) / len(linked), 6) if linked else None for k in K_VALUES
            },
            "observed_positive_link_recall_at_k": {
                str(k): round(sum(
                    c["observed_positive_hits_at_k"][str(k)] for c in linked
                ) / observed, 6) if observed else None for k in K_VALUES
            },
            "cases": cases,
            "independent_gold": False,
            **NO_CONFORMANCE,
        })
    return {"methods": list(METHODS), "runs": runs}


def source_index(docs: dict[str, bytes], code: dict[str, bytes], queue: dict) -> dict:
    """Blinded source references only; NO observed-link or sampling strata."""
    if set(docs) != set(DOC_FILES) or set(code) != set(CODE_FILES):
        raise EvidenceError("Source set does not match the pinned allowlist")
    for files, expected in ((docs, DOC_FILES), (code, CODE_FILES)):
        for path, raw in files.items():
            if git_blob_id(raw) != expected[path]:
                raise EvidenceError("Source hash mismatch: " + path)
    code_files = {
        path: {
            "url": f"https://github.com/{CODE_REPO}/blob/{CODE_COMMIT}/{path}",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "git_blob_sha1": CODE_FILES[path],
            "line_count": len(raw.decode("utf-8").splitlines()),
        } for path, raw in code.items() if path.endswith(".java")
    }
    req_files = {
        f"SAD_{rid:03d}": {
            "url": (f"https://github.com/{DOC_REPO}/blob/{DOC_COMMIT}/"
                    f"data/ftlr-texts/teastore/{rid}.txt"),
            "sha256": hashlib.sha256(
                docs[f"data/ftlr-texts/teastore/{rid}.txt"]
            ).hexdigest(),
        } for rid in REQ_IDS
    }
    cases = []
    for row in queue["queue"]:
        if row["source_path"] not in code_files or row["requirement_id"] not in req_files:
            raise EvidenceError("Reviewer case lacks a pinned source reference")
        cases.append({
            "case_id": row["case_id"],
            "requirement_id": row["requirement_id"],
            "source_path": row["source_path"],
            "source": code_files[row["source_path"]],
            "requirement": req_files[row["requirement_id"]],
        })
    return {
        "schema_version": "m25-blinded-source-index-1",
        "documentation_repository": DOC_REPO,
        "documentation_commit": DOC_COMMIT,
        "source_repository": CODE_REPO,
        "source_commit": CODE_COMMIT,
        "source_files": code_files,
        "requirement_files": req_files,
        "cases": cases,
        "cases_pending_independent_review": len(cases),
        "link_labels_present": False,
        "warning": "Links, negatives, and behavioral conformance are UNADJUDICATED. "
                   "Reviewers must cite exact source lines; do not share the internal "
                   "observed-link universe, scoring, or sampling-provenance manifest.",
    }


def generate(docs: dict[str, bytes], code: dict[str, bytes]) -> dict:
    """Validate M23 source and produce *separated* internal/reviewer evidence."""
    bundle = build_evidence(docs, code)
    universe, evidence = bundle["universe"], bundle["evidence"]
    project, version, requirements, paths = _teastore_cohort(universe, evidence)
    if (project, version) != ("TeaStore", "M23-five-file-subset"):
        raise EvidenceError("Unexpected project/version")
    selected = {path: code[path] for path in paths}
    ranking = evaluate_cohort(requirements, selected)
    index = source_index(docs, code, bundle["queue"])
    return {
        "reviewer": {"queue": bundle["queue"], "source_index": index},
        "internal": {
            "schema_version": "m25-source-grounded-teastore-1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "project": "TeaStore",
            "source_commit": CODE_COMMIT,
            "source_subset_sha256": universe["code_snapshot_sha256"],
            "source_license": "Apache-2.0",
            "documentation_package_license": "MIT",
            "third_party_documentation_rights_fully_cleared": False,
            "source_files": len(selected),
            "architecture_statements": len(requirements),
            "published_links_unverified": len(universe["observed_links"]),
            "blinded_pairs_pending_review": len(bundle["queue"]["queue"]),
            "independently_adjudicated_link_pairs": 0,
            "independently_adjudicated_behavioral_cases": 0,
            "research_95_eligible": False,
            **NO_CONFORMANCE,
            "comparison": ranking,
            "limitations": [
                "Three architecture statements and five purposively chosen Java files, not full application.",
                "Published links are observations, not independently adjudicated positives.",
                "No verified negatives or executable conformance labels.",
                "Source-content method was developed after viewing the M24 TeaStore baseline; "
                "this is exploratory development-set analysis, NOT held-out validation.",
                "Two independent reviewers must label 15 cases citing source lines; "
                "a third must adjudicate disagreements.",
                "Behavioral conformance requires separate real requirements, "
                "independently verified conforming/violating code revisions and held-out projects.",
            ],
        },
        "universe": universe,
        "evidence": evidence,
        "licenses": bundle["licenses"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = generate(
        fetch_pinned(DOC_REPO, DOC_COMMIT, DOC_FILES),
        fetch_pinned(CODE_REPO, CODE_COMMIT, CODE_FILES),
    )
    review_dir = args.out_dir / "reviewers"
    internal_dir = args.out_dir / "internal"
    review_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)
    write_outputs(result["reviewer"]["queue"], internal_dir / "annotation_provenance")
    write_outputs(result["reviewer"]["queue"], review_dir)
    # M20 write_outputs includes selection provenance. Do not expose it to reviewers.
    (review_dir / "manifest.json").unlink()
    (review_dir / "source_index.json").write_text(
        json.dumps(result["reviewer"]["source_index"], indent=2) + "\n", encoding="utf-8"
    )
    (review_dir / "README.txt").write_text(
        "BLINDED REVIEW: Open blind_queue.jsonl and the corresponding reviewer file.\n"
        "For each of 15 pairs, inspect the exact pinned source and requirement URLs\n"
        "in source_index.json. Record linked/not-linked/uncertain with concrete\n"
        "source line numbers and justification. Work independently; do not view\n"
        "the internal/ artifact or published links. Third-party documentation\n"
        "rights require confirmation before redistribution. These are architecture\n"
        "trace-link judgments, NOT behavioral conformance judgments.\n",
        encoding="utf-8",
    )
    for name, data in (
        ("baseline.json", result["internal"]),
        ("candidate_universe.json", result["universe"]),
        ("source_evidence.json", result["evidence"]),
    ):
        (internal_dir / name).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    for name, raw in result["licenses"].items():
        (internal_dir / name).write_bytes(raw)
    print(json.dumps({
        "project": "TeaStore", "source_files": result["internal"]["source_files"],
        "architecture_statements": result["internal"]["architecture_statements"],
        "review_pairs": result["internal"]["blinded_pairs_pending_review"],
        "independently_adjudicated_cases": 0, "research_95_eligible": False,
        "retrieval": [{
            "method": run["method"],
            "hit_at_1": run["hit_at_k_on_observed_linked_statements"]["1"],
            "observed_positive_recall_at_3": run["observed_positive_link_recall_at_k"]["3"],
        } for run in result["internal"]["comparison"]["runs"]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
