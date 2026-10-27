"""M27: pinned normative DSP 2025-1 -> real EDC implementation review evidence.

Only downloads and reads allowlisted, hash-verified static upstream files.
Produces M20 blinded link review and UNANSWERED behavioral review templates.
No third-party code is imported, built, executed, or declared conformant.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from backend.evaluation.m20_annotation_queue import build_queue, write_outputs
from backend.evaluation.m25_source_grounded_teastore import rank_source

SPEC_REPO = "eclipse-dataspace-protocol-base/DataspaceProtocol"
SPEC_COMMIT = "8c20a5b7427f6b43c834270ea8d30e3cdefb171e"
CODE_REPO = "eclipse-edc/Connector"
CODE_COMMIT = "29b9be1dfc8a95c7cc911e9f413202ac67bd2c31"
TCK_REPO = "eclipse-dataspacetck/dsp-tck"
TCK_COMMIT = "61bc3d2d7f81bd5b1eee164621872fd6808eb185"
SPEC_PATH = "specifications/catalog/catalog.binding.https.md"
TCK_PATH = "dsp/dsp-catalog/src/main/java/org/eclipse/dataspacetck/dsp/verification/catalog/Catalog01Test.java"
CODE_PATHS = (
    "data-protocols/dsp/dsp-2025/dsp-catalog-2025/dsp-catalog-http-api-2025/src/main/java/org/eclipse/edc/protocol/dsp/catalog/http/api/v2025/controller/DspCatalogApiController20251.java",
    "data-protocols/dsp/dsp-lib/src/main/java/org/eclipse/edc/protocol/dsp/catalog/http/api/controller/BaseDspCatalogApiController.java",
    "data-protocols/dsp/dsp-lib/src/main/java/org/eclipse/edc/protocol/dsp/catalog/validation/CatalogRequestMessageValidator.java",
    "data-protocols/dsp/dsp-lib/src/main/java/org/eclipse/edc/protocol/dsp/catalog/http/api/decorator/CatalogPaginationResponseDecorator.java",
)
# Git blob SHA-1 values read at these immutable commits using the GitHub API.
FILES = {
    SPEC_REPO: {
        "LICENSE": "2bb9ad240fa04c8cf706a4901c4807878e90c2dc",
        SPEC_PATH: "638d6cc7c157b3ad9eedc8e3eae87a6f120c964d",
    },
    CODE_REPO: {
        "LICENSE": "2bb9ad240fa04c8cf706a4901c4807878e90c2dc",
        CODE_PATHS[0]: "8c3f63d2a84d326d8c962bda0a9933a295bf5970",
        CODE_PATHS[1]: "cdc93b141bce8f4813ed553926675ea553a1399c",
        CODE_PATHS[2]: "a42462716ad29a6d6218e05b785c48ebbbb291d0",
        CODE_PATHS[3]: "8c770a8bb77628690850cf4364641c4dfc7843f0",
    },
    TCK_REPO: {
        "LICENSE.md": "2bb9ad240fa04c8cf706a4901c4807878e90c2dc",
        TCK_PATH: "c25a33fec284ba10f36ab486325b9e705a0b4b61",
    },
}
COMMITS = {SPEC_REPO: SPEC_COMMIT, CODE_REPO: CODE_COMMIT, TCK_REPO: TCK_COMMIT}
PROJECT = "ECLIPSE_EDC_DSP_2025_CATALOG_M27"
MAX_BYTES = 2_000_000
# Literal excerpts are checked against the pinned normative specification.
REQUIREMENTS = (
    ("DSP_CAT_MEDIA", "All request and response messages MUST use the `application/json` media type.",
     "All request and response messages MUST", 13, 13),
    ("DSP_CAT_FILTER_400", "If a filter expression is not supported by an implementation, it MUST return a HTTP 400 (Bad Request) response.",
     "If a filter expression is not supported", 45, 46),
    ("DSP_CAT_SUCCESS_200", "If the request is successful, the [=Catalog Service=] MUST return an HTTP 200 (OK) with a response body containing a [Catalog](#ack-catalog).",
     "If the request is successful", 50, 51),
    ("DSP_CAT_PAGINATION_LINK", "Pagination data MUST be specified using [Web Linking](https://datatracker.ietf.org/doc/html/rfc5988) and the HTTP `Link` header.",
     "Pagination data", 88, 89),
)


class EvidenceError(ValueError):
    """Invalid upstream source, license, normative excerpt or candidate set."""


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\\0".encode("ascii") + raw).hexdigest()


def _url(repo: str, path: str) -> str:
    return f"https://github.com/{repo}/blob/{COMMITS[repo]}/{path}"


def fetch_pinned() -> dict[str, dict[str, bytes]]:
    """Read only exact static allowlisted files, no redirects or code execution."""
    result = {}
    for repo, paths in FILES.items():
        result[repo] = {}
        for path, expected in paths.items():
            url = f"https://raw.githubusercontent.com/{repo}/{COMMITS[repo]}/{path}"
            request = urllib.request.Request(url, headers={"User-Agent": "srs-guardian-m27-static-evidence"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.geturl() != url or response.status != 200:
                    raise EvidenceError("Unexpected source redirect or HTTP status")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES or git_blob_id(raw) != expected:
                raise EvidenceError("Pinned upstream Git blob mismatch: " + repo + "/" + path)
            result[repo][path] = raw
    return result


def _snapshot_digest(sources: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(sources):
        raw = sources[path]
        name = path.encode("utf-8")
        h.update(len(name).to_bytes(4, "big"))
        h.update(name)
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return h.hexdigest()


def build_evidence(files: dict[str, dict[str, bytes]]) -> dict:
    """Create a complete 4x4 independent review universe; never assign labels."""
    if set(files) != set(FILES):
        raise EvidenceError("Unexpected source repository set")
    for repo, expected_paths in FILES.items():
        if set(files[repo]) != set(expected_paths):
            raise EvidenceError("Missing or unexpected upstream source")
        for path, expected in expected_paths.items():
            if git_blob_id(files[repo][path]) != expected:
                raise EvidenceError("Pinned upstream Git blob mismatch: " + repo + "/" + path)
        license_path = "LICENSE.md" if repo == TCK_REPO else "LICENSE"
        if b"Apache License" not in files[repo][license_path][:128]:
            raise EvidenceError("Apache-2.0 license not verified: " + repo)
    spec = files[SPEC_REPO][SPEC_PATH].decode("utf-8")
    lines = spec.splitlines()
    normalized = re.sub(r"\\s+", " ", spec)
    requirements = []
    for rid, excerpt, anchor, start, end in REQUIREMENTS:
        if excerpt not in normalized or anchor not in lines[start - 1]:
            raise EvidenceError("Normative excerpt or line position drift: " + rid)
        requirements.append({"requirement_id": rid, "requirement_text": excerpt})
    sources = {path: files[CODE_REPO][path] for path in CODE_PATHS}
    for path, raw in sources.items():
        if b"SPDX-License-Identifier: Apache-2.0" not in raw:
            raise EvidenceError("Implementation source license header missing: " + path)
    tck = files[TCK_REPO][TCK_PATH]
    if b"SPDX-License-Identifier: Apache-2.0" not in tck or b"@MandatoryTest" not in tck:
        raise EvidenceError("Expected licensed external TCK test source missing")
    symbols = [
        {"symbol_id": f"EDC_{i:02d}", "source_path": path,
         "qualified_name": Path(path).stem,
         "description": "Real EDC DSP catalog Java implementation; unverified requirement link"}
        for i, path in enumerate(sorted(sources), 1)
    ]
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT,
        "source_commit": CODE_COMMIT,
        "code_snapshot_sha256": _snapshot_digest(sources),
        "requirements": requirements, "symbols": symbols,
        "observed_links": [],  # No author-declared or independently reviewed links.
    }
    queue = build_queue(universe, seed="m27-dsp-normative-edc-complete-4x4-v1",
                        hard_per_requirement=4, random_per_requirement=0)
    if len(queue["queue"]) != 16:
        raise EvidenceError("Incomplete normative-to-implementation candidate universe")
    manifest = {
        repo: {path: {"git_blob_sha1": FILES[repo][path],
                      "sha256": hashlib.sha256(raw).hexdigest(),
                      "url": _url(repo, path), "lines": len(raw.decode("utf-8").splitlines())}
               for path, raw in repo_files.items()}
        for repo, repo_files in files.items()
    }
    citations = {
        rid: {"source_url": _url(SPEC_REPO, SPEC_PATH) + f"#L{start}-L{end}",
              "line_start": start, "line_end": end, "normative_excerpt": excerpt}
        for rid, excerpt, _, start, end in REQUIREMENTS
    }
    reviewer_index = {
        "schema": "m27-review-source-index-1",
        "specification_version": "DSP 2025-1 (pinned repository commit)",
        "requirements": citations,
        "implementation_files": manifest[CODE_REPO],
        "external_compliance_test": manifest[TCK_REPO][TCK_PATH],
        "warning": "All 16 requirement-to-code links UNADJUDICATED. External TCK tests were NOT run and do not establish EDC conformance. Do not infer negative labels from absent links.",
    }
    ranking = {
        rid: rank_source(excerpt, sources)
        for rid, excerpt, _, _, _ in REQUIREMENTS
    }
    internal = {
        "schema": "m27-normative-implementation-evidence-1",
        "project": "Eclipse Dataspace Connector (EDC)",
        "source_specification": SPEC_REPO,
        "specification_version": "2025-1",
        "implementation_repository": CODE_REPO,
        "implementation_commit": CODE_COMMIT,
        "tck_repository": TCK_REPO,
        "tck_commit": TCK_COMMIT,
        "static_files_git_hash_verified": sum(map(len, FILES.values())),
        "normative_requirements": len(requirements),
        "real_implementation_java_files": len(sources),
        "external_tck_java_files": 1,
        "candidate_links_pending_independent_review": len(queue["queue"]),
        "behavioral_cases_pending_independent_review": len(requirements),
        "independently_adjudicated_link_pairs": 0,
        "independently_adjudicated_behavioral_cases": 0,
        "source_subset_not_complete_application": True,
        "cross_repository_version_compatibility_independently_verified": False,
        "source_license_files_verified_apache_2_0": True,
        "independent_gold": False,
        "held_out_project_accuracy_eligible": False,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "conformance_coverage": None,
        "limitations": [
            "Real normative DSP 2025-1 requirements, but only four selected clauses and four EDC implementation files.",
            "The TCK test source is external supporting context, not a run or independent behavioral verdict.",
            "Protocol version compatibility, runtime configuration and full code dependency graph need independent review.",
            "No positive/negative link labels, execution observations, or independently verified conforming/violating revisions.",
            "Frozen M25 source-text retrieval yields candidate rankings only; no gold means no accuracy, precision, recall or coverage.",
            "Two independent reviewers must assess each of 16 links with cited source lines; adjudicate disagreements.",
            "Independent evaluators need controlled, approved EDC runtime tests or trusted reproducible behavioral evidence for all four requirements, including real violation cases.",
        ],
    }
    return {"queue": queue, "reviewer_index": reviewer_index,
            "internal": internal, "manifest": manifest,
            "candidate_universe": universe, "rankings_unscored": ranking}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_evidence(fetch_pinned())
    reviewers = args.out_dir / "reviewers"
    internal = args.out_dir / "internal"
    write_outputs(result["queue"], reviewers)
    # M20 manifest includes lexical sampling origin; do not give it to reviewers.
    reviewers.joinpath("manifest.json").unlink()
    reviewers.joinpath("source_index.json").write_text(
        json.dumps(result["reviewer_index"], indent=2) + "\\n", encoding="utf-8")
    for reviewer in ("A", "B"):
        rows = [
            {"requirement_id": rid, "reviewer": reviewer,
             "specification_url": result["reviewer_index"]["requirements"][rid]["source_url"],
             "implementation_commit": CODE_COMMIT,
             "actual_behavior_observed": None, "conformance_label": None,
             "violation_label": None, "trusted_execution_evidence": None,
             "source_line_evidence": None, "annotation_status": "pending"}
            for rid, _, _, _, _ in REQUIREMENTS
        ]
        reviewers.joinpath(f"behavior_reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\\n" for row in rows), encoding="utf-8")
    reviewers.joinpath("REVIEW_INSTRUCTIONS.md").write_text(
        "# M27 independent review\\n\\n"
        "Review 16 blinded requirement-to-code pairs using pinned spec and EDC source links; "
        "record linked/not-linked/uncertain and exact source lines independently. "
        "Adjudicate disagreements with a third reviewer.\\n\\n"
        "Separately evaluate four normative behaviors against a verified compatible EDC runtime "
        "using approved reproducible execution evidence; do NOT infer behavioral conformance "
        "from static code or TCK source. Record real conforming and violating revisions, "
        "or leave all labels NULL. This packet contains no gold labels.\\n",
        encoding="utf-8")
    internal.mkdir(parents=True, exist_ok=True)
    internal.joinpath("m20_sampling_manifest.json").write_text(
        json.dumps(result["queue"]["manifest"], indent=2) + "\\n", encoding="utf-8")
    for key in ("internal", "manifest", "candidate_universe", "rankings_unscored"):
        internal.joinpath(key + ".json").write_text(
            json.dumps(result[key], indent=2) + "\\n", encoding="utf-8")
    print(json.dumps({
        "verified_static_files": result["internal"]["static_files_git_hash_verified"],
        "normative_requirements": result["internal"]["normative_requirements"],
        "real_java_files": result["internal"]["real_implementation_java_files"],
        "pending_link_reviews": result["internal"]["candidate_links_pending_independent_review"],
        "pending_behavior_reviews": result["internal"]["behavioral_cases_pending_independent_review"],
        "independent_gold": False,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "conformance_coverage": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
