"""Offline M22 source inventory tests; no third-party code is fetched or executed."""
import pytest
from backend.evaluation import m22_external_corpus_inventory as m


def fake_tree():
    hashes = {
        "root": "a" * 40, "dvc": "b" * 40, "systems": "c" * 40,
        "albergate": "d" * 40, "dronology": "e" * 40,
    }
    return {
        f"git/trees/{m.COMMIT}": {"tree": [
            {"path": "LICENSE", "type": "blob", "sha": m.LICENSE_BLOB},
            {"path": "README.md", "type": "blob", "sha": m.README_BLOB},
            {"path": "dvc-data", "type": "tree", "sha": hashes["dvc"]},
        ]},
        f"git/trees/{hashes['dvc']}": {"tree": [
            {"path": "systems", "type": "tree", "sha": hashes["systems"]},
        ]},
        f"git/trees/{hashes['systems']}": {"tree": [
            {"path": "albergate", "type": "tree", "sha": hashes["albergate"]},
            {"path": "dronology", "type": "tree", "sha": hashes["dronology"]},
        ]},
        f"git/trees/{hashes['albergate']}?recursive=1": {"tree": [
            {"path": "corpus/req/R1.txt", "type": "blob", "sha": "1" * 40},
            {"path": "corpus/src/A.java", "type": "blob", "sha": "2" * 40},
            {"path": "mappings/ground_truth.txt", "type": "blob", "sha": "3" * 40},
            {"path": "results/summary.csv", "type": "blob", "sha": "4" * 40},
        ]},
        f"git/trees/{hashes['dronology']}?recursive=1": {"tree": [
            {"path": "corpus/req/RE-424.txt", "type": "blob", "sha": "5" * 40},
            {"path": "corpus/src/FlightZoneManager2.java", "type": "blob", "sha": "6" * 40},
            {"path": "mappings/ground_truth.txt", "type": "blob", "sha": "7" * 40},
        ]},
    }


def test_project_inventory_and_no_fake_gold():
    data = fake_tree()
    report = m.build_audit(load=lambda endpoint: data[endpoint])
    assert report["projects_with_requirements_source_and_mapping_candidates"] == ["albergate", "dronology"]
    assert report["research_95_eligible"] is False
    assert report["conformance_accuracy"] is None
    assert report["independently_adjudicated_projects"] == 0
    albergate = report["projects"][0]
    assert (albergate["requirements"], albergate["source_files"], albergate["mapping_candidates"]) == (1, 1, 1)
    assert albergate["data_rights"] == "not_verified"
    assert report["projects"][1]["availability"] == "not_present_at_pinned_commit"


def test_missing_license_fails_closed():
    data = fake_tree()
    data[f"git/trees/{m.COMMIT}"]["tree"][0]["sha"] = "0" * 40
    with pytest.raises(m.AuditError, match="license or README"):
        m.build_audit(load=lambda endpoint: data[endpoint])


def test_truncated_upstream_tree_fails_closed():
    data = fake_tree()
    data["git/trees/" + "d" * 40 + "?recursive=1"]["truncated"] = True
    def load(endpoint):
        result = data[endpoint]
        if result.get("truncated"):
            raise m.AuditError("Truncated Git tree")
        return result
    with pytest.raises(m.AuditError, match="Truncated"):
        m.build_audit(load=load)


def test_path_traversal_fails_closed():
    data = fake_tree()
    data["git/trees/" + "d" * 40 + "?recursive=1"]["tree"][0]["path"] = "../secret"
    with pytest.raises(m.AuditError, match="Invalid source path"):
        m.build_audit(load=lambda endpoint: data[endpoint])


def test_unexpected_git_object_id_fails_closed():
    data = fake_tree()
    data["git/trees/" + "d" * 40 + "?recursive=1"]["tree"][0]["sha"] = "not-sha"
    with pytest.raises(m.AuditError, match="Malformed"):
        m.build_audit(load=lambda endpoint: data[endpoint])
