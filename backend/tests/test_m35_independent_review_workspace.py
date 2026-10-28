"""M35 offline reviewer handoff tests; synthetic packets, no external code."""
import json
from pathlib import Path

import pytest

from backend.evaluation.m35_independent_review_workspace import (
    EXPECTED, build_workspaces, read_packet,
)


def packet(root: Path, project: str, reviewer: str):
    folder = root / project / "reviewers"
    folder.mkdir(parents=True, exist_ok=True)
    link_count, behavior_count = EXPECTED[project]
    links = [{
        "case_id": f"PAIR-{i}", "reviewer": f"reviewer_{reviewer}",
        "requirement_id": f"R{i}", "requirement_text": "Requirement text",
        "symbol_id": f"S{i}", "source_path": "source.py", "qualified_name": "f",
        "description": "Pinned source", "link_label": None,
        "evidence_notes": None, "annotation_status": "pending",
    } for i in range(link_count)]
    behaviors = [{
        "case_id": f"CASE-{i // 2}", "revision": ("before", "after")[i % 2],
        "reviewer": reviewer, "expected_behavior": "expected",
        "source_url": "https://github.com/pypa/pip",
        "observed_behavior": None, "conformance_label": None,
        "violation_label": None, "approved_runtime_evidence": None,
        "reviewer_notes": None, "status": "pending",
    } for i in range(behavior_count)]
    for name, rows in ((f"reviewer_{reviewer}.jsonl", links),
                       (f"behavior_reviewer_{reviewer}.jsonl", behaviors)):
        (folder / name).write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_four_offline_workspaces_remain_blinded_and_unlabeled(tmp_path):
    for project in EXPECTED:
        for reviewer in ("A", "B"):
            packet(tmp_path, project, reviewer)
    result = build_workspaces(tmp_path)
    assert result["projects"] == 2
    assert len(result["workspaces"]) == 4
    assert result["independent_adjudications"] == 0
    assert all(value is None for value in result["metrics"].values())
    for entry in result["workspaces"]:
        html = (tmp_path / entry["workspace"]).read_text()
        assert "Export link JSONL" in html
        assert "Export behavior JSONL" in html
        assert "Restore your own previously exported JSONL" in html
        assert "application/json" in html
        assert "independent execution/log" in html
        assert "static_model_before" not in html
        assert "sampling_provenance" not in html
        assert '"conformance_label": null' in html
        assert '"link_label": null' in html
        assert f'"reviewer": "{entry["reviewer"]}"' in html
        assert f'"reviewer": "reviewer_{entry["reviewer"]}"' in html
        other = "B" if entry["reviewer"] == "A" else "A"
        assert f'"reviewer": "reviewer_{other}"' not in html
        assert f'"reviewer": "{other}"' not in html


def test_fail_closed_on_prelabeled_or_cross_reviewer_rows(tmp_path):
    packet(tmp_path, "edc", "A")
    path = tmp_path / "edc" / "reviewers" / "reviewer_A.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[0]["link_label"] = "linked"
    path.write_text("".join(json.dumps(x) + "\n" for x in rows))
    with pytest.raises(ValueError, match="pre-labeled"):
        read_packet(path, 4, "A", behavior=False)
    rows[0]["link_label"] = None
    rows[0]["reviewer"] = "reviewer_B"
    path.write_text("".join(json.dumps(x) + "\n" for x in rows))
    with pytest.raises(ValueError, match="contamination"):
        read_packet(path, 4, "A", behavior=False)


def test_fail_closed_on_duplicate_behavior_case(tmp_path):
    packet(tmp_path, "pip", "B")
    path = tmp_path / "pip" / "reviewers" / "behavior_reviewer_B.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    rows[1] = dict(rows[0])
    path.write_text("".join(json.dumps(x) + "\n" for x in rows))
    with pytest.raises(ValueError, match="Duplicate"):
        read_packet(path, 6, "B", behavior=True)
