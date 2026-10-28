"""Synthetic first-party workflow tests; NEVER real reviewer evidence."""
import json
from pathlib import Path
import re

import pytest

from backend.evaluation import m39_three_project_adjudicator_workbench as m39


def seed(root: Path):
    for project, (nlinks, nbehavior) in m39.PROJECTS.items():
        folder = root / project / "reviewers"
        folder.mkdir(parents=True)
        for reviewer in ("A", "B"):
            links = [{
                "case_id": f"L{i}", "reviewer": f"reviewer_{reviewer}",
                "requirement_id": f"R{i}", "source_path": "source.py",
                "link_label": None, "evidence_notes": None,
                "annotation_status": "pending",
            } for i in range(nlinks)]
            behavior = [{
                "case_id": f"B{i//2}", "revision": "before" if i % 2 == 0 else "after",
                "reviewer": reviewer, "source_url": "https://github.com/example/pinned",
                "conformance_label": None, "violation_label": None,
                "observed_behavior": None, "approved_runtime_evidence": None,
                "reviewer_notes": None, "status": "pending",
            } for i in range(nbehavior)]
            for filename, rows in ((f"reviewer_{reviewer}.jsonl", links),
                                   (f"behavior_reviewer_{reviewer}.jsonl", behavior)):
                (folder / filename).write_text(
                    "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def edit(path, fn):
    rows = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
    fn(rows[0])
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_three_project_workbench_is_pending_and_unscored(tmp_path):
    seed(tmp_path / "reviews")
    out = tmp_path / "output"
    manifest = m39.generate(tmp_path / "reviews", out)
    assert manifest["projects"] == 3
    assert manifest["tasks"] == 30
    assert manifest["cases_per_project"] == {"edc": 8, "pip": 12, "werkzeug": 10}
    assert manifest["comparison_counts"]["pending_or_incomplete"] == 30
    assert manifest["independent_adjudications"] == 0
    assert all(x is None for x in manifest["metrics"].values())
    assert not manifest["external_project_code_executed"]
    tasks = [json.loads(s) for s in (out / "adjudication_queue.jsonl").read_text().splitlines()]
    assert len(tasks) == 30
    assert all(t["adjudicated_label"] is None and
               t["adjudication_status"] == "pending" for t in tasks)
    html = (out / "adjudicator_workbench.html").read_text()
    match = re.search(r'<script type="application/json" id="seed">(.*?)</script>', html, re.S)
    assert match
    assert len(json.loads(match.group(1))) == 30
    assert "Reviewer agreement never creates a gold label" in html


def test_evidence_backed_agreement_is_still_not_adjudication(tmp_path):
    seed(tmp_path / "reviews")
    for reviewer in ("A", "B"):
        edit(tmp_path / "reviews" / "werkzeug" / "reviewers" /
             f"reviewer_{reviewer}.jsonl",
             lambda row: row.update(link_label="linked", evidence_notes="pinned source line 42",
                                    annotation_status="reviewed"))
    manifest = m39.generate(tmp_path / "reviews", tmp_path / "output")
    assert manifest["comparison_counts"]["reviewer_agreement"] == 1
    assert manifest["comparison_counts"]["pending_or_incomplete"] == 29
    assert manifest["independent_adjudications"] == 0


def test_werkzeug_immutable_case_tampering_rejected(tmp_path):
    seed(tmp_path / "reviews")
    edit(tmp_path / "reviews" / "werkzeug" / "reviewers" / "reviewer_B.jsonl",
         lambda row: row.update(source_path="changed.py"))
    with pytest.raises(ValueError, match="Immutable evidence"):
        m39.generate(tmp_path / "reviews", tmp_path / "output")
    assert not (tmp_path / "output").exists()


def test_review_text_is_inert_in_html_payload(tmp_path):
    seed(tmp_path / "reviews")
    edit(tmp_path / "reviews" / "werkzeug" / "reviewers" / "reviewer_A.jsonl",
         lambda row: row.update(evidence_notes="</script><script>alert(1)</script>"))
    m39.generate(tmp_path / "reviews", tmp_path / "output")
    html = (tmp_path / "output" / "adjudicator_workbench.html").read_text()
    assert "</script><script>alert(1)</script>" not in html
    assert "\\u003c/script\\u003e" in html


def test_output_directory_cannot_mix_runs(tmp_path):
    seed(tmp_path / "reviews")
    out = tmp_path / "output"
    out.mkdir()
    (out / "old.txt").write_text("old")
    with pytest.raises(ValueError, match="empty"):
        m39.generate(tmp_path / "reviews", out)
