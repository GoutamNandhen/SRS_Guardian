"""M29: second independent real-project behavioral regression evidence (pip #12372).

Fetch only pinned, hash-checked static text. Build M20 blind link-review and
behavior-review packets. Neither upstream fixes nor tests are independent gold.
Never import, install, build, or execute the external pip source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

from backend.evaluation.m20_annotation_queue import build_queue, write_outputs

REPO = "pypa/pip"
BEFORE = "9685f64fe8c78e1e39cd9b32e5615f42e0a01f1c"
AFTER = "417ca92b439dba33d707b5da2493358863256bc3"
ISSUE = "https://github.com/pypa/pip/issues/12372"
FIX = "https://github.com/pypa/pip/pull/12392"
LICENSE = "LICENSE.txt"
SOURCE = "src/pip/_internal/resolution/resolvelib/factory.py"
TEST = "tests/functional/test_new_resolver.py"
FILES = {
    "before": {
        LICENSE: "8e7b65eaf628360e6f32f4140fcdd7ec7c2b7077",
        SOURCE: "38c199448a18a5dd6c2211384bf752eff819b5a8",
        TEST: "b5945edf89b0de0d8499972586380fa31391b32a",
    },
    "after": {
        LICENSE: "8e7b65eaf628360e6f32f4140fcdd7ec7c2b7077",
        SOURCE: "4adeb4309ce42ee0f6c428ae6cde11bde4a2e0d1",
        TEST: "3ff3f9425c202cb17a8a07eafca1971948d3bf72",
    },
}
COMMITS = {"before": BEFORE, "after": AFTER}
PROJECT = "PIP_LINK_EXTRAS_REGRESSION_12372"
MAX_BYTES = 1_000_000
# These are upstream claims or test intentions, NOT independently measured outcomes.
SCENARIOS = (
    {
        "case_id": "PIP_ISSUE_12372",
        "requirement_text": "Installing local gitlint and gitlint-core[trusted-deps] together should resolve the matching local dependency instead of reporting no matching distribution.",
        "origin": "upstream issue reporter expected behavior",
        "expected": "installation succeeds",
        "upstream_reported_before": "pip 23.3.1: no matching distribution; pip 23.2.1 reportedly works",
    },
    {
        "case_id": "PIP_DIRECT_LINK_EXTRA",
        "requirement_text": "Installing an explicit local pkg 1.0 wheel with extra ext and a compatible pkg==1 constraint should succeed.",
        "origin": "upstream merged regression test intent, not reporter reproduction",
        "expected": "pkg 1.0 installed",
        "upstream_reported_before": None,
    },
    {
        "case_id": "PIP_INDIRECT_LINK_EXTRA",
        "requirement_text": "Installing local pkg2 1.0 depending on pkg1[ext]==1.0 together with a local pkg1[ext] wheel should succeed.",
        "origin": "upstream merged regression test intent, not reporter reproduction",
        "expected": "pkg1 1.0 and pkg2 1.0 installed",
        "upstream_reported_before": None,
    },
)


class EvidenceError(ValueError):
    """Invalid or incomplete pinned external evidence."""


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(("blob %d\0" % len(raw)).encode("ascii") + raw).hexdigest()


def source_url(revision: str, path: str, line: int | None = None) -> str:
    url = f"https://github.com/{REPO}/blob/{COMMITS[revision]}/{path}"
    return url + (f"#L{line}" if line is not None else "")


def fetch_pinned() -> dict[str, dict[str, bytes]]:
    """Download only allowlisted text at immutable commits; verify each Git blob."""
    result: dict[str, dict[str, bytes]] = {}
    for revision, paths in FILES.items():
        result[revision] = {}
        for path, expected in paths.items():
            url = f"https://raw.githubusercontent.com/{REPO}/{COMMITS[revision]}/{path}"
            request = urllib.request.Request(url, headers={"User-Agent": "srs-guardian-m29-static-evidence"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200 or response.geturl() != url:
                    raise EvidenceError("Unexpected upstream status or redirect")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES or blob_sha(raw) != expected:
                raise EvidenceError(f"Git blob mismatch: {revision}/{path}")
            result[revision][path] = raw
    return result


def _line(text: str, marker: str) -> int:
    positions = [i for i, line in enumerate(text.splitlines(), 1) if marker in line]
    if len(positions) != 1:
        raise EvidenceError(f"Expected exactly one source anchor: {marker}")
    return positions[0]


def _snapshot_digest(paths: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        raw, name = paths[path], path.encode("utf-8")
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def build_evidence(files: dict[str, dict[str, bytes]]) -> dict:
    if set(files) != set(FILES):
        raise EvidenceError("Unexpected revision set")
    decoded, provenance = {}, {}
    for revision, paths in FILES.items():
        if set(files[revision]) != set(paths):
            raise EvidenceError("Missing or unexpected pinned path")
        decoded[revision], provenance[revision] = {}, {}
        for path, expected in paths.items():
            raw = files[revision][path]
            if len(raw) > MAX_BYTES or blob_sha(raw) != expected:
                raise EvidenceError(f"Git blob mismatch: {revision}/{path}")
            text = raw.decode("utf-8")
            decoded[revision][path] = text
            provenance[revision][path] = {
                "url": source_url(revision, path),
                "git_blob_sha1": expected,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "lines": len(text.splitlines()),
            }
        if "Permission is hereby granted, free of charge" not in decoded[revision][LICENSE]:
            raise EvidenceError("Pinned MIT license text missing")

    pre, post = decoded["before"], decoded["after"]
    if pre[SOURCE] == post[SOURCE] or pre[TEST] == post[TEST]:
        raise EvidenceError("Expected resolver and regression-test changes missing")
    if "def _make_base_candidate_from_link(" in pre[SOURCE]:
        raise EvidenceError("Expected pre-fix resolver distinction missing")
    if "def _make_base_candidate_from_link(" not in post[SOURCE] or "install_req_drop_extras" not in post[SOURCE]:
        raise EvidenceError("Expected post-fix resolver implementation missing")
    direct = "def test_new_resolver_constraint_on_link_with_extra("
    indirect = "def test_new_resolver_constraint_on_link_with_extra_indirect("
    if direct in pre[TEST] or indirect in pre[TEST] or direct not in post[TEST] or indirect not in post[TEST]:
        raise EvidenceError("Expected new regression tests not found")

    anchors = {
        "before_resolver": source_url("before", SOURCE, _line(pre[SOURCE], "def _make_candidate_from_link(")),
        "after_resolver": source_url("after", SOURCE, _line(post[SOURCE], "def _make_base_candidate_from_link(")),
        "after_direct_test": source_url("after", TEST, _line(post[TEST], direct)),
        "after_indirect_test": source_url("after", TEST, _line(post[TEST], indirect)),
    }
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT,
        "source_commit": AFTER,
        "code_snapshot_sha256": _snapshot_digest({path: files["after"][path] for path in (SOURCE, TEST)}),
        "requirements": [
            {"requirement_id": s["case_id"], "requirement_text": s["requirement_text"]}
            for s in SCENARIOS
        ],
        "symbols": [
            {
                "symbol_id": "PIP_RESOLVER_FACTORY",
                "source_path": SOURCE,
                "qualified_name": "Factory._make_requirements_from_install_req",
                "description": "Resolver implementation of link candidates and extras; linkage unverified",
            },
            {
                "symbol_id": "PIP_RESOLVER_FUNCTIONAL_TESTS",
                "source_path": TEST,
                "qualified_name": "test_new_resolver_constraint_on_link_with_extra",
                "description": "Upstream functional tests for link and extras behavior; linkage unverified",
            },
        ],
        "observed_links": [],
    }
    queue = build_queue(universe, seed="m29-pip-12372-v1", hard_per_requirement=2, random_per_requirement=0)
    if len(queue["queue"]) != 6:
        raise EvidenceError("Incomplete M20 requirement-to-code universe")
    reviewer_index = {
        "schema": "m29-review-source-index-1",
        "repository": REPO,
        "license": "MIT (pinned LICENSE.txt; individual third-party dependency licenses not audited)",
        "revisions": COMMITS,
        "source_provenance": provenance,
        "source_anchors": anchors,
        "case_origins": {s["case_id"]: s["origin"] for s in SCENARIOS},
        "caution": "Upstream issue and merged tests are hypotheses/evidence, not independent verdicts. Do not execute external code.",
    }
    internal = {
        "schema": "m29-pip-historical-regression-evidence-1",
        "issue": ISSUE,
        "merged_upstream_fix": FIX,
        "before_commit": BEFORE,
        "after_merge_commit": AFTER,
        "static_file_revision_objects_verified": sum(map(len, FILES.values())),
        "distinct_git_blobs_verified": len({sha for paths in FILES.values() for sha in paths.values()}),
        "upstream_behavior_scenarios": len(SCENARIOS),
        "issue_reported_scenarios": 1,
        "post_fix_test_scenarios": 2,
        "m20_link_pairs_pending": len(queue["queue"]),
        "behavior_revision_cases_pending_per_reviewer": len(SCENARIOS) * len(COMMITS),
        "reporter_allegations_not_gold": [
            {"case_id": s["case_id"], "allegation": s["upstream_reported_before"]}
            for s in SCENARIOS if s["upstream_reported_before"] is not None
        ],
        "independently_adjudicated_links": 0,
        "independently_adjudicated_behavior_cases": 0,
        "external_code_executed": False,
        "representative_held_out": False,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "conformance_coverage": None,
        "limitations": [
            "Upstream issue concerns a gitlint local-install scenario; new tests use small synthetic wheel fixtures and are not exact reproductions.",
            "A merged fix and test source do not prove execution results on either pinned revision.",
            "The pinned source files do not constitute a complete runnable pip environment or dependency lock.",
            "Two independent link/behavior annotators and third-party adjudication remain required.",
            "A representative unseen-project benchmark with independently verified positive and negative outcomes is still missing.",
        ],
    }
    return {"queue": queue, "universe": universe, "reviewer_index": reviewer_index, "internal": internal}


def write_evidence(result: dict, out_dir: Path) -> None:
    reviewers, internal = out_dir / "reviewers", out_dir / "internal"
    write_outputs(result["queue"], reviewers)
    reviewers.joinpath("manifest.json").unlink()
    reviewers.joinpath("source_index.json").write_text(
        json.dumps(result["reviewer_index"], indent=2) + "\n", encoding="utf-8"
    )
    for reviewer in ("A", "B"):
        rows = [
            {
                "case_id": s["case_id"],
                "revision": revision,
                "reviewer": reviewer,
                "expected_behavior": s["expected"],
                "origin": s["origin"],
                "source_url": source_url(revision, SOURCE),
                "test_url": source_url(revision, TEST),
                "observed_behavior": None,
                "conformance_label": None,
                "violation_label": None,
                "approved_runtime_evidence": None,
                "reviewer_notes": None,
                "status": "pending",
            }
            for s in SCENARIOS for revision in ("before", "after")
        ]
        reviewers.joinpath(f"behavior_reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
        )
    reviewers.joinpath("REVIEW_INSTRUCTIONS.md").write_text(
        "# M29 independent pip regression review\n\n"
        "Two independent reviewers must inspect all six M20 requirement-to-code/test pairs, "
        "record linked/not-linked/uncertain and cite exact pinned source lines. "
        "Independently assess the three expected behaviors at both pinned revisions "
        "(six behavior cases per reviewer). The original reporter's alleged failure "
        "is withheld; the two added test cases are NOT the reporter's exact reproduction. "
        "Only enter observed behavior from approved, independently reproduced, "
        "version-compatible execution or trustworthy archived logs; never run upstream "
        "code in this evidence generator. A third person adjudicates disagreements. "
        "All unsupported outcomes remain null.\n",
        encoding="utf-8",
    )
    internal.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("internal", result["internal"]),
        ("candidate_universe", result["universe"]),
        ("m20_sampling_manifest", result["queue"]["manifest"]),
    ):
        internal.joinpath(name + ".json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = build_evidence(fetch_pinned())
    write_evidence(result, args.out_dir)
    print(json.dumps({k: result["internal"][k] for k in (
        "static_file_revision_objects_verified", "upstream_behavior_scenarios",
        "m20_link_pairs_pending", "behavior_revision_cases_pending_per_reviewer",
        "conformance_accuracy", "violation_precision", "violation_recall",
        "conformance_coverage",
    )}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
