"""M44: a fourth real upstream issue-to-code review candidate (NOT GOLD).

Use the existing M20 blinded queue and M35 offline reviewer UI. Fetch exactly
pinned Apache-2.0 Requests source/license/test objects as inert text; no
third-party project code is imported, installed, or executed. The historical
issue and merged patch are not independent behavioral ground truth.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

from backend.evaluation import m20_annotation_queue as m20
from backend.evaluation import m35_independent_review_workspace as m35
from backend.evaluation import m37_werkzeug_holdout as m37

REPO = "psf/requests"
ISSUE = "https://github.com/psf/requests/issues/7432"
FIX = "https://github.com/psf/requests/pull/7433"
REVISIONS = {
    "before": "0b401c76b6e80a4eecf3c690085b2553f6e261ca",
    "after": "6404f345e562d962abe6700a1c357ec1e7e18232",
}
LICENSE = "LICENSE"
SOURCE = "src/requests/models.py"
TEST = "tests/test_requests.py"
BLOBS = {
    "before": {
        LICENSE: "67db8588217f266eb561f75fae738656325deac9",
        SOURCE: "4142f2a4bbf39820b46b414a15af805a34b1a013",
        TEST: "09cd4a388a760ad7d757afe0b9560e486ea4b7c9",
    },
    "after": {
        LICENSE: "67db8588217f266eb561f75fae738656325deac9",
        SOURCE: "57e114866da042a866dced7a2f55a8a7da597878",
        TEST: "571535fe7998dcc7a747266f4461f96fcea3c2d3",
    },
}
PROJECT = "REQUESTS_STREAM_REDIRECT_7432"
MAX_BYTES = 2_000_000
REQUIREMENT = (
    "A file-like upload wrapper that delegates __iter__, read, tell, and seek "
    "through __getattr__ should retain its request body when following a "
    "307 redirect, rather than sending an empty or consumed body."
)
METRICS = ("conformance_accuracy", "violation_precision", "violation_recall",
           "conformance_coverage")


class EvidenceError(ValueError):
    """Immutable source or research provenance is invalid."""


def url(revision: str, path: str, line: int | None = None) -> str:
    if revision not in REVISIONS or path not in BLOBS[revision]:
        raise EvidenceError("Unpinned revision or source path")
    result = f"https://github.com/{REPO}/blob/{REVISIONS[revision]}/{path}"
    return result + (f"#L{line}" if line else "")


def fetch_pinned() -> dict[str, dict[str, bytes]]:
    files = {}
    for revision, paths in BLOBS.items():
        files[revision] = {}
        for path, expected in paths.items():
            address = f"https://raw.githubusercontent.com/{REPO}/{REVISIONS[revision]}/{path}"
            request = urllib.request.Request(
                address, headers={"User-Agent": "srs-guardian-m44-pinned-source"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200 or response.geturl() != address:
                    raise EvidenceError("Unexpected upstream HTTP status or redirect")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES or m37.blob_sha(raw) != expected:
                raise EvidenceError(f"Git blob mismatch: {revision}/{path}")
            files[revision][path] = raw
    return files


def _snapshot_digest(files: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(files):
        raw = files[path]
        h.update(len(path.encode()).to_bytes(4, "big"))
        h.update(path.encode())
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return h.hexdigest()


def build_evidence(files: dict[str, dict[str, bytes]]) -> dict:
    if set(files) != set(REVISIONS):
        raise EvidenceError("Missing or unexpected revision")
    texts, provenance = {}, {}
    for revision, expected in BLOBS.items():
        if set(files[revision]) != set(expected):
            raise EvidenceError("Missing or unexpected pinned file")
        texts[revision], provenance[revision] = {}, {}
        for path, sha in expected.items():
            raw = files[revision][path]
            if len(raw) > MAX_BYTES or m37.blob_sha(raw) != sha:
                raise EvidenceError(f"Git blob mismatch: {revision}/{path}")
            text = raw.decode("utf-8")
            texts[revision][path] = text
            provenance[revision][path] = {
                "url": url(revision, path),
                "git_blob_sha1": sha,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "lines": len(text.splitlines()),
            }
        license_text = texts[revision][LICENSE]
        if not all(x in license_text for x in (
            "Apache License", "Version 2.0, January 2004",
            "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION")):
            raise EvidenceError("Pinned Apache-2.0 license was not verified")

    pre, post = texts["before"], texts["after"]
    old = "if isinstance(data, Iterable) and not isinstance("
    new = 'is_iterable = isinstance(data, Iterable) or hasattr(data, "__iter__")'
    regression = "def test_getattr_proxy_stream_follows_redirect"
    if old not in pre[SOURCE] or new in pre[SOURCE]:
        raise EvidenceError("Before source does not match historical patch")
    if new not in post[SOURCE] or old in post[SOURCE]:
        raise EvidenceError("After source does not match historical patch")
    if regression in pre[TEST] or regression not in post[TEST]:
        raise EvidenceError("Regression-test addition not verified")
    anchors = {
        "before_source": url("before", SOURCE, m37.anchor(pre[SOURCE], old)),
        "after_source": url("after", SOURCE, m37.anchor(post[SOURCE], new)),
        "after_test": url("after", TEST, m37.anchor(post[TEST], regression)),
    }

    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT,
        "source_commit": REVISIONS["after"],
        "code_snapshot_sha256": _snapshot_digest(files["after"]),
        "requirements": [{"requirement_id": "REQ_7432", "requirement_text": REQUIREMENT}],
        "symbols": [
            {"symbol_id": "REQUESTS_PREPARE_BODY", "source_path": SOURCE,
             "qualified_name": "PreparedRequest.prepare_body",
             "description": "Upload body stream detection and rewind position capture"},
            {"symbol_id": "REQUESTS_REDIRECT_TEST", "source_path": TEST,
             "qualified_name": "TestRequests.test_getattr_proxy_stream_follows_redirect",
             "description": "Upstream regression test, not a behavioral observation"},
        ],
        "observed_links": [],
    }
    queue = m20.build_queue(
        universe, seed="m44-requests-7432-review-v1",
        hard_per_requirement=2, random_per_requirement=0)
    if len(queue["queue"]) != 2:
        raise EvidenceError("Unexpected M20 candidate count")
    manifest = {
        "schema": "m44-requests-independent-review-candidate-1",
        "project": PROJECT, "upstream_repository": REPO,
        "issue": ISSUE, "merged_fix": FIX, "revisions": REVISIONS,
        "license": "Apache-2.0 (verified at both pinned revisions)",
        "file_revision_objects_hash_verified": 6,
        "source_provenance": provenance, "source_anchors": anchors,
        "m20_pairs_per_reviewer": 2, "behavior_revisions_per_reviewer": 2,
        "independent_reviewers_completed": 0, "independent_adjudications": 0,
        "approved_runtime_observations": 0, "held_out_candidate_only": True,
        "held_out_scored": False, "external_project_code_executed": False,
        "metrics": {name: None for name in METRICS},
        "research_status": (
            "Externally authored issue, immutable source and merged upstream test; "
            "NOT independent ground truth. Do not tune on this candidate if "
            "reserving it for a future held-out evaluation."
        ),
        "review_required": (
            "Two independent reviewers each assess two M20 candidate links "
            "against exact pinned source lines, and one behavior case at each "
            "revision. For behavioral verdicts obtain approved, independent "
            "revision-compatible runtime observations including fixture, "
            "Python and dependency versions, request/redirect inputs, output "
            "or exception, and reproducible logs. A third person adjudicates "
            "disagreements. Historical reporter claims and upstream tests "
            "are NOT independent execution evidence."
        ),
    }
    return {"queue": queue, "manifest": manifest}


def write_evidence(evidence: dict, files: dict[str, dict[str, bytes]],
                   out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()):
        raise EvidenceError("Output directory must be empty")
    internal = out_dir / "internal"
    m20.write_outputs(evidence["queue"], internal / "m20")
    (internal / "evidence_manifest.json").write_text(
        json.dumps(evidence["manifest"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    for reviewer in m35.REVIEWERS:
        destination = out_dir / f"reviewer_{reviewer}"
        destination.mkdir(parents=True)
        packet = internal / "m20" / f"reviewer_{reviewer}.jsonl"
        shutil.copyfile(packet, destination / "link_seed.jsonl")
        behavior_rows = []
        for revision in REVISIONS:
            behavior_rows.append({
                "case_id": "REQUESTS_7432_REDIRECT", "revision": revision,
                "reviewer": reviewer, "expected_behavior": REQUIREMENT,
                "source_url": evidence["manifest"]["source_anchors"][f"{revision}_source"],
                "test_url": evidence["manifest"]["source_anchors"]["after_test"],
                "test_scope_note": "Merged upstream test is not an independent runtime result.",
                "observed_behavior": None, "conformance_label": None,
                "violation_label": None, "approved_runtime_evidence": None,
                "reviewer_notes": None, "status": "pending",
            })
        (destination / "behavior_seed.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in behavior_rows),
            encoding="utf-8")
        links = m35.read_packet(destination / "link_seed.jsonl", 2, reviewer, behavior=False)
        behaviors = m35.read_packet(destination / "behavior_seed.jsonl", 2, reviewer, behavior=True)
        payload = json.dumps({"project": "requests", "reviewer": reviewer,
                              "links": links, "behaviors": behaviors})
        payload = (payload.replace("<", "\\u003c").replace(">", "\\u003e")
                   .replace("&", "\\u0026"))
        (destination / "workspace.html").write_text(
            m35.PAGE.replace("__PAYLOAD__", payload), encoding="utf-8")
        for revision, paths in files.items():
            for path, raw in paths.items():
                location = destination / "source" / revision / (path + ".txt")
                location.parent.mkdir(parents=True, exist_ok=True)
                location.write_bytes(raw)
        (destination / "REVIEW_INSTRUCTIONS.md").write_text(
            "# Requests 7432 independent review (NOT GOLD)\n\n"
            "Use workspace.html locally; read source/ as inert text. "
            "Do not import or run upstream project code in this workflow. "
            "Do not share the internal provenance manifest or other reviewer's work. "
            "Independently assess both M20 candidate links and both revision-specific "
            "behaviors. Source anchors and upstream regression tests are leads, "
            "not ground truth. For a behavioral label cite separately approved "
            "runtime evidence with exact commit, fixture, environment, logs, "
            "and observed output. Leave unsupported cases pending. "
            "Export both JSONL files; a third human adjudicator is required.\n",
            encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    files = fetch_pinned()
    evidence = build_evidence(files)
    write_evidence(evidence, files, args.out_dir)
    print(json.dumps({
        "project": PROJECT, "verified_objects": 6,
        "links_per_reviewer": 2, "behaviors_per_reviewer": 2,
        "independent_adjudications": 0, "metrics": evidence["manifest"]["metrics"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
