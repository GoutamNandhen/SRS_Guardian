"""First-party loopback tests; NEVER import or execute upstream Requests."""
import hashlib
from http.client import HTTPConnection
import json
import threading

from backend.evaluation.m45_redirect_observation_fixture import make_server


def _request(port, path, body, headers=None):
    connection = HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("POST", path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        return result
    finally:
        connection.close()


def test_307_preserves_redirect_intent_and_echo_records_payload():
    server, observations, lock = make_server()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        port = server.server_port
        status, headers, data = _request(port, "/redirect", b"data")
        assert status == 307
        assert headers["Location"] == "/echo"
        assert data == b""
        status, _, data = _request(port, "/echo", b"data")
        assert status == 200
        echo = json.loads(data)
        assert echo["length"] == 4
        assert echo["body_utf8"] == "data"
        assert echo["sha256"] == hashlib.sha256(b"data").hexdigest()
        with lock:
            assert len(observations) == 2
            assert [x["path"] for x in observations] == ["/redirect", "/echo"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_chunked_body_and_oversize_rejection():
    server, observations, _ = make_server()
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        port = server.server_port
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            conn.request("POST", "/echo", body=[b"da", b"ta"], encode_chunked=True,
                         headers={"Transfer-Encoding": "chunked"})
            resp = conn.getresponse()
            assert resp.status == 200
            assert json.loads(resp.read())["body_utf8"] == "data"
        finally:
            conn.close()
        status, _, _ = _request(port, "/echo", b"", {"Content-Length": "1048577"})
        assert status == 400
        assert len(observations) == 1
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
