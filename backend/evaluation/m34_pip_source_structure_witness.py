"""M34: pinned pip resolver structural verification, without executing pip.

AST-inspect the exact before/after link+extras success path. This establishes
source-level structure only, not runtime success, independent gold or accuracy.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

from backend.evaluation import m29_pip_historical_regression as m29

SCHEMA = "m34-pip-link-extras-source-structure-1"
METRICS = ("conformance_accuracy", "violation_precision",
           "violation_recall", "conformance_coverage")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise m29.EvidenceError("Pinned pip source structure changed: " + message)


def _method(source: str) -> ast.FunctionDef:
    tree = ast.parse(source)  # Parse text only; never import or execute it.
    factories = [n for n in tree.body if isinstance(n, ast.ClassDef)
                 and n.name == "Factory"]
    _require(len(factories) == 1, "Factory class")
    methods = [n for n in factories[0].body if isinstance(n, ast.FunctionDef)
               and n.name == "_make_requirements_from_install_req"]
    _require(len(methods) == 1, "resolver method")
    return methods[0]


def _source_path(method: ast.FunctionDef) -> tuple[list[ast.stmt], ast.If]:
    markers = [n for n in method.body if isinstance(n, ast.If)
               and ast.unparse(n.test) ==
               "not ireq.match_markers(requested_extras)"]
    _require(len(markers) == 1, "marker guard")
    marker_guard = markers[0]
    _require(len(marker_guard.orelse) == 1 and
             isinstance(marker_guard.orelse[0], ast.If), "link branch")
    no_link = marker_guard.orelse[0]
    _require(ast.unparse(no_link.test) == "not ireq.link",
             "explicit local/URL link branch")
    branch = no_link.orelse
    _require(bool(branch), "link branch body")
    success = [n for n in branch if isinstance(n, ast.If)
               and ast.unparse(n.test) == "cand is None"]
    _require(len(success) == 1 and bool(success[0].orelse),
             "candidate-success branch")
    return branch, success[0]


def inspect_structure(source: str, revision: str) -> dict:
    """Fail closed unless the exact pinned source-level path is recognizable."""
    _require(revision in ("before", "after"), "unknown revision")
    method = _method(source)
    branch, cand_guard = _source_path(method)
    assignments = [n for n in branch if isinstance(n, ast.Assign)
                   and len(n.targets) == 1
                   and isinstance(n.targets[0], ast.Name)
                   and n.targets[0].id == "cand"]
    _require(len(assignments) == 1 and isinstance(assignments[0].value, ast.Call),
             "candidate assignment")
    call = assignments[0].value
    _require(isinstance(call.func, ast.Attribute), "candidate constructor")
    kwargs = {kw.arg: ast.unparse(kw.value) for kw in call.keywords}
    _require(len(kwargs) == len(call.keywords), "duplicate/spread keywords")
    _require(bool(call.args) and ast.unparse(call.args[0]) == "ireq.link",
             "candidate link argument")
    success = cand_guard.orelse
    base_yield = "yield self.make_requirement_from_candidate(cand)"
    _require(ast.unparse(success[0]) == base_yield, "base candidate yield")

    if revision == "before":
        _require(call.func.attr == "_make_candidate_from_link",
                 "pre-fix candidate method")
        _require(kwargs.get("extras") == "frozenset(ireq.extras)"
                 and kwargs.get("template") == "ireq", "pre-fix extras template")
        _require(len(success) == 1, "pre-fix successful path must have one yield")
        return {
            "revision": revision, "constructor": call.func.attr,
            "successful_link_extras_yield_sites": 1,
            "explicit_base_without_extras": False,
            "separate_extras_requirement": False,
            "source_anchors": {
                "candidate": m29.source_url(revision, m29.SOURCE, assignments[0].lineno),
                "base_requirement": m29.source_url(revision, m29.SOURCE, success[0].lineno),
            },
        }

    _require(call.func.attr == "_make_base_candidate_from_link",
             "post-fix base candidate method")
    _require("extras" not in kwargs and
             kwargs.get("template") ==
             "install_req_drop_extras(ireq) if ireq.extras else ireq",
             "post-fix extras-free base template")
    _require(len(success) == 2 and isinstance(success[1], ast.If),
             "post-fix separate extras branch")
    extras_guard = success[1]
    _require(ast.unparse(extras_guard.test) == "ireq.extras"
             and not extras_guard.orelse and len(extras_guard.body) == 1,
             "extras conditional")
    _require(ast.unparse(extras_guard.body[0]) ==
             "yield self.make_requirement_from_candidate(self._make_extras_candidate(cand, frozenset(ireq.extras)))",
             "separate extras candidate yield")
    return {
        "revision": revision, "constructor": call.func.attr,
        "successful_link_extras_yield_sites": 2,
        "explicit_base_without_extras": True,
        "separate_extras_requirement": True,
        "source_anchors": {
            "candidate": m29.source_url(revision, m29.SOURCE, assignments[0].lineno),
            "base_requirement": m29.source_url(revision, m29.SOURCE, success[0].lineno),
            "extras_requirement": m29.source_url(revision, m29.SOURCE, extras_guard.lineno),
        },
    }


def build(files: dict[str, dict[str, bytes]]) -> dict:
    evidence = m29.build_evidence(files)  # Hash, MIT license, test provenance, M20.
    observations = [
        inspect_structure(files[revision][m29.SOURCE].decode("utf-8"), revision)
        for revision in ("before", "after")
    ]
    report = {
        "schema": SCHEMA, "project": m29.REPO, "issue": m29.ISSUE,
        "fix": m29.FIX, "commits": m29.COMMITS,
        "source_license": "MIT (pinned LICENSE.txt, hash-verified)",
        "verified_file_revision_objects": 6,
        "structural_observations": observations,
        "m20_unlabeled_link_pairs": len(evidence["queue"]["queue"]),
        "behavior_revision_cases_per_reviewer": len(m29.SCENARIOS) * 2,
        "independent_adjudications": 0,
        "external_project_code_executed": False,
        "held_out_evaluation": False,
        "metrics": {name: None for name in METRICS},
        "scope": (
            "AST-verified source structure under matching markers, a present link, "
            "nonempty extras and a successfully built candidate. The two yields "
            "are syntactic sites, not observed runtime yields or installs."
        ),
        "unverified": (
            "No observed pip resolution/installation outcomes on either revision. "
            "Upstream reporter claim and developer tests are not independent gold."
        ),
        "review_tasks": (
            "Two independent reviewers inspect all six M20 links and six "
            "revision-behavior cases each; confirm requirement legitimacy, "
            "trace links, and approved version-matched execution evidence. "
            "A third adjudicates disagreements. Use unseen held-out projects "
            "for frozen-verifier conformance accuracy, violation precision/recall "
            "and coverage. Unsupported labels remain null."
        ),
    }
    return {"report": report, "m29": evidence}


def write(result: dict, out_dir: Path) -> None:
    m29.write_evidence(result["m29"], out_dir)
    internal = out_dir / "internal"
    (internal / "m34_source_structure.json").write_text(
        json.dumps(result["report"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (internal / "M34_HANDOFF.md").write_text(
        "# M34 internal source-structure handoff\n\n"
        + result["report"]["scope"] + "\n\n"
        + result["report"]["unverified"] + "\n\n"
        + result["report"]["review_tasks"] + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = build(m29.fetch_pinned())
    write(result, args.out_dir)
    print(json.dumps({
        "source_structural_yield_sites": [
            o["successful_link_extras_yield_sites"]
            for o in result["report"]["structural_observations"]
        ],
        "m20_unlabeled_link_pairs": result["report"]["m20_unlabeled_link_pairs"],
        "independent_adjudications": 0,
        "conformance_accuracy": None,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
