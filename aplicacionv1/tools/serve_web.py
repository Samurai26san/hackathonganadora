"""Local Flutter Web preview with a same-origin API/SSE proxy (development only)."""
from __future__ import annotations

import argparse
import http.client
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    backend_port = 8000

    def proxy(self) -> None:
        backend = http.client.HTTPConnection("127.0.0.1", self.backend_port, timeout=180)
        size = int(self.headers.get("Content-Length", "0"))
        if size > 20 * 1024 * 1024:
            self.send_error(413)
            return
        headers = {key: value for key, value in self.headers.items() if key.lower() not in {"connection", "transfer-encoding"}}
        try:
            backend.request(self.command, self.path, self.rfile.read(size) if size else None, headers)
            response = backend.getresponse()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in {"transfer-encoding", "connection", "content-length"}:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            while chunk := response.read1(65536):
                self.wfile.write(chunk)
                self.wfile.flush()
            self.close_connection = True
        except (OSError, http.client.HTTPException):
            self.close_connection = True
        finally:
            backend.close()

    def do_GET(self) -> None:
        if self.path.startswith("/api/") or self.path in {"/health", "/ready"}:
            self.proxy()
        else:
            if not Path(self.translate_path(self.path.split("?", 1)[0])).is_file() and self.path != "/":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self) -> None:
        self.proxy()

    do_PUT = do_POST
    do_DELETE = do_POST


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler, directory=str(ROOT / "build/web"))).serve_forever()
