"""M45 first-party loopback HTTP fixture for independent Requests #7432 observations.

This server NEVER imports or executes upstream Requests code. It only records
the wire-level HTTP requests sent by an independently approved client runner.
A 307 redirect must preserve POST method and payload. Captured logs are
observations, not adjudicated behavioral labels.
"""
from __future__ import annotations

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

MAX_BODY = 1024 * 1024


def _read_body(handler: BaseHTTPRequestHandler) -> bytes:
    transfer = handler.headers.get("Transfer-Encoding", "").lower()
    if transfer:
        if transfer != "chunked":
            raise ValueError("Unsupported transfer encoding")
        result = bytearray()
        while True:
            line = handler.rfile.readline(64)
            if not line or not line.endswith(b"\r\n"):
                raise ValueError("Invalid chunk header")
            size = int(line.strip().split(b";", 1)[0], 16)
            if size < 0 or len(result) + size > MAX_BODY:
                raise ValueError("Body too large")
            if size == 0:
                # Read trailers, but never allow unbounded input.
                for _ in range(20):
                    trailer = handler.rfile.readline(1024)
                    if trailer == b"\r\n":
                        return bytes(result)
                    if not trailer:
                        raise ValueError("Truncated trailers")
                raise ValueError("Too many trailers")
            chunk = handler.rfile.read(size)
            if len(chunk) != size or handler.rfile.read(2) != b"\r\n":
                raise ValueError("Invalid chunk")
            result.extend(chunk)
    raw_length = handler.headers.get("Content-Length", "0")
    length = int(raw_length)
    if length < 0 or length > MAX_BODY:
        raise ValueError("Invalid body length")
    data = handler.rfile.read(length)
    if len(data) != length:
        raise ValueError("Truncated body")
    return data


def make_handler(observations: list[dict], lock: threading.Lock):
    class RedirectHandler(BaseHTTPRequestHandler):
        server_version = "SRSGuardianFixture/1.0"

        def log_message(self, *_args):
            return

        def do_GET(self):
            if self.path != "/health":
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

        def do_POST(self):
            if self.path not in ("/redirect", "/echo"):
                self.send_error(404)
                return
            try:
                body = _read_body(self)
            except (ValueError, OverflowError):
                self.send_error(400, "Invalid request body")
                return
            observation = {
                "path": self.path,
                "method": "POST",
                "length": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "body_utf8": body.decode("utf-8", errors="replace"),
                "transfer_encoding": self.headers.get("Transfer-Encoding"),
                "content_length": self.headers.get("Content-Length"),
            }
            with lock:
                observations.append(observation)
            if self.path == "/redirect":
                self.send_response(307)
                self.send_header("Location", "/echo")
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                payload = json.dumps(observation, sort_keys=True).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
    return RedirectHandler


def make_server(port: int = 0):
    """Bind only to IPv4 loopback; use port 0 in first-party tests."""
    observations: list[dict] = []
    lock = threading.Lock()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(observations, lock))
    server.daemon_threads = True
    return server, observations, lock


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if not 0 <= args.port <= 65535:
        parser.error("Invalid port")
    if args.output.exists():
        parser.error("Output already exists; choose a fresh path")
    server, observations, lock = make_server(args.port)
    print(f"Loopback fixture: http://127.0.0.1:{server.server_port}/redirect", flush=True)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with lock, args.output.open("x", encoding="utf-8") as handle:
            for row in observations:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        print(f"Saved {len(observations)} wire observations (NOT GOLD) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
