"""テスト用の偽 GitLab API サーバー。必要な API だけを持つ。"""

from __future__ import annotations

import json
import threading
import urllib.parse
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer

Handler = Callable[[str, str, dict | None, dict], tuple[int, object | bytes]]


class FakeGitLab:
    def __init__(self, token: str = "test-token") -> None:
        self.token = token
        self.calls: list[tuple[str, str, dict | None]] = []
        self.projects: dict[str, dict] = {}
        self.files: dict[tuple[str, str], bytes] = {}
        self.ref = "main"  # ファイルを返すブランチ

    def add_project(self, path: str) -> dict:
        self.projects[path] = {"protected": None, "pipeline_required": False}
        return self.projects[path]

    def handle(self, method: str, raw_path: str, body: dict | None) -> tuple[int, object | bytes]:
        self.calls.append((method, raw_path, body))
        path, _, query = raw_path.partition("?")
        parts = path.removeprefix("/api/v4/projects/").split("/")
        name = urllib.parse.unquote(parts[0])
        rest = parts[1:]

        if rest[:2] == ["repository", "files"] and method == "GET":
            file_path = urllib.parse.unquote(rest[2])
            key = (name, file_path)
            if rest[3:] == ["raw"] and query == f"ref={self.ref}" and key in self.files:
                return 200, self.files[key]
            return 404, {"message": "404 File Not Found"}

        project = self.projects.get(name)
        if project is None:
            return 404, {"message": "404 Project Not Found"}
        if not rest:
            if method == "GET":
                return 200, {"id": 1}
            if method == "PUT":
                project["pipeline_required"] = body["only_allow_merge_if_pipeline_succeeds"]
                return 200, {"id": 1}
        if rest[:1] == ["protected_branches"]:
            if method == "DELETE":
                existed = project["protected"] is not None
                project["protected"] = None
                return (204, None) if existed else (404, {"message": "404 Not found"})
            if method == "POST":
                project["protected"] = body
                return 201, body
        return 400, {"message": f"unexpected {method} {raw_path}"}


def serve(fake: FakeGitLab) -> tuple[str, Callable[[], None]]:
    class Handler(BaseHTTPRequestHandler):
        def _serve(self) -> None:
            if self.headers.get("PRIVATE-TOKEN") != fake.token:
                status, payload = 401, {"message": "401 Unauthorized"}
            else:
                length = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                status, payload = fake.handle(self.command, self.path, body)
            if isinstance(payload, bytes):
                raw = payload
            else:
                raw = b"" if payload is None else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        do_GET = do_POST = do_PUT = do_DELETE = _serve

        def log_message(self, *args: object) -> None:
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_port}", httpd.shutdown
