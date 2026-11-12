"""Checks resumability and integrity of large model downloads with a tiny server."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import download_models as downloader


class DownloadsTest(unittest.TestCase):
    def setUp(self):
        self.payload = bytes(range(61))
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                start, end = map(int, self.headers["Range"][6:].split("-"))
                owner.requests.append((start, end))
                self.send_response(206)
                self.send_header(
                    "Content-Range", f"bytes {start}-{end}/{len(owner.payload)}"
                )
                self.end_headers()
                self.wfile.write(owner.payload[start : end + 1])

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}/model"
        self.folder = tempfile.TemporaryDirectory()
        self.target = Path(self.folder.name) / "model.gguf"
        self.partial = self.target.with_name("model.gguf.partial")
        self.journal = self.target.with_name("model.gguf.ranges.json")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.folder.cleanup()

    def test_preserves_sequential_prefix_and_completes_parallel_ranges(self):
        self.partial.write_bytes(self.payload[:21])
        with patch.object(downloader, "BLOCK", 16):
            downloader.download(self.url, self.target, len(self.payload), 3)
        self.assertEqual(self.partial.read_bytes(), self.payload)
        self.assertNotIn((0, 15), self.requests)
        self.assertEqual(
            json.loads(self.journal.read_text())["completed"], [0, 1, 2, 3]
        )

    def test_sparse_size_is_not_treated_as_completed_prefix(self):
        self.partial.write_bytes(self.payload[:16] + b"\0" * 32 + self.payload[48:])
        self.journal.write_text(
            json.dumps(
                {
                    "url": self.url,
                    "size": len(self.payload),
                    "block": 16,
                    "completed": [0, 3],
                }
            )
        )
        with patch.object(downloader, "BLOCK", 16):
            downloader.download(self.url, self.target, len(self.payload), 2)
        self.assertEqual(self.partial.read_bytes(), self.payload)
        self.assertEqual(sorted(self.requests), [(16, 31), (32, 47)])

    def test_rejects_checkpoint_from_another_revision(self):
        self.partial.write_bytes(self.payload[:16])
        self.journal.write_text(
            json.dumps(
                {
                    "url": "https://another-revision.invalid",
                    "size": len(self.payload),
                    "block": 16,
                    "completed": [0],
                }
            )
        )
        with patch.object(downloader, "BLOCK", 16), self.assertRaises(SystemExit):
            downloader.download(self.url, self.target, len(self.payload), 2)
        self.assertEqual(self.requests, [])

    def test_migrates_completed_larger_blocks_without_redownloading(self):
        self.partial.write_bytes(self.payload[:32] + b"\0" * 29)
        self.journal.write_text(
            json.dumps(
                {
                    "url": self.url,
                    "size": len(self.payload),
                    "block": 32,
                    "completed": [0],
                }
            )
        )
        with patch.object(downloader, "BLOCK", 16):
            downloader.download(self.url, self.target, len(self.payload), 2)
        self.assertEqual(self.partial.read_bytes(), self.payload)
        self.assertEqual(sorted(self.requests), [(32, 47), (48, 60)])
        self.assertEqual(json.loads(self.journal.read_text())["block"], 16)


if __name__ == "__main__":
    unittest.main()
