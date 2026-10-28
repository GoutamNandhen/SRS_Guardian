"""M38: hand a reviewer complete, hash-verified Werkzeug evidence without network.

Reuses M20/M35, not a new verifier or a new scoring gate. No upstream code is
imported, installed, or executed; source files are written as inert .txt files.
Reviewer A/B packages contain no adjudication, gold, model predictions, or
sampling origins. The internal provenance remains outside reviewer packages.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from backend.evaluation import m35_independent_review_workspace as m35
from backend.evaluation import m37_werkzeug_holdout as m37


ANCHORS = (
    ("before", m37.PARSER, "option = unquote_header_value(option)"),
    ("after", m37.PARSER, "option = unquote_header_value(option).lower()"),
    ("before", m37.CALLER, 'filename = extra.get("filename")'),
    ("after", m37.CALLER, 'filename = extra.get("filename")'),
    ("after", m37.TEST, "def test_parse_options_header_case_insensitive"),
)


def _source_index(files: dict[str, dict[str, bytes]]) -> str:
    cards = []
    for revision, path, marker in ANCHORS:
        lines = files[revision][path].decode("utf-8").splitlines()
        number = m37.anchor("\n".join(lines), marker)
        excerpt = "\n".join(f"{i + 1:4} {lines[i]}" for i in
                            range(max(0, number - 9), min(len(lines), number + 8)))
        local = f"source/{revision}/{path}.txt"
        cards.append(
            f"<article><h2>{escape(revision)} — {escape(path)}</h2>"
            f"<p>Commit: {escape(m37.REVISIONS[revision])}; "
            f"line {number}. <a href='{escape(local, quote=True)}'>"
            "Full verified source (offline text)</a> · "
            f"<a href='{escape(m37.url(revision, path, number), quote=True)}'>"
            "Pinned upstream line</a></p>"
            f"<pre>{escape(excerpt)}</pre></article>"
        )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Werkzeug pinned source index — not gold</title>"
        "<style>body{font:16px system-ui;max-width:1100px;margin:24px auto;"
        "padding:12px;color:#192a3b}article{padding:16px;border:1px solid #ccd;"
        "margin:16px 0;border-radius:8px}pre{overflow:auto;background:#f4f6f9;"
        "padding:14px}a{overflow-wrap:anywhere}</style></head><body>"
        "<h1>Verified pinned source — independent review</h1>"
        "<p>These are source excerpts, not runtime results, gold labels or "
        "adjudications. Open the full local text files for context. "
        "Before/after differences do not establish behavioral outcomes.</p>"
        + "".join(cards) +
        "<p>Complete LICENSE.rst, http.py, multipart.py and test_http.py files "
        "at both revisions are included under source/before and source/after "
        "as inert .txt files.</p></body></html>"
    )


def generate(out_dir: Path, files: dict[str, dict[str, bytes]] | None = None) -> dict:
    # Verification is performed even for caller-supplied bytes, before writing.
    files = m37.fetch_pinned() if files is None else files
    evidence = m37.build_evidence(files)
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError("Output directory must be empty to prevent mixed reviewer runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="srs-m38-") as temp:
        stage = Path(temp)
        m37.write_evidence(evidence, stage)
        shutil.copytree(stage / "internal", out_dir / "internal")
        for reviewer in m35.REVIEWERS:
            dest = out_dir / f"reviewer_{reviewer}"
            dest.mkdir()
            links = m35.read_packet(stage / "reviewers" / f"reviewer_{reviewer}.jsonl",
                                    6, reviewer, behavior=False)
            behaviors = m35.read_packet(
                stage / "reviewers" / f"behavior_reviewer_{reviewer}.jsonl",
                4, reviewer, behavior=True)
            payload = json.dumps({
                "project": "werkzeug", "reviewer": reviewer,
                "links": links, "behaviors": behaviors,
            }, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
            page = m35.PAGE.replace("__PAYLOAD__", payload)
            page = page.replace('<section id="links">',
                                '<p><a href="source_index.html">Open verified source '
                                'snapshots (available offline)</a></p>\n'
                                '<section id="links">', 1)
            (dest / "workspace.html").write_text(page, encoding="utf-8")
            (dest / "source_index.html").write_text(_source_index(files), encoding="utf-8")
            for revision, paths in m37.FILES.items():
                for path in paths:
                    local = dest / "source" / revision / (path + ".txt")
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_bytes(files[revision][path])
            shutil.copyfile(stage / "reviewers" / f"reviewer_{reviewer}.jsonl",
                            dest / "link_seed.jsonl")
            shutil.copyfile(stage / "reviewers" / f"behavior_reviewer_{reviewer}.jsonl",
                            dest / "behavior_seed.jsonl")
            shutil.copyfile(stage / "reviewers" / "REVIEW_INSTRUCTIONS.md",
                            dest / "REVIEW_INSTRUCTIONS.md")
    manifest = {
        "schema": "m38-offline-reviewer-handoff-1",
        "project": m37.PROJECT,
        "license": evidence["manifest"]["license"],
        "source_file_revision_objects_hash_verified": 8,
        "independent_reviewer_packages": 2,
        "links_pending_per_reviewer": 6,
        "behavior_revisions_pending_per_reviewer": 4,
        "independent_reviewer_submissions": 0,
        "independent_adjudications": 0,
        "approved_runtime_observations": 0,
        "external_project_code_executed": False,
        "held_out_candidate_only": True,
        "metrics": {name: None for name in m37.METRICS},
        "next_blocker": "Two humans independently review six links and four revision "
                        "behaviors each using approved execution evidence; a third "
                        "adjudicates. Freeze the verifier before any held-out scoring.",
    }
    (out_dir / "internal" / "m38_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    manifest = generate(args.out_dir)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
