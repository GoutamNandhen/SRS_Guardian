"""M33: replay pinned upstream EDC integration-test INTENT against conditional source models.

Upstream Java tests are read as static text, never executed. Their expected
counts are developer-authored test assertions, NOT independently adjudicated
requirements, runtime observations, or conformance gold.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

from backend.evaluation import m28_historical_pagination_regression as m28
from backend.evaluation import m30_static_pagination_witness as m30
from backend.evaluation.m20_annotation_queue import build_queue, write_outputs

SCHEMA = "m33-upstream-test-intent-replay-1"
TEST_NAME = "should_return_offers_subset_when_across_multiple_contract_definitions"
EXPECTED_RANGES = ((0, 12), (8, 14), (0, 999), (4, 888), (3, 20), (23, 25))


def parse_test_intent(java: str) -> tuple[tuple[int, int], tuple[tuple[int, int], ...]]:
    """Parse only the allowlisted parameterized test and its RangeProvider.

    Fail closed on changed fixture structure; this is not a general Java parser.
    """
    method = re.search(
        r"@ParameterizedTest\s+@ArgumentsSource\(RangeProvider\.class\)\s+"
        r"void should_return_offers_subset_when_across_multiple_contract_definitions"
        r"\(int from, int to\)\s*\{(.*?)\n    \}\s*\n\s*@Test",
        java, re.S,
    )
    if not method:
        raise m28.EvidenceError("Pinned parameterized integration test not found")
    body = method.group(1)
    first = re.search(r"var assets1 = range\((\d+), (\d+)\)", body)
    second = re.search(r"var assets2 = range\((\d+), (\d+)\)", body)
    required = (
        "var maximumRange = max(0, (assets1.size() + assets2.size()) - from);",
        "var requestedRange = to - from;",
        "hasSize(min(requestedRange, maximumRange))",
    )
    if not first or not second or any(marker not in body for marker in required):
        raise m28.EvidenceError("Upstream fixture or expected-size assertion changed")
    bounds = tuple(map(int, (*first.groups(), *second.groups())))
    if bounds != (0, 10, 10, 20):
        raise m28.EvidenceError("Unexpected upstream fixture bounds")
    provider = re.search(
        r"static class RangeProvider implements ArgumentsProvider\s*\{.*?"
        r"return Stream\.of\((.*?)\);", java, re.S,
    )
    if not provider:
        raise m28.EvidenceError("RangeProvider not found")
    ranges = tuple((int(a), int(b)) for a, b in
                   re.findall(r"Arguments\.of\((\d+), (\d+)\)", provider.group(1)))
    if ranges != EXPECTED_RANGES:
        raise m28.EvidenceError("RangeProvider cases differ from pinned upstream test")
    return (10, 10), ranges


def replay_test_intent(asset_counts: tuple[int, int],
                       ranges: tuple[tuple[int, int], ...]) -> list[dict]:
    """Conditional replay; matches to upstream assertion are NOT runtime results."""
    cases = []
    for i, (start, end) in enumerate(ranges, 1):
        if start < 0 or end <= start:
            raise m28.EvidenceError("Invalid upstream range")
        expected = min(end - start, max(0, sum(asset_counts) - start))
        pre = m30.simulate_before(asset_counts, start, end - start)
        post = m30.simulate_after(asset_counts, start, end - start)
        cases.append({
            "case_id": f"EDC_UPSTREAM_TEST_{i:02d}",
            "from": start, "to": end,
            "test_assertion_expected_not_gold": expected,
            "before_conditional_model": pre["model_returned_offers"],
            "after_conditional_model": post["model_returned_offers"],
            "before_model_matches_test_intent": pre["model_returned_offers"] == expected,
            "after_model_matches_test_intent": post["model_returned_offers"] == expected,
            "runtime_before": None, "runtime_after": None,
            "independent_labels": None,
        })
    return cases


def build(files: dict[str, dict[str, bytes]]) -> dict:
    # This verifies six pinned Git blobs, Apache-2.0 source licenses and
    # literal before/after Java source-expression anchors.
    binding = m30.source_binding(files)
    java = files["after"][m28.TEST].decode("utf-8")
    counts, ranges = parse_test_intent(java)
    cases = replay_test_intent(counts, ranges)
    if len(cases) != 6:
        raise m28.EvidenceError("Incomplete upstream test-intent replay")
    for case, (start, end) in zip(cases, ranges):
        line = m28._line(java, f"Arguments.of({start}, {end})")
        case["upstream_test_case_source"] = m28.source_url("after", m28.TEST, line)
    source_sha = hashlib.sha256(files["after"][m28.SOURCE] +
                                files["after"][m28.TEST]).hexdigest()
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": "EDC_UPSTREAM_TEST_INTENT_2494",
        "source_commit": m28.AFTER,
        "code_snapshot_sha256": source_sha,
        "requirements": [{
            "requirement_id": c["case_id"],
            "requirement_text": (
                f"Upstream integration test intent: with two 10-asset definitions, "
                f"Range({c['from']}, {c['to']}) should yield "
                f"{c['test_assertion_expected_not_gold']} offers."
            ),
        } for c in cases],
        "symbols": [
            {"symbol_id": "EDC_PAGINATION_IMPLEMENTATION", "source_path": m28.SOURCE,
             "qualified_name": "ContractOfferResolverImpl.queryContractOffers",
             "description": "Candidate implementation, link not independently reviewed"},
            {"symbol_id": "EDC_PAGINATION_TEST", "source_path": m28.TEST,
             "qualified_name": "ContractOfferResolverImplIntegrationTest.RangeProvider",
             "description": "Candidate integration test, link not independently reviewed"},
        ],
        "observed_links": [],
    }
    queue = build_queue(universe, seed="m33-edc-upstream-test-intent-1",
                        hard_per_requirement=2, random_per_requirement=0)
    if len(queue["queue"]) != 12:
        raise m28.EvidenceError("M20 review queue incomplete")
    report = {
        "schema": SCHEMA, "source_repository": m28.REPO,
        "source_license": "Apache-2.0 (pinned and hash-verified)",
        "before_commit": m28.BEFORE, "after_commit": m28.AFTER,
        "verified_static_file_revision_objects": 6,
        "test_intent_cases": len(cases),
        "before_model_disagrees_with_test_intent": sum(
            not c["before_model_matches_test_intent"] for c in cases),
        "after_model_agrees_with_test_intent": sum(
            c["after_model_matches_test_intent"] for c in cases),
        "m20_unlabeled_link_pairs": len(queue["queue"]),
        "behavior_revision_cases_per_reviewer": len(cases) * 2,
        "independent_adjudications": 0,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "conformance_coverage": None,
        "held_out_evaluation": False, "external_project_code_executed": False,
        "cases": cases, "source_expression_anchors": binding["anchors"],
        "interpretation": (
            "Six developer-authored post-fix integration-test inputs and assertions "
            "replayed through a first-party conditional Python abstraction. "
            "Model/assertion agreement is NOT Java execution, independent "
            "adjudication, conformance accuracy, or held-out evaluation."
        ),
    }
    return {"report": report, "queue": queue, "universe": universe}


def write(result: dict, out_dir: Path) -> None:
    internal, reviewers = out_dir / "internal", out_dir / "reviewers"
    internal.mkdir(parents=True, exist_ok=True)
    (internal / "test_intent_replay.json").write_text(
        json.dumps(result["report"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (internal / "candidate_universe.json").write_text(
        json.dumps(result["universe"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_outputs(result["queue"], reviewers)
    (internal / "m20_sampling_manifest.json").write_text(
        json.dumps(result["queue"]["manifest"], indent=2) + "\n", encoding="utf-8")
    (reviewers / "manifest.json").unlink()
    cases = result["report"]["cases"]
    (reviewers / "source_index.json").write_text(json.dumps({
        "repository": m28.REPO, "before_commit": m28.BEFORE,
        "after_commit": m28.AFTER,
        "test_cases": [{"case_id": c["case_id"],
                        "test_url": c["upstream_test_case_source"]} for c in cases],
        "source_before": m28.source_url("before", m28.SOURCE),
        "source_after": m28.source_url("after", m28.SOURCE),
        "note": "Developer-authored test intent is not independent behavioral ground truth.",
    }, indent=2) + "\n", encoding="utf-8")
    for reviewer in ("A", "B"):
        rows = [{
            "case_id": c["case_id"], "revision": rev, "reviewer": reviewer,
            "expected_from_upstream_test_not_gold": c["test_assertion_expected_not_gold"],
            "upstream_test_case_source": c["upstream_test_case_source"],
            "source_url": m28.source_url(rev, m28.SOURCE),
            "observed_offers": None, "approved_execution_evidence": None,
            "conformance_label": None, "violation_label": None,
            "reviewer_notes": None, "status": "pending",
        } for c in cases for rev in ("before", "after")]
        (reviewers / f"behavior_reviewer_{reviewer}.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8")
    (reviewers / "REVIEW_INSTRUCTIONS.md").write_text(
        "# M33 independent review\n\n"
        "Six upstream developer-authored test intentions are NOT independently "
        "adjudicated specifications. Each of two independent reviewers must inspect "
        "12 unlabeled M20 requirement-to-code/test pairs and 12 behavior/revision "
        "cases. Cite pinned lines and independently determine whether the test "
        "assertion reflects the intended requirement. Only label before/after "
        "behavior using approved version-matched runtime evidence or trustworthy "
        "archived execution logs. A separate adjudicator resolves disagreement. "
        "The internal conditional model predictions must remain blinded. "
        "Unsupported fields stay null. Do not execute third-party code here.\n",
        encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = build(m28.fetch_pinned())
    write(result, args.out_dir)
    report = result["report"]
    print(json.dumps({key: report[key] for key in (
        "test_intent_cases", "before_model_disagrees_with_test_intent",
        "after_model_agrees_with_test_intent", "m20_unlabeled_link_pairs",
        "behavior_revision_cases_per_reviewer", "independent_adjudications",
        "conformance_accuracy")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
