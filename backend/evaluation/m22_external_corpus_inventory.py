"""M22: immutable, metadata-only availability audit of external traceability corpora.

Fetches only Git tree metadata and a pinned repository LICENSE. Does not import,
download, execute, or relabel third-party source files. A repository-level
Apache-2.0 LICENSE does NOT establish licensing of bundled third-party datasets.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request

OWNER_REPO = "WM-SEMERU/Sense-traceability"
COMMIT = "05daf75800a99e01b9845232cdf373e142e01bcf"
LICENSE_BLOB = "d3ef6b29be3026bcabacbc8eb92f9242420686e6"
README_BLOB = "36d6356ae9cb83a9dc8a275e94ded6976f3e7772"
PROJECTS = ("albergate", "ebt", "etour", "itrust", "libest", "smos", "dronology")
SHA = re.compile(r"[a-f0-9]{40}\Z")
MAX_BYTES = 5_000_000


class AuditError(ValueError):
    """An upstream source or Git tree cannot be independently verified."""


def _request_json(endpoint: str) -> dict:
    """Fixed-host GitHub API only. No caller-controlled URL or credentials."""
    if not endpoint.startswith("git/trees/") or not re.fullmatch(r"git/trees/[a-f0-9]{40}(?:\?recursive=1)?", endpoint):
        raise AuditError("Unapproved Git API endpoint")
    url = f"https://api.github.com/repos/{OWNER_REPO}/{endpoint}"
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "srs-guardian-static-corpus-audit",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise AuditError("Git tree response too large")
    payload = json.loads(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("tree"), list):
        raise AuditError("Missing Git tree response")
    if payload.get("truncated"):
        raise AuditError("Truncated Git tree cannot support complete inventory")
    return payload


def _entry(tree: list[dict], name: str, kind: str) -> dict | None:
    matches = [e for e in tree if e.get("path") == name and e.get("type") == kind]
    if len(matches) > 1:
        raise AuditError("Ambiguous Git tree entry")
    return matches[0] if matches else None


def _require_sha(entry: dict) -> None:
    if not SHA.fullmatch(str(entry.get("sha", ""))):
        raise AuditError("Malformed Git blob/tree identifier")


def _kind(path: str) -> str:
    p = path.casefold()
    segments = p.split("/")
    if "corpus" in segments and "req" in segments:
        return "requirement_artifact"
    if "corpus" in segments and "src" in segments:
        return "source_artifact"
    if "mappings" in segments or any(x in p for x in ("ground_truth", "gold_standard", "trace_links")):
        return "trace_mapping_candidate"
    if p.endswith(".dvc"):
        return "dvc_pointer"
    return "other"


def _project_inventory(name: str, root: list[dict], load) -> dict:
    ent = _entry(root, name, "tree")
    if ent is None:
        return {"project_id": name, "availability": "not_present_at_pinned_commit",
                "requirements": 0, "source_files": 0, "mapping_candidates": 0,
                "data_rights": "not_verified", "independent_adjudication": False}
    _require_sha(ent)
    response = load(f"git/trees/{ent['sha']}?recursive=1")
    files = []
    for item in response["tree"]:
        if item.get("type") not in ("blob", "commit"):
            continue
        _require_sha(item)
        path = item.get("path")
        if not isinstance(path, str) or not path or path.startswith("/") or ".." in path.split("/"):
            raise AuditError("Invalid source path")
        files.append({
            "path": f"dvc-data/systems/{name}/{path}",
            "git_object_sha1": item["sha"],
            "git_object_type": item["type"],
            "size": item.get("size"),
            "category": _kind(path),
        })
    files.sort(key=lambda f: f["path"])
    categories = Counter(f["category"] for f in files)
    return {
        "project_id": name, "availability": "git_tree_present",
        "tree_sha1": ent["sha"], "total_git_objects": len(files),
        "requirements": categories["requirement_artifact"],
        "source_files": categories["source_artifact"],
        "mapping_candidates": categories["trace_mapping_candidate"],
        "dvc_pointers": categories["dvc_pointer"],
        "gitlinks": sum(f["git_object_type"] == "commit" for f in files),
        "data_rights": "not_verified",
        "independent_adjudication": False,
        "source_code_executed": False,
        "objects": files,
    }


def build_audit(load=_request_json) -> dict:
    root = load(f"git/trees/{COMMIT}")
    license_entry = _entry(root["tree"], "LICENSE", "blob")
    readme_entry = _entry(root["tree"], "README.md", "blob")
    if not license_entry or not readme_entry:
        raise AuditError("Pinned upstream license/README absent")
    if license_entry.get("sha") != LICENSE_BLOB or readme_entry.get("sha") != README_BLOB:
        raise AuditError("Pinned license or README changed")
    dvc = _entry(root["tree"], "dvc-data", "tree")
    if dvc is None:
        raise AuditError("No upstream dvc-data directory")
    _require_sha(dvc)
    data_tree = load(f"git/trees/{dvc['sha']}")
    systems = _entry(data_tree["tree"], "systems", "tree")
    if systems is None:
        raise AuditError("No upstream systems directory")
    _require_sha(systems)
    projects_tree = load(f"git/trees/{systems['sha']}")
    projects = [_project_inventory(name, projects_tree["tree"], load) for name in PROJECTS]
    return {
        "schema_version": "m22-external-corpus-availability-1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "upstream": OWNER_REPO, "commit": COMMIT,
        "repository_license": "Apache-2.0",
        "repository_license_blob_sha1": LICENSE_BLOB,
        "repository_readme_blob_sha1": README_BLOB,
        "license_scope_warning": "Repository license verified by pinned Git blob, but third-party dataset redistribution and reuse rights have NOT been independently verified.",
        "projects": projects,
        "project_count": len(projects),
        "projects_with_requirements_source_and_mapping_candidates": [
            p["project_id"] for p in projects
            if p["requirements"] and p["source_files"] and p["mapping_candidates"]
        ],
        "independently_adjudicated_projects": 0,
        "conformance_accuracy": None,
        "violation_precision": None, "violation_recall": None,
        "conformance_coverage": None, "research_95_eligible": False,
        "annotation_next_steps": [
            "Confirm rights for each bundled third-party corpus with upstream primary sources.",
            "Check actual requirement, source and mapping file contents against Git object IDs.",
            "Identify author-declared links without treating absent links as verified negatives.",
            "Create M20 blinded review queues from real projects, masking source trace hints.",
            "Obtain two independent reviewers and adjudicate link decisions.",
            "Collect independent executable behavioral conformance/violation labels; do not infer from trace links.",
        ],
        "caution": "Git tree metadata alone cannot establish that artifact contents are usable or that original links are correct.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = build_audit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "upstream": result["upstream"], "commit": result["commit"],
        "project_counts": [
            {k: p.get(k) for k in ("project_id", "availability", "requirements", "source_files", "mapping_candidates")}
            for p in result["projects"]
        ],
        "candidate_projects": result["projects_with_requirements_source_and_mapping_candidates"],
        "research_95_eligible": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
