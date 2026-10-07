"""gitlab_admin.py のテスト。偽のGitLab APIサーバーを立てて、実際のHTTP通信まで確認する。

実行: pytest admin
"""

from __future__ import annotations

import base64
import json
import sys
import threading
import urllib.parse
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitlab_admin  # noqa: E402


class FakeGitLab:
    """必要なAPIだけを持つ、メモリ上のGitLab。"""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []
        self.projects = {"grp/tool-a": {"files": {}, "protected": None, "pipeline_required": False}}
        self.mrs: list[dict] = []

    def handle(self, method: str, raw_path: str, body: dict | None) -> tuple[int, object]:
        self.calls.append((method, raw_path, body))
        path, _, query = raw_path.partition("?")
        parts = path.removeprefix("/api/v4/projects/").split("/")
        project = self.projects.get(urllib.parse.unquote(parts[0]))
        if project is None:
            return 404, {"message": "404 Project Not Found"}
        rest = parts[1:]

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
        if rest[:2] == ["repository", "files"] and method == "GET":
            name = urllib.parse.unquote(rest[2])
            assert query == "ref=main"
            if name not in project["files"]:
                return 404, {"message": "404 File Not Found"}
            return 200, {"content": base64.b64encode(project["files"][name].encode()).decode()}
        if rest[:2] == ["repository", "commits"] and method == "POST":
            assert body["start_branch"] == "main"
            return 201, {"id": "abc"}
        if rest[:1] == ["merge_requests"] and method == "POST":
            self.mrs.append(body)
            return 201, {"web_url": "http://gitlab.local/grp/tool-a/-/merge_requests/1"}
        return 400, {"message": f"unexpected {method} {raw_path}"}


@pytest.fixture
def server() -> Iterator[tuple[str, FakeGitLab]]:
    fake = FakeGitLab()

    class Handler(BaseHTTPRequestHandler):
        def _serve(self) -> None:
            assert self.headers["PRIVATE-TOKEN"] == "test-token"
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length)) if length else None
            status, payload = fake.handle(self.command, self.path, body)
            raw = b"" if payload is None else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        do_GET = do_POST = do_PUT = do_DELETE = _serve

        def log_message(self, *args: object) -> None:
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}", fake
    httpd.shutdown()


@pytest.fixture
def projects_file(tmp_path: Path) -> Path:
    path = tmp_path / "projects.txt"
    path.write_text("# コメント\n\ngrp/tool-a\n", encoding="utf-8")
    return path


@pytest.fixture
def env(server: tuple[str, FakeGitLab], monkeypatch: pytest.MonkeyPatch) -> FakeGitLab:
    url, fake = server
    monkeypatch.setenv("GITLAB_URL", url)
    monkeypatch.setenv("GITLAB_TOKEN", "test-token")
    return fake


def test_protectでmain保護とパイプライン必須が設定される(
    env: FakeGitLab, projects_file: Path
) -> None:
    rc = gitlab_admin.main(["protect", "--projects", str(projects_file)])
    project = env.projects["grp/tool-a"]
    assert rc == 0
    assert project["protected"] == {
        "name": "main",
        "push_access_level": 0,
        "merge_access_level": 30,
        "allow_force_push": False,
    }
    assert project["pipeline_required"] is True


def test_protectは既存の保護設定があっても付け直す(env: FakeGitLab, projects_file: Path) -> None:
    env.projects["grp/tool-a"]["protected"] = {"name": "main", "push_access_level": 40}
    assert gitlab_admin.main(["protect", "--projects", str(projects_file)]) == 0
    assert env.projects["grp/tool-a"]["protected"]["push_access_level"] == 0


def test_dry_runでは何も変更しない(env: FakeGitLab, projects_file: Path) -> None:
    assert gitlab_admin.main(["protect", "--dry-run", "--projects", str(projects_file)]) == 0
    assert env.calls == []


def test_sync_rulesは差分があるファイルだけMRにする(env: FakeGitLab, projects_file: Path) -> None:
    agents = (gitlab_admin.REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    env.projects["grp/tool-a"]["files"] = {
        "AGENTS.md": agents
    }  # AGENTS.md は最新、.pr_agent.toml は無い

    assert gitlab_admin.main(["sync-rules", "--projects", str(projects_file)]) == 0
    commit = next(c for c in env.calls if c[1].endswith("/repository/commits"))
    assert [(a["action"], a["file_path"]) for a in commit[2]["actions"]] == [
        ("create", ".pr_agent.toml")
    ]
    assert env.mrs[0]["target_branch"] == "main"


def test_sync_rulesは全て最新ならMRを作らない(env: FakeGitLab, projects_file: Path) -> None:
    env.projects["grp/tool-a"]["files"] = {
        name: (gitlab_admin.REPO_ROOT / name).read_text(encoding="utf-8")
        for name in gitlab_admin.DEFAULT_SYNC_FILES
    }
    assert gitlab_admin.main(["sync-rules", "--projects", str(projects_file)]) == 0
    assert env.mrs == []


def test_存在しないプロジェクトは失敗として報告する(
    env: FakeGitLab, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "projects.txt"
    path.write_text("grp/unknown\n", encoding="utf-8")
    assert gitlab_admin.main(["protect", "--projects", str(path)]) == 1
    assert "[NG] grp/unknown" in capsys.readouterr().err


def test_環境変数が無ければ止まる(monkeypatch: pytest.MonkeyPatch, projects_file: Path) -> None:
    monkeypatch.delenv("GITLAB_URL", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    assert gitlab_admin.main(["protect", "--projects", str(projects_file)]) == 1
