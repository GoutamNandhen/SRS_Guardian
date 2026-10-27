"""M26: frozen M25 retrieval transferred to an unseen Apache-2.0 DSP-TCK project.

This is a documentation-to-compliance-test *module association* pilot, not
behavioral requirement-to-implementation conformance. The four README module
descriptions are not independently adjudicated requirements. The five
documentation-derived associations are unverified observations, not gold.
No third-party Java or downloaded material is executed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.request

from backend.evaluation.m20_annotation_queue import build_queue, write_outputs
from backend.evaluation.m25_source_grounded_teastore import evaluate_cohort
from backend.evaluation.m24_cross_corpus_baseline import NO_CONFORMANCE

REPO = "eclipse-dataspacetck/dsp-tck"
COMMIT = "61bc3d2d7f81bd5b1eee164621872fd6808eb185"
FILES = {
    "LICENSE.md": "2bb9ad240fa04c8cf706a4901c4807878e90c2dc",
    "NOTICE.md": "7d7088653155ffbbdeb880d148c766fb1e706ec9",
    "README.md": "4c9e590fd9e1fb2eaeac84ea78908fa07486d152",
    "dsp/dsp-metadata/src/main/java/org/eclipse/dataspacetck/dsp/verification/metadata/Metadata01Test.java": "fd1316f2fcf35196c8792859efd7ccc482ecd880",
    "dsp/dsp-catalog/src/main/java/org/eclipse/dataspacetck/dsp/verification/catalog/Catalog01Test.java": "c25a33fec284ba10f36ab486325b9e705a0b4b61",
    "dsp/dsp-contract-negotiation/src/main/java/org/eclipse/dataspacetck/dsp/verification/cn/ContractNegotiationProvider01Test.java": "08d369561eabb24475e51f03167e5bcc7ce638a5",
    "dsp/dsp-transfer-process/src/main/java/org/eclipse/dataspacetck/dsp/verification/tp/TransferProcessProvider01Test.java": "a721da5c53eedda89c37f90e89aa8754a8141a24",
    "dsp/dsp-transfer-process/src/main/java/org/eclipse/dataspacetck/dsp/verification/tp/TransferProcessConsumer01Test.java": "73b4f11f12be96a860b2176065e89e1fe96b56ae",
}
# These are copied exactly from the pinned README's four module descriptions,
# with whitespace normalized. They are NOT normative behavioral requirements.
MODULE_TEXT = {
    "MODULE_METADATA": "dsp-metadata: Tests for the metadata endpoint in package org.eclipse.dataspacetck.dsp.verification.metadata.",
    "MODULE_CATALOG": "dsp-catalog: Tests for the catalog protocol in package org.eclipse.dataspacetck.dsp.verification.catalog.",
    "MODULE_NEGOTIATION": "dsp-contract-negotiation: Tests for the contract negotiation protocol in package org.eclipse.dataspacetck.dsp.verification.cn.",
    "MODULE_TRANSFER": "dsp-transfer-process: Tests for the transfer process protocol in package org.eclipse.dataspacetck.dsp.verification.tp.",
}
MODULE_PACKAGE = {
    "MODULE_METADATA": "/verification/metadata/",
    "MODULE_CATALOG": "/verification/catalog/",
    "MODULE_NEGOTIATION": "/verification/cn/",
    "MODULE_TRANSFER": "/verification/tp/",
}
MAX_BYTES = 2_000_000
PROJECT_ID = "ECLIPSE_DSP_TCK_MODULE_TO_TEST_M26"


class SourceError(ValueError):
    """Pinned external data mismatch or invalid evidence."""


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()


def fetch_pinned(*, source_dir: Path | None = None) -> dict[str, bytes]:
    """Fetch only exact allowlisted GitHub static files; verify every Git blob."""
    out = {}
    for path, expected in FILES.items():
        if source_dir is None:
            url = f"https://raw.githubusercontent.com/{REPO}/{COMMIT}/{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "srs-guardian-m26-static"})
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read(MAX_BYTES + 1)
        else:
            raw = (source_dir / path).read_bytes()
        if len(raw) > MAX_BYTES or git_blob_id(raw) != expected:
            raise SourceError("Pinned source hash mismatch: " + path)
        out[path] = raw
    return out


def _snapshot_digest(code: dict[str, bytes]) -> str:
    h = hashlib.sha256()
    for path in sorted(code):
        raw = code[path]
        name = path.encode("utf-8")
        h.update(len(name).to_bytes(4, "big"))
        h.update(name)
        h.update(len(raw).to_bytes(8, "big"))
        h.update(raw)
    return h.hexdigest()


def build_evidence(files: dict[str, bytes]) -> dict:
    """Prepare held-aside project transfer evaluation and M20 blind queue."""
    if set(files) != set(FILES):
        raise SourceError("Incomplete or unexpected pinned files")
    for path, expected in FILES.items():
        if git_blob_id(files[path]) != expected:
            raise SourceError("Pinned source hash mismatch: " + path)
    if not files["LICENSE.md"].lstrip().startswith(b"Apache License"):
        raise SourceError("Pinned Apache-2.0 license missing")
    if b"SPDX-License-Identifier: Apache-2.0" not in files["NOTICE.md"]:
        raise SourceError("Pinned NOTICE license declaration missing")
    readme = files["README.md"].decode("utf-8")
    normalized = re.sub(r"\s+", " ", readme.replace("**", "").replace("`", ""))
    # Source is author documentation, NOT a separately adjudicated spec.
    for rid, sentence in MODULE_TEXT.items():
        if sentence not in normalized:
            raise SourceError("README module description changed: " + rid)
    code = {path: raw for path, raw in files.items() if path.endswith(".java")}
    if len(code) != 5:
        raise SourceError("Expected five pinned compliance test classes")
    for path, raw in code.items():
        text = raw.decode("utf-8")
        if "SPDX-License-Identifier: Apache-2.0" not in text or "@MandatoryTest" not in text:
            raise SourceError("Missing license header or mandatory test: " + path)
    paths = sorted(code)
    symbols = [
        {"symbol_id": f"TEST_{i:03d}", "source_path": path,
         "qualified_name": Path(path).stem,
         "description": "Pinned Apache-2.0 Java mandatory compliance test class"}
        for i, path in enumerate(paths, 1)
    ]
    sid = {s["source_path"]: s["symbol_id"] for s in symbols}
    reqs = [{"requirement_id": rid, "requirement_text": text}
            for rid, text in sorted(MODULE_TEXT.items())]
    observed = [
        {"requirement_id": rid, "symbol_id": sid[path]}
        for rid, package in MODULE_PACKAGE.items() for path in paths if package in path
    ]
    if len(observed) != 5:
        raise SourceError("README module associations do not match source paths")
    universe = {
        "schema_version": "m20-candidate-universe-1",
        "project_id": PROJECT_ID, "source_commit": COMMIT,
        "code_snapshot_sha256": _snapshot_digest(code),
        "requirements": reqs, "symbols": symbols, "observed_links": observed,
    }
    queue = build_queue(universe, seed="m26-dsp-tck-readme-modules-v1",
                        hard_per_requirement=2, random_per_requirement=2)
    if len(queue["queue"]) != 20:
        raise SourceError("Expected complete 4x5 review universe")
    eval_reqs = [
        {"id": rid, "text": text,
         "observed_paths": [path for path in paths if MODULE_PACKAGE[rid] in path]}
        for rid, text in sorted(MODULE_TEXT.items())
    ]
    comparison = evaluate_cohort(eval_reqs, code)
    source_files = {
        path: {"git_blob_sha1": FILES[path],
               "sha256": hashlib.sha256(raw).hexdigest(),
               "line_count": len(raw.decode("utf-8").splitlines()),
               "url": f"https://github.com/{REPO}/blob/{COMMIT}/{path}"}
        for path, raw in files.items()
    }
    reviewer_index = {
        "schema_version": "m26-blinded-source-index-1",
        "source_repository": REPO, "source_commit": COMMIT,
        "source_files": source_files,
        "review_pairs": [{"case_id": row["case_id"],
                          "readme_url": source_files["README.md"]["url"],
                          "source_url": source_files[row["source_path"]]["url"]}
                         for row in queue["queue"]],
        "warning": "README module descriptions are not normative requirements; Java files are compliance tests, not the connector implementation. All associations unverified; no behavioral conformance judgments.",
    }
    baseline = {
        "schema_version": "m26-dsp-tck-transfer-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "project": "Eclipse Dataspace TCK",
        "source_commit": COMMIT, "source_license": "Apache-2.0",
        "pinned_static_files": len(files), "module_descriptions": len(reqs),
        "java_test_classes": len(code), "documentation_derived_associations_unverified": len(observed),
        "blinded_pairs_pending_review": len(queue["queue"]),
        "independently_adjudicated_link_pairs": 0,
        "independently_adjudicated_behavioral_cases": 0,
        "research_95_eligible": False, "independent_gold": False,
        **NO_CONFORMANCE,
        "comparison": comparison,
        "limitations": [
            "M25 source-content ranking frozen before this external project; no parameter tuning.",
            "Only four README module descriptions and five purposively selected compliance test classes.",
            "Module descriptions are not normative behavioral requirements.",
            "README package associations are documentation-derived observations, not independent gold.",
            "The test suite is not the product implementation, and no connector was executed.",
            "No independent link labels, negatives, behavioral oracles, or violation outcomes.",
            "Review all 20 candidate associations independently with cited source lines; adjudicate disagreements.",
            "Acquire independently licensed connector source snapshots and independently verified conforming/violating revisions for conformance.",
        ],
    }
    return {"reviewer": {"queue": queue, "index": reviewer_index},
            "internal": {"baseline": baseline, "universe": universe,
                         "source_manifest": source_files}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = build_evidence(fetch_pinned())
    reviewer = args.out_dir / "reviewers"
    internal = args.out_dir / "internal"
    write_outputs(result["reviewer"]["queue"], reviewer)
    (reviewer / "manifest.json").unlink()  # selection origins are internal only
    reviewer.mkdir(parents=True, exist_ok=True)
    (reviewer / "source_index.json").write_text(
        json.dumps(result["reviewer"]["index"], indent=2) + "\n", encoding="utf-8")
    (reviewer / "README.txt").write_text(
        "Review all 20 pairs independently. Inspect pinned README and Java source URLs. "
        "Record linked/not-linked/uncertain with cited source lines; third reviewer adjudicates. "
        "Do not use internal manifests or assume unobserved links are negatives. "
        "These are module-to-compliance-test links, NOT connector conformance cases.\n",
        encoding="utf-8")
    internal.mkdir(parents=True, exist_ok=True)
    write_outputs(result["reviewer"]["queue"], internal / "annotation_provenance")
    for name, data in result["internal"].items():
        (internal / (name + ".json")).write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    b = result["internal"]["baseline"]
    print(json.dumps({
        "project": b["project"], "pinned_files": b["pinned_static_files"],
        "module_descriptions": b["module_descriptions"],
        "java_test_classes": b["java_test_classes"],
        "unverified_module_associations": b["documentation_derived_associations_unverified"],
        "blinded_review_pairs": b["blinded_pairs_pending_review"],
        "independent_gold": False, "research_95_eligible": False,
        "retrieval": [
            {"method": run["method"],
             "hit_at_1": run["hit_at_k_on_observed_linked_statements"]["1"],
             "observed_link_recall_at_3": run["observed_positive_link_recall_at_k"]["3"]}
            for run in b["comparison"]["runs"]],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
