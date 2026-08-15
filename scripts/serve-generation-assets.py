#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


MAX_WEBHOOK_BYTES = 64 * 1024 * 1024


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--root", required=True)
    result.add_argument("--webhook-path", required=True)
    result.add_argument("--webhook-output", required=True)
    result.add_argument("--host", default="0.0.0.0")
    result.add_argument("--port", type=int, default=8000)
    return result


def handler_factory(root: Path, webhook_path: str, webhook_output: Path):
    if not webhook_path.startswith("/") or webhook_path == "/":
        raise ValueError("webhook path must be a non-root absolute path")
    root = root.resolve()
    webhook_output = webhook_output.resolve()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def list_directory(self, path):
            self.send_error(403, "directory listing disabled")
            return None

        def do_POST(self):
            if self.path != webhook_path:
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "-1"))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_WEBHOOK_BYTES:
                self.send_error(413)
                return
            raw = self.rfile.read(length)
            try:
                packet = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_error(400)
                return
            if not isinstance(packet, dict) or not packet.get("request_id"):
                self.send_error(422)
                return
            if webhook_output.exists():
                self.send_error(409)
                return
            webhook_output.parent.mkdir(parents=True, exist_ok=True)
            partial = webhook_output.with_suffix(webhook_output.suffix + ".partial")
            partial.write_text(
                json.dumps(packet, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.chmod(partial, 0o600)
            partial.replace(webhook_output)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok\n")

        def log_message(self, format, *args):
            print(f"generation-asset-server: {self.command} {self.path} {args[1]}")

    return Handler


def main() -> int:
    args = parser().parse_args()
    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit("asset root does not exist")
    server = ThreadingHTTPServer(
        (args.host, args.port),
        handler_factory(root, args.webhook_path, Path(args.webhook_output)),
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
