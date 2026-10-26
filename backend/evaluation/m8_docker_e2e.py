"""M8: exact, trusted-fixture-only Docker end-to-end gate for the M2→M4 path.

Runs only against repository-owned reviewed samples in examples/m4; does not accept
a user ZIP or an arbitrary module, image, URL or Docker command. Intended for CI.
An operator-attested source↔image binding is not cryptographic provenance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from backend.app.research.approved_runner import ApprovalError, execute_approved
from backend.app.services.code_traceability import index_archive, save_index

SAMPLES = (
    ("banking_api.py", "examples.m4.banking_api", "passed_available_checks"),
    ("banking_api_buggy.py", "examples.m4.banking_api_buggy", "observed_violation"),
)
RULE = "The banking system shall reject transfers exceeding 10000 rupees."
IMAGE_ID = re.compile(r"sha256:[a-f0-9]{64}\Z")


def _approved_local_image(tag: str) -> str:
    """Inspect a locally built image; do not pull remote images."""
    if tag != "srs-m8-trusted-banking:ci":
        raise ApprovalError("M8 supports only the fixed CI-reviewed image tag")
    p = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", tag],
        capture_output=True, text=True, check=False, timeout=15)
    image_id = p.stdout.strip()
    if p.returncode or not IMAGE_ID.fullmatch(image_id):
        raise ApprovalError("Approved fixture image was not built locally")
    return image_id


def run(*, image_tag: str = "srs-m8-trusted-banking:ci") -> dict:
    image_id = _approved_local_image(image_tag)
    results = []
    with tempfile.TemporaryDirectory(prefix="srs-m8-") as td:
        tmp = Path(td)
        indexes = tmp / "code_indexes"
        for source_name, module, expected in SAMPLES:
            filename = Path("examples/m4") / source_name
            source = filename.read_bytes()
            if len(source) > 40_000:
                raise ApprovalError("Fixture unexpectedly large")
            # Only these exact two committed files can enter this CI index.
            buf = BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("banking_api.py", source)
            index = index_archive(buf.getvalue(), source_name)
            save_index(index, indexes)
            symbols = [
                s for s in index["symbols"]
                if s["qualified_name"] == "transfer_money"
                and {"method": "POST", "route": "/payments/transfer"} in s["http"]
            ]
            if len(symbols) != 1:
                raise AssertionError("Exactly one reviewed transfer endpoint required")
            symbol = symbols[0]
            target_id = "ci-approved-" + source_name.removesuffix(".py")
            manifest = {
                "schema_version": "m4-approvals-1",
                "targets": [{
                    "id": target_id, "approved": True,
                    "source_index_id": index["index_id"],
                    "symbol_id": symbol["symbol_id"],
                    "image_id": image_id,
                    "app_module": module, "app_attribute": "app",
                    "route": "/payments/transfer", "method": "POST",
                    "revision": "m8-reviewed-ci-fixture",
                }],
            }
            manifest_file = tmp / "approved_targets.json"
            manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
            report = execute_approved(
                manifest_path=manifest_file, index_directory=indexes,
                target_id=target_id, index_id=index["index_id"],
                symbol_id=symbol["symbol_id"], req_key="REQ-TRANSFER-LIMIT",
                requirement=RULE, reviewer_approved=True,
            )
            if report["worker_evidence"]["decision"] != expected:
                raise AssertionError(f"{source_name}: unexpected conformance observation")
            if report["source_image_binding"] != "operator_attested_not_cryptographically_verified":
                raise AssertionError("Provenance must not be overstated")
            if (report["source_content_binding"] != "worker_reported_module_digest_matches_index"
                    or report["indexed_source_sha256"] != hashlib.sha256(source).hexdigest()
                    or report["executed_module_sha256"] != hashlib.sha256(source).hexdigest()):
                raise AssertionError("Executed module bytes must match the indexed source")
            observations = report["worker_evidence"]["cases"]
            if len(observations) != 2 or not all(
                isinstance(o.get("http_status"), int) and o["http_status"] == 200
                for o in observations
            ):
                raise AssertionError("M4 must return two actual HTTP 200 observations")
            results.append({
                "fixture": source_name, "expected_decision": expected,
                "observed_decision": report["worker_evidence"]["decision"],
                "source_sha256": hashlib.sha256(source).hexdigest(),
                "source_content_binding": report["source_content_binding"],
                "executed_module_sha256": report["executed_module_sha256"],
                "source_index_id": index["index_id"], "symbol_id": symbol["symbol_id"],
                "image_id": image_id, "worker_evidence_sha256":
                    report["worker_evidence"]["evidence_sha256"],
                "cases": observations,
            })
    return {
        "schema_version": "srs-m8-trusted-fixture-e2e-1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "docker_executed": True, "trusted_fixture_only": True,
        "independent_project_count": 0, "research_95_eligible": False,
        "external_generalization_measured": False,
        "source_image_binding": "operator_attested_not_cryptographically_verified",
        "all_expectations_met": len(results) == len(SAMPLES),
        "results": results,
        "warning": "Fixed controlled examples; NOT a 95% real-world accuracy benchmark",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted-only Docker M8 integration test")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    result = run()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({
        "docker_executed": result["docker_executed"],
        "observed_decisions": [r["observed_decision"] for r in result["results"]],
        "research_95_eligible": result["research_95_eligible"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
