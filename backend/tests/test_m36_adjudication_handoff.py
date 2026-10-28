"""Synthetic first-party tests: never interpret as research performance."""
import json
from pathlib import Path
import pytest
from backend.evaluation import m36_adjudication_handoff as m36


def seed(root: Path):
    for project, (nlinks, nbehavior) in m36.PROJECTS.items():
        folder = root / project / "reviewers"
        folder.mkdir(parents=True)
        for reviewer in ("A", "B"):
            links = [{"case_id": f"L{i}", "reviewer": f"reviewer_{reviewer}",
                      "requirement_id": f"R{i}", "source_path": "p.py",
                      "link_label": None, "evidence_notes": None,
                      "annotation_status": "pending"} for i in range(nlinks)]
            behaviors = [{"case_id": f"B{i//2}",
                          "revision": "before" if i % 2 == 0 else "after",
                          "reviewer": reviewer, "source_url": "https://github.com/example/pin",
                          "conformance_label": None, "violation_label": None,
                          "observed_behavior": None, "approved_runtime_evidence": None,
                          "reviewer_notes": None, "status": "pending"}
                         for i in range(nbehavior)]
            for name, rows in ((f"reviewer_{reviewer}.jsonl", links),
                               (f"behavior_reviewer_{reviewer}.jsonl", behaviors)):
                (folder / name).write_text("".join(json.dumps(r) + "\n" for r in rows))


def edit(path, update):
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    update(rows[0])
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_pending_unscored(tmp_path):
    seed(tmp_path)
    tasks, manifest = m36.reconcile(tmp_path)
    assert len(tasks) == 20
    assert manifest["comparison_counts"] == {
        "pending_or_incomplete": 20, "reviewer_agreement": 0, "reviewer_disagreement": 0}
    assert all(t["adjudicated_label"] is None for t in tasks)
    assert all(v is None for v in manifest["metrics"].values())
    m36.write_outputs(tasks, manifest, tmp_path / "output")
    assert len((tmp_path / "output/adjudication_queue.jsonl").read_text().splitlines()) == 20


def test_agreement_still_not_gold(tmp_path):
    seed(tmp_path)
    for r in ("A", "B"):
        edit(tmp_path / f"edc/reviewers/reviewer_{r}.jsonl",
             lambda row: row.update(link_label="linked", evidence_notes="source line 22",
                                    annotation_status="reviewed"))
    tasks, manifest = m36.reconcile(tmp_path)
    assert manifest["comparison_counts"]["reviewer_agreement"] == 1
    assert manifest["independent_adjudications"] == 0
    assert all(t["adjudicated_label"] is None for t in tasks)


def test_disagreement_not_gold(tmp_path):
    seed(tmp_path)
    for r, label in (("A", True), ("B", False)):
        edit(tmp_path / f"pip/reviewers/behavior_reviewer_{r}.jsonl",
             lambda row: row.update(conformance_label=label, violation_label=not label,
                                    observed_behavior="observed log",
                                    approved_runtime_evidence="approved log ID",
                                    reviewer_notes="pinned environment", status="reviewed"))
    tasks, manifest = m36.reconcile(tmp_path)
    assert manifest["comparison_counts"]["reviewer_disagreement"] == 1
    assert manifest["independent_adjudications"] == 0


def test_immutable_tampering_rejected(tmp_path):
    seed(tmp_path)
    edit(tmp_path / "edc/reviewers/reviewer_B.jsonl",
         lambda row: row.update(source_path="other.py"))
    with pytest.raises(ValueError, match="Immutable evidence"):
        m36.reconcile(tmp_path)


def test_missing_case_and_identity_rejected(tmp_path):
    seed(tmp_path)
    edit(tmp_path / "edc/reviewers/reviewer_B.jsonl",
         lambda row: row.update(case_id="NOT_THE_SAME"))
    with pytest.raises(ValueError, match="universe mismatch"):
        m36.reconcile(tmp_path)
    again = tmp_path / "again"
    seed(again)
    edit(again / "pip/reviewers/reviewer_B.jsonl",
         lambda row: row.update(reviewer="reviewer_A"))
    with pytest.raises(ValueError, match="identity mismatch"):
        m36.reconcile(again)


def test_unsubstantiated_verdict_not_counted(tmp_path):
    seed(tmp_path)
    for r in ("A", "B"):
        edit(tmp_path / f"edc/reviewers/behavior_reviewer_{r}.jsonl",
             lambda row: row.update(conformance_label=True, violation_label=False,
                                    status="reviewed", observed_behavior="42"))
    _, manifest = m36.reconcile(tmp_path)
    assert manifest["comparison_counts"]["pending_or_incomplete"] == 20


def test_zero_observation_is_valid(tmp_path):
    seed(tmp_path)
    for r in ("A", "B"):
        edit(tmp_path / f"edc/reviewers/behavior_reviewer_{r}.jsonl",
             lambda row: row.update(conformance_label=True, violation_label=False,
                                    status="reviewed", observed_offers=0,
                                    approved_runtime_evidence="approved run",
                                    reviewer_notes="environment"))
    _, manifest = m36.reconcile(tmp_path)
    assert manifest["comparison_counts"]["reviewer_agreement"] == 1
    assert manifest["independent_adjudications"] == 0
