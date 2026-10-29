"""M60: bounded, static, non-executing Django URL userinfo rule check.

This is a development-case static property diagnostic, NOT behavioral conformance
and NOT independently annotated requirement-to-code ground truth. The source
locus was identified from an already inspected upstream historical PR.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import urllib.request

REPO = "django/django"
PATH = "django/core/validators.py"
LICENSE_PATH = "LICENSE"
LICENSE_BLOB = "5f4f225dd282aa7e4361ec3c2750bbbaaed8ab1f"
REVISIONS = {
    "before": {"commit": "b9cf764be62e77b4777b3a75ec256f6209a57671",
               "blob": "92394a7eaeadb697481b905332cc6e5af5bd7d33"},
    "after": {"commit": "cdcf4164bec9dc09465424d7042c3f9d4f0f1fdc",
              "blob": "c1c9cd1c87e83564c90493a506da51fef7cea30f"},
}
# Only a tightly bounded grammar is supported. Unknown regex syntax => abstain.
USERINFO = re.compile(
    r"^\(\?:(?P<user>\\S|\[\^[^\]]+\])\+\(\?::(?P<password>\\S|\[\^[^\]]+\])\*\)\?@\)\?$"
)
FRAGMENT = re.compile(r"://(?P<userinfo>\(\?:.{1,128}?@\)\?)\(\?:")
PROHIBITED = (":", "@", "/")


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _leading_literal(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _leading_literal(node.left)
    return ""


def extract_userinfo(source: str) -> tuple[str, int]:
    if len(source) > 2_000_000:
        raise ValueError("Source too large")
    tree = ast.parse(source)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)
               and n.name == "URLValidator"]
    if len(classes) != 1:
        raise ValueError("URLValidator class not unique")
    assignments = [n for n in classes[0].body if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == "regex"
                           for t in n.targets)]
    if len(assignments) != 1 or not isinstance(assignments[0].value, ast.Call):
        raise ValueError("URLValidator regex assignment unsupported")
    call = assignments[0].value
    if not (isinstance(call.func, ast.Name) and call.func.id == "_lazy_re_compile"
            and call.args):
        raise ValueError("URLValidator regex call unsupported")
    prefix = _leading_literal(call.args[0])
    matches = list(FRAGMENT.finditer(prefix))
    if len(matches) != 1:
        raise ValueError("Userinfo regex fragment not uniquely extractable")
    fragment = matches[0].group("userinfo")
    lines = [i for i, line in enumerate(source.splitlines(), 1) if fragment in line]
    if len(lines) != 1:
        raise ValueError("Userinfo source line not unique")
    return fragment, lines[0]


def _exclusions(token: str) -> set[str] | None:
    if token == r"\S":
        return set()  # Non-whitespace also permits all three forbidden delimiters.
    if not (token.startswith("[^") and token.endswith("]")):
        return None
    body = token[2:-1]
    if not body.startswith(r"\s"):
        return None
    rest = body[2:]
    # Only plain delimiter exclusions are modeled; ranges/escapes abstain.
    if any(c not in ":@/" for c in rest):
        return None
    return set(rest)


def check_fragment(fragment: str) -> dict:
    match = USERINFO.fullmatch(fragment)
    if not match:
        return {"static_result": "abstain_unsupported_grammar", "reason": "unsupported userinfo grammar"}
    parsed = {}
    for field in ("user", "password"):
        token = match.group(field)
        excluded = _exclusions(token)
        if excluded is None:
            return {"static_result": "abstain_unsupported_grammar", "reason": "unsupported character class"}
        parsed[field] = {"token": token, "excluded_delimiters": sorted(excluded),
                         "permitted_prohibited_delimiters": sorted(set(PROHIBITED) - excluded)}
    permits = any(parsed[k]["permitted_prohibited_delimiters"] for k in parsed)
    return {"static_result": "static_rule_violated" if permits else "static_rule_satisfied",
            "user_and_password_character_classes": parsed,
            "scope": "userinfo regex character-class property only; not whole URLValidator behavior"}


def verify_snapshot(source: bytes, license_raw: bytes, revision: str) -> dict:
    if revision not in REVISIONS:
        raise ValueError("Unknown revision")
    info = REVISIONS[revision]
    if git_blob(source) != info["blob"] or git_blob(license_raw) != LICENSE_BLOB:
        raise ValueError("Pinned source/license Git blob mismatch")
    license_text = license_raw.decode("utf-8")
    if not all(term in license_text for term in (
            "Django Software Foundation", "Redistribution and use in source and binary forms",
            "THIS SOFTWARE IS PROVIDED")):
        raise ValueError("BSD-3-Clause license evidence not established")
    fragment, line = extract_userinfo(source.decode("utf-8-sig"))
    return {"revision": revision, "source_commit": info["commit"],
            "source_git_blob": info["blob"], "source_sha256": sha256(source),
            "license": "BSD-3-Clause", "license_git_blob": LICENSE_BLOB,
            "license_sha256": sha256(license_raw), "source_path": PATH,
            "source_line": line,
            "source_url": f"https://github.com/{REPO}/blob/{info['commit']}/{PATH}#L{line}",
            "extracted_literal_userinfo_regex": fragment, **check_fragment(fragment)}


def download_pinned(commit: str, path: str) -> bytes:
    if commit not in {v["commit"] for v in REVISIONS.values()} or path not in {PATH, LICENSE_PATH}:
        raise ValueError("Only pinned upstream paths are allowed")
    url = f"https://raw.githubusercontent.com/{REPO}/{commit}/{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "SRS-Guardian-M60-static-evidence"})
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Oversized pinned upstream blob")
    return raw


def build(fetch=download_pinned) -> dict:
    records = []
    for revision, info in REVISIONS.items():
        source = fetch(info["commit"], PATH)
        license_raw = fetch(info["commit"], LICENSE_PATH)
        records.append(verify_snapshot(source, license_raw, revision))
    return {
        "schema": "m60-django-static-userinfo-property-development-NOT-GOLD-1",
        "requirement_source": "https://github.com/django/django/pull/10097",
        "requirement_property": "Raw colon, at-sign and slash must not be permitted inside username/password character classes; the single colon separator remains permitted.",
        "case_selection": "Previously inspected historical fix; known URLValidator locus; NOT blind retrieval",
        "independent_annotation": None, "independent_behavioral_observations": 0,
        "adjudications": 0, "held_out_projects_scored": 0,
        "conformance_accuracy": None, "violation_precision": None,
        "violation_recall": None, "coverage": None,
        "external_project_code_executed": False,
        "limitations": [
            "Only a syntactic regex character-class property is checked; this is not runtime URL validation.",
            "Known historical PR/source locus makes this a development demonstration, not held-out evaluation.",
            "No independent requirement-to-code trace labels, test observations, or adjudications exist.",
            "Other regex forms abstain; this is not a general requirement-to-code verifier.",
            "Historical upstream gold patch and test metadata are not independent ground truth.",
        ],
        "revisions": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    result = build()
    if args.out_dir.exists():
        raise ValueError("Refusing to overwrite evidence")
    args.out_dir.mkdir(parents=True)
    (args.out_dir / "INTERNAL_STATIC_DEVELOPMENT_NOT_GOLD.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / "REVIEW_BOUNDARY.md").write_text(
        "# M60 bounded static Django demonstration — NOT GOLD\n\n"
        "The issue/known historical fix locus is already inspected. Do not provide this "
        "oracle-informed analysis to blinded M20 reviewers before they freeze stage-1 "
        "links. This source-level check only inspects literal regex character classes, "
        "without importing or executing Django or its tests. It does not prove the "
        "runtime validator accepts/rejects any complete URL.\n\n"
        "Independent reviewers must (1) judge the requirement-to-code link "
        "without historical fix hints, (2) verify the intended rule and test relevance, "
        "(3) independently record approved before/after behavioral observations with "
        "pinned dependencies/inputs/outputs, and (4) submit to a separate adjudicator. "
        "Freeze the general verifier before any untouched held-out project evaluation. "
        "All conformance/violation metrics remain undefined.\n", encoding="utf-8")
    print(json.dumps({"revisions": len(result["revisions"]),
                      "static_results": {r["revision"]: r["static_result"] for r in result["revisions"]},
                      "independent_labels": 0, "behavioral_accuracy": None,
                      "external_project_code_executed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
