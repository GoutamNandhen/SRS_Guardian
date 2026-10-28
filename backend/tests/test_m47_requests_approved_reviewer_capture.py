"""First-party-only M47 checks: no external Requests import or execution."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from backend.evaluation import m47_requests_approved_reviewer_capture as m47


def test_fixture_url_is_loopback_only():
    assert m47.validate_url("http://127.0.0.1:8765/redirect").endswith("/redirect")
    for value in (
        "https://127.0.0.1:8765/redirect",
        "http://localhost:8765/redirect",
        "http://127.0.0.1:8765/echo",
        "http://127.0.0.1:8765/redirect?x=1",
        "http://127.0.0.1:8765@evil.example/redirect",
        "http://127.0.0.1:0/redirect",
    ):
        with pytest.raises(m47.CaptureError):
            m47.validate_url(value)


def test_delegated_file_like_behavior():
    proxy = m47.AttrProxy(BytesIO(b"data"))
    assert hasattr(proxy, "__iter__")
    assert proxy.tell() == 0
    assert proxy.read() == b"data"
    assert proxy.tell() == 4


def test_capture_success_uses_exact_input_and_does_not_label():
    class FakeClient:
        def post(self, url, data, allow_redirects, timeout):
            assert url == "http://127.0.0.1:8765/redirect"
            assert allow_redirects is True and timeout == 10
            assert data.read() == b"data"
            return SimpleNamespace(
                status_code=200,
                history=[SimpleNamespace(status_code=307, url=url)],
                url="http://127.0.0.1:8765/echo",
                text='{"length": 4}',
            )

    result = m47.collect(FakeClient(), "http://127.0.0.1:8765/redirect")
    assert result["response_status"] == 200
    assert result["redirect_history"][0]["status"] == 307
    assert result["exception"] is None
    assert "conformance_label" not in result


def test_capture_exception_is_observation_not_a_verdict():
    class FakeClient:
        def post(self, *args, **kwargs):
            raise RuntimeError("synthetic exception")

    result = m47.collect(FakeClient(), "http://127.0.0.1:8765/redirect")
    assert result["response_status"] is None
    assert result["exception"]["type"] == "RuntimeError"
    assert "conformance_label" not in result


def test_pinned_checkout_rejects_mismatched_source(tmp_path, monkeypatch):
    monkeypatch.setattr(
        m47.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=m47.REVISIONS["before"] + "\n"),
    )
    (tmp_path / "LICENSE").write_text("tampered", encoding="utf-8")
    with pytest.raises(m47.CaptureError, match="Git blob mismatch"):
        m47.verify_checkout(tmp_path, "before")


def test_pinned_checkout_rejects_wrong_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(
        m47.subprocess, "run",
        lambda *args, **kwargs: SimpleNamespace(stdout=m47.REVISIONS["after"] + "\n"),
    )
    with pytest.raises(m47.CaptureError, match="Git HEAD"):
        m47.verify_checkout(tmp_path, "before")


def test_git_blob_hash_is_content_addressed():
    assert m47.git_blob_sha(b"hello") == "b6fc4c620b67d95f953a5c1c1230aaab5db5a1b0"
