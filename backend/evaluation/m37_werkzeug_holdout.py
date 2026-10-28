"""M37: reserve a third real external regression for independent held-out review.

Only fetch allowlisted immutable upstream source snapshots; never import or run them.
The issue and merged PR are historical claims, NOT adjudicated conformance labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

from backend.evaluation.m20_annotation_queue import build_queue, write_outputs

REPO = "pallets/werkzeug"
BEFORE = "446afc9dc21b786531b1171d14ca31adf4f084a3"
AFTER = "f488ea16cd2f9b81cf4602c257e7963421b40156"
ISSUE = "https://github.com/pallets/werkzeug/issues/2422"
FIX = "https://github.com/pallets/werkzeug/pull/2442"
LICENSE = "LICENSE.rst"
PARSER = "src/werkzeug/http.py"
CALLER = "src/werkzeug/sansio/multipart.py"
TEST = "tests/test_http.py"
PROJECT = "WERKZEUG_HISTORICAL_FILENAME_2422"
FILES = {
    "before": {
        LICENSE: "c37cae49ec77ad6ebb25568c1605f1fee5313cfb",
        PARSER: "936990013ff1337d7dc95fdce09ab0e3fcb52c09",
        CALLER: "d8abeb35436da7531d7e57a3581f3e33cf92b1f2",
        TEST: "5936bfa59bc67193e6f5259645691afddd3b3e25",
    },
    "after": {
        LICENSE: "c37cae49ec77ad6ebb25568c1605f1fee5313cfb",
        PARSER: "3d0fba905e5200e0eb7e3dc532efdedbe381fffa",
        CALLER: "d8abeb35436da7531d7e57a3581f3e33cf92b1f2",
        TEST: "623114cb59787c65c4bec32778a9868a3b375577",
    },
}
REVISIONS = {"before": BEFORE, "after": AFTER}
MAX_BYTES = 2_000_000
SCENARIOS = (
    ("WERK_FILENAME_OPTION",
     'For the input something; fileName="File.ext", the parsed option name should be filename with value File.ext.',
     PARSER, "Unit test in the merged fix; not independently adjudicated."),
    ("WERK_MULTIPART_FILE",
     "For multipart parts using fileName instead of filename, the reporter expects file classification, not ordinary form fields.",
     CALLER, "Reporter allegation; the added unit test does NOT establish end-to-end multipart behavior."),
)
METRICS = ("conformance_accuracy", "violation_precision", "violation_recall", "conformance_coverage")


class EvidenceError(ValueError):
    """Pinned upstream bytes or expected static anchors are inconsistent."""


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(("blob %d\0" % len(raw)).encode("ascii") + raw).hexdigest()


def url(revision: str, path: str, line: int | None = None) -> str:
    result = f"https://github.com/{REPO}/blob/{REVISIONS[revision]}/{path}"
    return result + (f"#L{line}" if line is not None else "")


def fetch_pinned() -> dict[str, dict[str, bytes]]:
    out: dict[str, dict[str, bytes]] = {}
    for revision, paths in FILES.items():
        out[revision] = {}
        for path, expected in paths.items():
            address = f"https://raw.githubusercontent.com/{REPO}/{REVISIONS[revision]}/{path}"
            request = urllib.request.Request(
                address, headers={"User-Agent": "srs-guardian-m37-static-provenance"})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200 or response.geturl() != address:
                    raise EvidenceError("Unexpected status or redirect")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES or blob_sha(raw) != expected:
                raise EvidenceError(f"Git blob mismatch: {revision}/{path}")
            out[revision][path] = raw
    return out


def anchor(text: str, marker: str) -> int:
    found = [i for i, line in enumerate(text.splitlines(), 1) if marker in line]
    if len(found) != 1:
        raise EvidenceError(f"Nonunique/missing static source anchor: {marker}")
    return found[0]


def digest_snapshot(paths: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(paths):
        name, raw = path.encode("utf-8"), paths[path]
        h.update(len(name).to_bytes(4, "big"))
        h.update(name)
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return h.hexdigest()


def build_evidence(files: dict[str, dict[str, bytes]]) -> dict:
    if set(files) != set(FILES):
        raise EvidenceError("Unexpected revision set")
    texts, provenance = {}, {}
    for revision, paths in FILES.items():
        if set(files[revision]) != set(paths):
            raise EvidenceError("Missing/unexpected pinned paths")
        texts[revision], provenance[revision] = {}, {}
        for path, expected in paths.items():
            raw = files[revision][path]
            if len(raw) > MAX_BYTES or blob_sha(raw) != expected:
                raise EvidenceError(f"Git blob mismatch: {revision}/{path}")
            decoded = raw.decode("utf-8")
            texts[revision][path] = decoded
            provenance[revision][path] = {
                "url": url(revision, path),
                "git_blob_sha1": expected,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "lines": len(decoded.splitlines()),
            }
        license_text = texts[revision][LICENSE]
        if not all(s in license_text for s in (
            "Redistribution and use in source and binary forms",
            "Neither the name of the copyright holder",
            "THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS")):
            raise EvidenceError("Pinned BSD-3-Clause license text not verified")
    pre, post = texts["before"], texts["after"]
    if pre[PARSER] == post[PARSER] or pre[TEST] == post[TEST]:
        raise EvidenceError("Expected implementation/test change missing")
    if pre[CALLER] != post[CALLER]:
        raise EvidenceError("Expected unchanged multipart caller changed")
    if "option = unquote_header_value(option).lower()" in pre[PARSER]:
        raise EvidenceError("Pre-fix parser already normalizes options")
    if "option = unquote_header_value(option).lower()" not in post[PARSER]:
        raise EvidenceError("Post-fix parser normalization missing")
    marker = "def test_parse_options_header_case_insensitive"
    if marker in pre[TEST] or marker not in post[TEST]:
        raise EvidenceError("Historical regression test distinction missing")
    if 'filename = extra.get("filename")' not in pre[CALLER]:
        raise EvidenceError("Multipart caller anchor missing")
    anchors = {
        "before_parser": url("before", PARSER, anchor(pre[PARSER], "option = unquote_header_value(option)")),
        "after_parser": url("after", PARSER, anchor(post[PARSER], "option = unquote_header_value(option).lower()")),
        "after_test": url("after", TEST, anchor(post[TEST], marker)),
        "multipart_caller": url("after", CALLER, anchor(post[CALLER], 'filename = extra.get("filename")')),
    }
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT,
        "source_commit": AFTER,
        "code_snapshot_sha256": digest_snapshot({
            path: files["after"][path] for path in (PARSER, CALLER, TEST)}),
        "requirements": [
            {"requirement_id": "WERK_REQ_OPTION",
             "requirement_text": "The Content-Disposition option name fileName must be matched case-insensitively as filename, preserving its value."},
            {"requirement_id": "WERK_REQ_MULTIPART",
             "requirement_text": "Multipart parts using the fileName attribute must be recognized as file parts rather than ordinary form fields."},
        ],
        "symbols": [
            {"symbol_id": "WERK_HTTP_PARSE", "source_path": PARSER,
             "qualified_name": "werkzeug.http.parse_options_header",
             "description": "Header parameter parsing implementation"},
            {"symbol_id": "WERK_MULTIPART_DECODER", "source_path": CALLER,
             "qualified_name": "werkzeug.sansio.multipart.MultipartDecoder",
             "description": "Multipart consumer of parsed filename parameter"},
            {"symbol_id": "WERK_HTTP_TEST", "source_path": TEST,
             "qualified_name": "TestHTTP.test_parse_options_header_case_insensitive",
             "description": "Post-fix upstream unit test for mixed-case option"},
        ],
        "observed_links": [],
    }
    queue = build_queue(universe, seed="m37-werkzeug-2422-reserved-v1",
                        hard_per_requirement=3, random_per_requirement=0)
    if len(queue["queue"]) != 6:
        raise EvidenceError("Unexpected M20 blinded pair count")
    manifest = {
        "schema": "m37-werkzeug-reserved-holdout-candidate-1",
        "project": PROJECT,
        "upstream_repository": REPO,
        "issue": ISSUE,
        "merged_fix": FIX,
        "revisions": REVISIONS,
        "license": "BSD-3-Clause (verified from pinned LICENSE.rst in both revisions)",
        "file_revision_objects_verified": 8,
        "source_provenance": provenance,
        "anchors": anchors,
        "review_cases": {"links_per_reviewer": 6, "behavior_revisions_per_reviewer": 4},
        "independent_reviewers_completed": 0,
        "independent_adjudications": 0,
        "held_out_candidate_only": True,
        "frozen_verifier_evaluation_completed": False,
        "external_project_code_executed": False,
        "metrics": {key: None for key in METRICS},
        "warning": "Source-grounded regression candidate, NOT gold. The historical report and merged patch are not independent runtime measurements. This project must remain unused for tuning; a frozen verifier and independent adjudication are required before held-out evaluation.",
        "next_blocker": "Two independent reviewers must assess 6 M20 trace pairs and 4 behavior/revision cases each, with approved version-compatible runtime evidence for parser and multipart outcomes. A separate adjudicator must resolve all verdicts.",
    }
    return {"queue": queue, "manifest": manifest, "scenarios": SCENARIOS, "anchors": anchors}


def write_evidence(evidence: dict, out_dir: Path) -> None:
    internal, reviewers = out_dir / "internal", out_dir / "reviewers"
    internal.mkdir(parents=True, exist_ok=True)
    reviewers.mkdir(parents=True, exist_ok=True)
    write_outputs(evidence["queue"], internal / "m20")
    (internal / "evidence_manifest.json").write_text(
        json.dumps(evidence["manifest"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    m20 = internal / "m20"
    shutil.copyfile(m20 / "blind_queue.jsonl", reviewers / "blind_queue.jsonl")
    for reviewer in ("A", "B"):
        shutil.copyfile(m20 / f"reviewer_{reviewer}.jsonl",
                        reviewers / f"reviewer_{reviewer}.jsonl")
        rows = []
        for case_id, expected, path, scope in evidence["scenarios"]:
            for revision in ("before", "after"):
                rows.append({
                    "case_id": case_id,
                    "revision": revision,
                    "reviewer": reviewer,
                    "expected_behavior": expected,
                    "expectation_origin": "Historical upstream issue #2422 and fix #2442, NOT independent gold",
                    "source_url": url(revision, path),
                    "test_url": url("after", TEST) if case_id == "WERK_FILENAME_OPTION" else None,
                    "test_scope_note": scope,
                    "observed_behavior": None,
                    "conformance_label": None,
                    "violation_label": None,
                    "approved_runtime_evidence": None,
                    "reviewer_notes": None,
                    "status": "pending",
                })
        (reviewers / f"behavior_reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    (reviewers / "REVIEW_INSTRUCTIONS.md").write_text(
        "# M37 independent review — Werkzeug historical filename regression\n\n"
        "This is a reserved third-project held-out CANDIDATE, not a scored benchmark. "
        "Each of two independent human reviewers must assess all 6 M20 link pairs, "
        "citing exact pinned source lines, and all 4 revision-specific behavioral cases. "
        "For each behavior, supply a reproducible, approved runtime log/artifact tied "
        "to the exact before/after revision, Python/dependency versions, input fixture, "
        "and observed output. The historical reporter's claims and post-fix unit test "
        "are not independent execution evidence. The multipart classification claim "
        "must be tested separately; the upstream unit test covers header parsing only. "
        "Do not share the internal manifest or selection origins with reviewers. "
        "Keep A/B submissions separate; a third adjudicator must document final "
        "decisions before any conformance metric is computed. "
        "Never execute untrusted code in the research automation.\n",
        encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    evidence = build_evidence(fetch_pinned())
    write_evidence(evidence, args.out_dir)
    print(json.dumps({
        "project": PROJECT,
        "verified_file_revision_objects": 8,
        "m20_pairs_per_reviewer": 6,
        "behavior_cases_per_reviewer": 4,
        "independent_adjudications": 0,
        "metrics": evidence["manifest"]["metrics"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
