"""M52: pinned, inert SWE-bench Verified intake for future M20 annotation.

This is independently *screened issue quality*, NOT independent link or
behavioral-conformance gold. No upstream project code is imported or executed.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from pathlib import Path
from urllib.request import urlopen

DATASET_REV = "c104f840cc67f8b6eec6f759ebc8b2693d585d4a"
DATASET_SHA256 = "a45b1fe4e2f0c8390b2b2938ac83e92ed5979000856808f3679c07812e9e6dcd"
DATASET_PATH = "data/test-00000-of-00001.parquet"
DATASET_URL = (
    "https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified/"
    f"resolve/{DATASET_REV}/{DATASET_PATH}"
)
REPO = "sympy/sympy"
MAX_BYTES = 4_000_000
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
INSTANCE_RE = re.compile(r"sympy__sympy-([0-9]+)\Z")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def download(url: str, *, max_bytes: int = MAX_BYTES) -> bytes:
    if not url.startswith(("https://huggingface.co/", "https://raw.githubusercontent.com/")):
        raise ValueError("Unexpected external source host")
    with urlopen(url, timeout=35) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("External evidence exceeds size limit")
    return data


def verify_dataset(raw: bytes) -> list[dict]:
    if digest(raw) != DATASET_SHA256:
        raise ValueError("Pinned SWE-bench Verified dataset SHA-256 mismatch")
    # pyarrow reads inert Parquet data. No Python or repository source is executed.
    import pyarrow.parquet as pq

    columns = ["repo", "instance_id", "base_commit", "problem_statement",
               "patch", "test_patch", "FAIL_TO_PASS"]
    rows = pq.read_table(io.BytesIO(raw), columns=columns).to_pylist()
    if len(rows) != 500 or len({r["instance_id"] for r in rows}) != 500:
        raise ValueError("Expected 500 unique human-screened instances")
    return rows


def validate_license(raw: bytes) -> None:
    text = raw.decode("utf-8")
    if not all(fragment in text for fragment in (
        "Redistribution and use in source and binary forms",
        "Neither the name of SymPy",
        "THIS SOFTWARE IS PROVIDED",
    )):
        raise ValueError("Pinned SymPy BSD-3-Clause license evidence missing")


def build_manifest(rows: list[dict], *, license_fetch=download, count: int = 3) -> dict:
    """Choose a deterministic bounded candidate set; do not reveal patches to reviewers."""
    if count < 1 or count > 10:
        raise ValueError("Candidate count must be 1..10")
    candidates = sorted((r for r in rows if r.get("repo") == REPO),
                        key=lambda r: r.get("instance_id", ""))
    ids = [r.get("instance_id") for r in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate candidate")
    selected = []
    seen = set()
    for row in candidates:
        match = INSTANCE_RE.fullmatch(str(row.get("instance_id", "")))
        commit = row.get("base_commit")
        if not match or not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
            raise ValueError("Malformed instance identifier or source commit")
        if row["instance_id"] in seen:
            raise ValueError("Duplicate candidate")
        seen.add(row["instance_id"])
        for field in ("problem_statement", "patch", "test_patch"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Missing actual external evidence: {field}")
        if not isinstance(row.get("FAIL_TO_PASS"), str):
            raise ValueError("Missing external test metadata")
        if len(selected) >= count:
            break
        url = f"https://raw.githubusercontent.com/sympy/sympy/{commit}/LICENSE"
        license_raw = license_fetch(url)
        validate_license(license_raw)
        selected.append({
            "instance_id": row["instance_id"],
            "review_case_id": f"CASE-{len(selected) + 1:03d}",
            "requirement_text": row["problem_statement"],
            "project": REPO,
            "source_commit": commit,
            "source_snapshot_url": f"https://github.com/sympy/sympy/tree/{commit}",
            "historical_pr_url": f"https://github.com/sympy/sympy/pull/{match.group(1)}",
            "dataset_revision": DATASET_REV,
            "dataset_sha256": DATASET_SHA256,
            "license_url": url,
            "license_sha256": digest(license_raw),
            "license_class": "BSD-3-Clause (text checked at pinned base commit)",
            "requirement_sha256": digest(row["problem_statement"].encode("utf-8")),
            "patch_sha256": digest(row["patch"].encode("utf-8")),
            "test_patch_sha256": digest(row["test_patch"].encode("utf-8")),
            "fail_to_pass_metadata_sha256": digest(row["FAIL_TO_PASS"].encode("utf-8")),
            "source_tree_blobs_verified": False,
            "historical_patch_is_independent_link_gold": False,
            "behavioral_observation_verified": False,
            "m20_independent_review_status": "pending",
            "held_out_evaluation_status": "not_eligible_until_baseline_freeze_and_contamination_audit",
        })
    if len(selected) != count:
        raise ValueError("Not enough complete SymPy instances")
    return {
        "schema": "m52-swebench-verified-pre-m20-intake-1",
        "external_dataset": "princeton-nlp/SWE-bench_Verified",
        "dataset_revision": DATASET_REV,
        "dataset_sha256": DATASET_SHA256,
        "human_screening_scope": "issue clarity and test appropriateness; not conformance labels",
        "project": REPO,
        "selected_count": len(selected),
        "candidate_cases": selected,
        "independent_link_labels": 0,
        "independent_behavioral_labels": 0,
        "adjudications": 0,
        "held_out_projects_scored": 0,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "coverage": None,
        "external_code_executed": False,
        "required_next": [
            "Freeze the entire requirement-to-code verifier and record its commit and settings.",
            "Check contamination: none of these issues or projects may have informed tuning.",
            "Verify complete first-party source tree blobs at each base commit before M20 symbol extraction.",
            "Construct blind M20 link queues without disclosing historical gold patches.",
            "Collect two independent link and revision-compatible behavioral reviews.",
            "Third reviewer adjudicates; only then evaluate on eligible held-out projects.",
        ],
    }


def write_manifest(manifest: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "INTERNAL_PROVENANCE_NOT_GOLD.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Do not expose the instance ID: it encodes the upstream fix PR number.
    # Historical PR URLs and patch metadata stay in the internal manifest only.
    # These are pre-M20 case intakes, not independently reviewed trace links.
    for reviewer in ("A", "B"):
        path = output / f"reviewer_{reviewer}_intake_NOT_M20_GOLD.jsonl"
        path.write_text("".join(json.dumps({
            "review_case_id": case["review_case_id"],
            "requirement_text": case["requirement_text"],
            "source_snapshot_url": case["source_snapshot_url"],
            "requirement_sha256": case["requirement_sha256"],
            "reviewer": reviewer,
            "link_label": None,
            "behavioral_label": None,
            "annotation_status": "pending_source_tree_and_m20_queue",
        }, sort_keys=True) + "\n" for case in manifest["candidate_cases"]),
            encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = build_manifest(verify_dataset(download(DATASET_URL)))
    write_manifest(manifest, args.out_dir)
    print(json.dumps({
        "project": REPO,
        "human_screened_candidate_cases": manifest["selected_count"],
        "independent_behavioral_labels": 0,
        "held_out_projects_scored": 0,
        "external_code_executed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
