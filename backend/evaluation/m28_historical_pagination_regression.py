"""M28: external historical pagination regression candidate, NOT adjudicated gold.

Static-only acquisition of two pinned EDC source revisions and their integration
tests. The public bug report supplies expected outcomes and alleged pre-fix
observations; neither those observations nor the patch are independent verdicts.
No external Java is built, imported, or executed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

from backend.evaluation.m20_annotation_queue import build_queue, write_outputs

REPO = "eclipse-edc/Connector"
BEFORE = "3d0bd14d62f2fc29762027e94c5f778c90991228"
AFTER = "bab97cccf4d61a3a380a1d70925b34f4cec1b401"
ISSUE = "https://github.com/eclipse-edc/Connector/issues/2493"
PATCH = "https://github.com/eclipse-edc/Connector/pull/2494"
SOURCE = "core/control-plane/contract-core/src/main/java/org/eclipse/edc/connector/contract/offer/ContractOfferResolverImpl.java"
TEST = "core/control-plane/contract-core/src/test/java/org/eclipse/edc/connector/contract/offer/ContractOfferResolverImplIntegrationTest.java"
LICENSE = "LICENSE"
FILES = {
    "before": {
        LICENSE: "2bb9ad240fa04c8cf706a4901c4807878e90c2dc",
        SOURCE: "60b1698d8556771a4913d01b6bfdeb87dd11f20f",
        TEST: "145e02b1dc6c386bb9acafb9871a9e915fd531cc",
    },
    "after": {
        LICENSE: "2bb9ad240fa04c8cf706a4901c4807878e90c2dc",
        SOURCE: "d2d21bfa5ff02f5f8f73f6b9325c604355f33d4a",
        TEST: "47c5ef30e9647dd8c26e0a56ef38b8b2605bb841",
    },
}
COMMITS = {"before": BEFORE, "after": AFTER}
PROJECT = "EDC_HISTORICAL_PAGINATION_2493"
MAX_BYTES = 2_000_000
SCENARIOS = (
    ("PAG_52_0", 0, 52, 52, 100),
    ("PAG_2_49", 49, 2, 2, 3),
)


class EvidenceError(ValueError):
    """Pinned upstream evidence is missing, tampered with, or inconsistent."""


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(("blob %d\0" % len(raw)).encode("ascii") + raw).hexdigest()


def source_url(revision: str, path: str, line: int | None = None) -> str:
    url = f"https://github.com/{REPO}/blob/{COMMITS[revision]}/{path}"
    return url + (f"#L{line}" if line is not None else "")


def fetch_pinned() -> dict[str, dict[str, bytes]]:
    """Only allowlisted raw text files at immutable commits, with blob verification."""
    result: dict[str, dict[str, bytes]] = {}
    for revision, paths in FILES.items():
        result[revision] = {}
        for path, expected in paths.items():
            url = f"https://raw.githubusercontent.com/{REPO}/{COMMITS[revision]}/{path}"
            request = urllib.request.Request(url, headers={"User-Agent": "srs-guardian-m28-static-evidence"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.geturl() != url or response.status != 200:
                    raise EvidenceError("Unexpected upstream redirect/status")
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


def _digest_sources(paths: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        name = path.encode("utf-8")
        raw = paths[path]
        digest.update(len(name).to_bytes(4, "big"))
        digest.update(name)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(raw)
    return digest.hexdigest()


def build_evidence(files: dict[str, dict[str, bytes]]) -> dict:
    if set(files) != set(FILES):
        raise EvidenceError("Unexpected revision set")
    decoded: dict[str, dict[str, str]] = {}
    provenance: dict[str, dict] = {}
    for revision, paths in FILES.items():
        if set(files[revision]) != set(paths):
            raise EvidenceError("Missing/unexpected pinned path")
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
        if "Apache License" not in decoded[revision][LICENSE][:128]:
            raise EvidenceError("Apache-2.0 license missing")
        for path in (SOURCE, TEST):
            if "SPDX-License-Identifier: Apache-2.0" not in decoded[revision][path]:
                raise EvidenceError("Source SPDX license missing")

    pre, post = decoded["before"], decoded["after"]
    if pre[SOURCE] == post[SOURCE] or pre[TEST] == post[TEST]:
        raise EvidenceError("No source-and-test change between pinned revisions")
    if "dynamicLimit" in pre[SOURCE] or "dynamicLimit" not in post[SOURCE]:
        raise EvidenceError("Expected static code change missing")
    if "should_return_offers_subset_when_across_multiple_contract_definitions" in pre[TEST]:
        raise EvidenceError("Expected pre-fix integration-test distinction missing")
    if "should_return_offers_subset_when_across_multiple_contract_definitions" not in post[TEST]:
        raise EvidenceError("Expected post-fix integration test missing")

    anchors = {
        "before_source": source_url("before", SOURCE, _line(pre[SOURCE], "queryContractOffers(ContractOfferQuery query)")),
        "after_source": source_url("after", SOURCE, _line(post[SOURCE], "dynamicLimit =")),
        "after_test": source_url("after", TEST, _line(post[TEST], "should_return_offers_subset_when_across_multiple_contract_definitions(")),
    }
    requirements = [
        {
            "requirement_id": case_id,
            "requirement_text": (
                f"With two contract definitions selecting 50 assets each, "
                f"catalog request offset={offset}, limit={limit} should return "
                f"{expected} contract offers (reporter-stated expected behavior)."
            ),
        }
        for case_id, offset, limit, expected, _ in SCENARIOS
    ]
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT,
        "source_commit": AFTER,
        "code_snapshot_sha256": _digest_sources({p: files["after"][p] for p in (SOURCE, TEST)}),
        "requirements": requirements,
        "symbols": [
            {"symbol_id": "EDC_OFFER_RESOLVER", "source_path": SOURCE,
             "qualified_name": "ContractOfferResolverImpl.queryContractOffers",
             "description": "Catalog offer pagination implementation; link unverified"},
            {"symbol_id": "EDC_OFFER_INTEGRATION_TEST", "source_path": TEST,
             "qualified_name": "ContractOfferResolverImplIntegrationTest",
             "description": "Historical pagination integration test; link unverified"},
        ],
        "observed_links": [],
    }
    queue = build_queue(universe, seed="m28-historical-pagination-2493-v1",
                        hard_per_requirement=2, random_per_requirement=0)
    if len(queue["queue"]) != 4:
        raise EvidenceError("Incomplete M20 review universe")
    reviewer_index = {
        "schema": "m28-review-source-index-1",
        "source_repository": REPO,
        "revisions": {"before": BEFORE, "after": AFTER},
        "source_provenance": provenance,
        "source_anchors": anchors,
        "expected_behavior_origin": "Public upstream issue, not an independently validated specification",
        "caution": "The issue describes an alleged bug and the PR describes a proposed fix; neither is independently adjudicated conformance evidence. Do not execute upstream Java.",
    }
    internal = {
        "schema": "m28-historical-regression-evidence-1",
        "issue": ISSUE,
        "merged_upstream_pr": PATCH,
        "before_commit": BEFORE,
        "after_merge_commit": AFTER,
        "static_file_revision_objects_verified": sum(map(len, FILES.values())),
        "distinct_git_blobs_verified": len({v for paths in FILES.values() for v in paths.values()}),
        "historical_bug_report_scenarios": len(SCENARIOS),
        "m20_link_pairs_pending": len(queue["queue"]),
        "behavior_revision_cases_pending": len(SCENARIOS) * len(COMMITS),
        "reporter_alleged_before_observations_not_gold": [
            {"case_id": case_id, "expected": expected, "reported_observed_before": reported}
            for case_id, _, _, expected, reported in SCENARIOS
        ],
        "independent_reviewed_links": 0,
        "independent_reviewed_behavior_cases": 0,
        "external_code_executed": False,
        "representative_held_out": False,
        "conformance_accuracy": None,
        "violation_precision": None,
        "violation_recall": None,
        "conformance_coverage": None,
        "limitations": [
            "The 2023 bug report concerns historical EDC contract-offer offset/limit behavior, NOT DSP 2025-1 Link-header conformance.",
            "A reported before/after fix is a candidate regression, not independently measured negative/positive ground truth.",
            "The added integration test uses a different asset-count setup than the reported 100-asset scenarios.",
            "The selected source and tests are not a full executable deployment; no upstream Java was run.",
            "Two independent reviewers must assess links and reproduce both cases at each revision with approved, version-compatible runtime evidence.",
            "A separate unseen-project test set with adjudicated conforming and violating cases is required for research accuracy.",
        ],
    }
    return {"queue": queue, "reviewer_index": reviewer_index, "internal": internal,
            "universe": universe}


def write_evidence(result: dict, out_dir: Path) -> None:
    reviewers, internal = out_dir / "reviewers", out_dir / "internal"
    write_outputs(result["queue"], reviewers)
    # M20 sampling origins must not be in the reviewer-only packet.
    reviewers.joinpath("manifest.json").unlink()
    reviewers.joinpath("source_index.json").write_text(
        json.dumps(result["reviewer_index"], indent=2) + "\n", encoding="utf-8")
    for reviewer in ("A", "B"):
        rows = [
            {
                "case_id": case_id, "revision": revision, "reviewer": reviewer,
                "offset": offset, "limit": limit, "expected_offers": expected,
                "source_url": source_url(revision, SOURCE),
                "test_url": source_url(revision, TEST),
                "observed_offers": None, "conformance_label": None,
                "violation_label": None, "approved_runtime_evidence": None,
                "independent_reviewer_notes": None, "status": "pending",
            }
            for case_id, offset, limit, expected, _ in SCENARIOS
            for revision in ("before", "after")
        ]
        reviewers.joinpath(f"behavior_reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    reviewers.joinpath("REVIEW_INSTRUCTIONS.md").write_text(
        "# M28 independent historical-regression review\n\n"
        "Two independent reviewers: examine four M20 requirement-to-source/test pairs and "
        "record linked/not-linked/uncertain with exact source-line citations. "
        "Separately review four behavior/revision cases each. "
        "The reported issue observations are withheld from this packet; do not assume "
        "the historical PR establishes conformance. Only record an observed offer count "
        "after approved, version-compatible independent execution or trusted archived "
        "execution evidence. A third reviewer must adjudicate disagreements. "
        "Keep every unsupported label null. No external code is executed by this workflow.\n",
        encoding="utf-8")
    internal.mkdir(parents=True, exist_ok=True)
    for name, data in (
        ("internal", result["internal"]),
        ("candidate_universe", result["universe"]),
        ("m20_sampling_manifest", result["queue"]["manifest"]),
    ):
        internal.joinpath(name + ".json").write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = build_evidence(fetch_pinned())
    write_evidence(result, args.out_dir)
    print(json.dumps({key: result["internal"][key] for key in (
        "static_file_revision_objects_verified", "historical_bug_report_scenarios",
        "m20_link_pairs_pending", "behavior_revision_cases_pending",
        "conformance_accuracy", "violation_precision", "violation_recall",
        "conformance_coverage")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
