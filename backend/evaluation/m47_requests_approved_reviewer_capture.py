"""First-party capture client for *approved independent* Requests #7432 review.

Never invoked by CI/tests against upstream code. This module does not import
Requests until a reviewer explicitly runs main() against a pinned checkout.
Observations are not labels, adjudication, or held-out scores.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
from importlib import metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
from urllib.parse import urlsplit

REVISIONS = {
    "before": "0b401c76b6e80a4eecf3c690085b2553f6e261ca",
    "after": "6404f345e562d962abe6700a1c357ec1e7e18232",
}
BLOBS = {
    "before": {
        "LICENSE": "67db8588217f266eb561f75fae738656325deac9",
        "src/requests/models.py": "4142f2a4bbf39820b46b414a15af805a34b1a013",
        "tests/test_requests.py": "09cd4a388a760ad7d757afe0b9560e486ea4b7c9",
    },
    "after": {
        "LICENSE": "67db8588217f266eb561f75fae738656325deac9",
        "src/requests/models.py": "57e114866da042a866dced7a2f55a8a7da597878",
        "tests/test_requests.py": "571535fe7998dcc7a747266f4461f96fcea3c2d3",
    },
}
PAYLOAD = b"data"


class CaptureError(ValueError):
    pass


class AttrProxy:
    """Delegate file-like methods via __getattr__, as in the upstream regression."""

    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __getattr__(self, name):
        return getattr(self.wrapped, name)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def validate_url(url: str) -> str:
    parts = urlsplit(url)
    try:
        port = parts.port
    except ValueError as exc:
        raise CaptureError("Invalid fixture port") from exc
    if (parts.scheme != "http" or parts.hostname != "127.0.0.1"
            or port is None or not 1 <= port <= 65535
            or parts.path != "/redirect" or parts.query or parts.fragment
            or parts.username is not None or parts.password is not None):
        raise CaptureError("Only http://127.0.0.1:<port>/redirect is permitted")
    return url


def verify_checkout(checkout: Path, revision: str) -> dict[str, str]:
    if revision not in REVISIONS:
        raise CaptureError("Unknown pinned revision")
    root = checkout.resolve(strict=True)
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, timeout=10)
    if result.stdout.strip() != REVISIONS[revision]:
        raise CaptureError("Git HEAD is not the expected pinned revision")
    for relative, expected in BLOBS[revision].items():
        path = root / relative
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise CaptureError("Missing, symlinked, or unsafe source: " + relative)
        raw = path.read_bytes()
        if len(raw) > 2_000_000 or git_blob_sha(raw) != expected:
            raise CaptureError("Pinned Git blob mismatch: " + relative)
        if relative == "LICENSE" and not all(
            part in raw.decode("utf-8") for part in
            ("Apache License", "Version 2.0, January 2004",
             "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION")
        ):
            raise CaptureError("Apache-2.0 license text did not match")
    return dict(BLOBS[revision])


def collect(client, url: str) -> dict:
    """Run only when the reviewer explicitly supplies an approved client module."""
    from io import BytesIO

    proxy = AttrProxy(BytesIO(PAYLOAD))
    try:
        response = client.post(url, data=proxy, allow_redirects=True, timeout=10)
        return {
            "response_status": response.status_code,
            "redirect_history": [
                {"status": item.status_code, "url": item.url}
                for item in response.history
            ],
            "response_url": response.url,
            "response_text": response.text[:2000],
            "exception": None,
        }
    except Exception as exc:
        return {
            "response_status": None, "redirect_history": [],
            "response_url": None, "response_text": None,
            "exception": {"type": type(exc).__name__, "message": str(exc)[:2000]},
        }


def installed_version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--revision", choices=tuple(REVISIONS), required=True)
    parser.add_argument("--fixture-url", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    validate_url(args.fixture_url)
    if args.out.exists():
        parser.error("Refusing to overwrite an existing evidence file")
    try:
        verified_blobs = verify_checkout(args.checkout, args.revision)
    except (OSError, subprocess.SubprocessError, CaptureError) as exc:
        parser.error(str(exc))
    root = args.checkout.resolve()
    # Explicit trust boundary: ONLY a reviewer-approved invocation imports upstream.
    if "requests" in sys.modules:
        parser.error("Requests already imported before pinned-path validation")
    sys.path.insert(0, str(root / "src"))
    requests = importlib.import_module("requests")
    module_file = Path(requests.__file__).resolve()
    expected_package = (root / "src" / "requests").resolve()
    if not module_file.is_relative_to(expected_package):
        parser.error("Imported Requests does not originate from pinned checkout")
    record = {
        "schema": "m47-approved-reviewer-observation-v1",
        "reviewer_supplied": True,
        "independent_adjudication": False,
        "behavior_label": None,
        "revision": args.revision,
        "git_commit": REVISIONS[args.revision],
        "verified_git_blobs": verified_blobs,
        "fixture_url": args.fixture_url,
        "fixture_log": "Attach separately; server writes JSONL on shutdown.",
        "expected_payload_sha256": hashlib.sha256(PAYLOAD).hexdigest(),
        "expected_payload_length": len(PAYLOAD),
        "requests_module_path": str(module_file),
        "python": sys.version,
        "platform": platform.platform(),
        "dependency_versions": {
            package: installed_version(package)
            for package in ("urllib3", "idna", "charset-normalizer", "certifi")
        },
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "observation": collect(requests, args.fixture_url),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with args.out.open("xb") as output:
        output.write(payload)
    print(json.dumps({
        "evidence_path": str(args.out),
        "evidence_sha256": hashlib.sha256(payload).hexdigest(),
        "note": "Observation only; NOT independently adjudicated ground truth",
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
