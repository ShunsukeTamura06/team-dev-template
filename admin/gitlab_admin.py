"""テンプレート導入済みのGitLabプロジェクトを一括で設定・更新する管理用スクリプト。

使う人: GitLabグループのMaintainer以上の権限を持つ人(チーフなど)
使う場所: 自分のPCで、社内GitLabの team-dev-template を clone したフォルダ

準備(最初に1回):
    自分のGitLabアカウントで「個人アクセストークン」(スコープ: api)を発行し、環境変数に入れる。
    Windows(PowerShell):
        $env:GITLAB_URL = "https://gitlab.example.local"
        $env:GITLAB_TOKEN = "glpat-..."

コマンド:
    # main ブランチの保護 + 「パイプライン成功が必須」を設定する
    python admin/gitlab_admin.py protect --dry-run      # 何が変わるかを表示するだけ
    python admin/gitlab_admin.py protect                # 実行する

    # AGENTS.md と .pr_agent.toml の最新版を、各プロジェクトへMRとして配る
    python admin/gitlab_admin.py sync-rules --dry-run
    python admin/gitlab_admin.py sync-rules

対象プロジェクトは admin/projects.txt に1行1つ書く(例: my-group/bond-reconcile)。
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECTS_FILE = Path(__file__).resolve().parent / "projects.txt"
DEFAULT_SYNC_FILES = ["AGENTS.md", ".pr_agent.toml"]

NO_ONE = 0
DEVELOPER = 30  # 「Developers + Maintainers」


class GitLabError(RuntimeError):
    pass


class GitLab:
    def __init__(self, url: str, token: str) -> None:
        self.api = url.rstrip("/") + "/api/v4"
        self.token = token

    def request(self, method: str, path: str, body: dict | None = None) -> tuple[int, object]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.api + path, data=data, method=method)
        req.add_header("PRIVATE-TOKEN", self.token)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                raw = res.read()
                return res.status, json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw) if raw else None
            except ValueError:
                payload = raw.decode(errors="replace")
            return e.code, payload


def project_ref(path: str) -> str:
    return urllib.parse.quote(path, safe="")


def read_projects(file: Path) -> list[str]:
    if not file.exists():
        raise SystemExit(f"{file} がありません。対象プロジェクトを1行1つで書いてください")
    lines = [line.strip() for line in file.read_text(encoding="utf-8").splitlines()]
    projects = [line for line in lines if line and not line.startswith("#")]
    if not projects:
        raise SystemExit(f"{file} に対象プロジェクトが書かれていません")
    return projects


def _check(status: int, payload: object, action: str, ok: tuple[int, ...]) -> None:
    if status not in ok:
        raise GitLabError(f"{action} に失敗しました (HTTP {status}): {payload}")


def protect(gl: GitLab, project: str, dry_run: bool) -> list[str]:
    """main を保護し(直接push禁止・MRマージは全員可)、パイプライン成功を必須にする。"""
    ref = project_ref(project)
    done = [
        "main: 直接push=No one / マージ=Developers + Maintainers / 強制push=禁止",
        "マージ条件: パイプライン成功が必須",
    ]
    if dry_run:
        return done

    status, payload = gl.request("GET", f"/projects/{ref}")
    _check(status, payload, f"{project} の取得", (200,))

    # 既存の設定があれば外してから付け直す(設定値を確実にそろえるため)
    status, payload = gl.request("DELETE", f"/projects/{ref}/protected_branches/main")
    _check(status, payload, "既存の main 保護の解除", (204, 404))

    status, payload = gl.request(
        "POST",
        f"/projects/{ref}/protected_branches",
        {
            "name": "main",
            "push_access_level": NO_ONE,
            "merge_access_level": DEVELOPER,
            "allow_force_push": False,
        },
    )
    _check(status, payload, "main の保護", (201,))

    status, payload = gl.request(
        "PUT", f"/projects/{ref}", {"only_allow_merge_if_pipeline_succeeds": True}
    )
    _check(status, payload, "「パイプライン成功が必須」の設定", (200,))
    return done


def _remote_file(gl: GitLab, ref: str, file_path: str) -> str | None:
    encoded = urllib.parse.quote(file_path, safe="")
    status, payload = gl.request("GET", f"/projects/{ref}/repository/files/{encoded}?ref=main")
    if status == 404:
        return None
    _check(status, payload, f"{file_path} の取得", (200,))
    assert isinstance(payload, dict)
    return base64.b64decode(payload["content"]).decode("utf-8")


def sync_rules(gl: GitLab, project: str, files: list[str], dry_run: bool) -> list[str]:
    """テンプレートの最新ファイルと違うものだけを、新しいブランチにコミットしてMRを作る。"""
    ref = project_ref(project)
    actions = []
    for file_path in files:
        local = (REPO_ROOT / file_path).read_text(encoding="utf-8")
        remote = _remote_file(gl, ref, file_path)
        if remote == local:
            continue
        actions.append(
            {
                "action": "create" if remote is None else "update",
                "file_path": file_path,
                "content": local,
            }
        )

    if not actions:
        return ["変更なし(すでに最新)"]
    changed = [f"{a['action']}: {a['file_path']}" for a in actions]
    if dry_run:
        return changed

    branch = f"update-team-rules-{dt.datetime.now():%Y%m%d-%H%M%S}"
    status, payload = gl.request(
        "POST",
        f"/projects/{ref}/repository/commits",
        {
            "branch": branch,
            "start_branch": "main",
            "commit_message": "チーム共通ルールを最新版に更新",
            "actions": actions,
        },
    )
    _check(status, payload, "更新コミットの作成", (201,))

    status, payload = gl.request(
        "POST",
        f"/projects/{ref}/merge_requests",
        {
            "source_branch": branch,
            "target_branch": "main",
            "title": "チーム共通ルールを最新版に更新",
            "description": "team-dev-template の最新版を反映するMRです。\n\n"
            + "\n".join(f"- {c}" for c in changed),
            "remove_source_branch": True,
        },
    )
    _check(status, payload, "MRの作成", (201,))
    assert isinstance(payload, dict)
    return [*changed, f"MR: {payload.get('web_url')}"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("protect", "sync-rules"):
        p = sub.add_parser(name)
        p.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS_FILE)
        p.add_argument("--dry-run", action="store_true", help="変更せずに内容だけ表示する")
        if name == "sync-rules":
            p.add_argument("--file", action="append", dest="files", help="配るファイル(複数可)")
    args = parser.parse_args(argv)

    url, token = os.environ.get("GITLAB_URL"), os.environ.get("GITLAB_TOKEN")
    if not url or not token:
        print("環境変数 GITLAB_URL と GITLAB_TOKEN を設定してください", file=sys.stderr)
        return 1
    gl = GitLab(url, token)

    failed = 0
    for project in read_projects(args.projects):
        try:
            if args.command == "protect":
                results = protect(gl, project, args.dry_run)
            else:
                results = sync_rules(gl, project, args.files or DEFAULT_SYNC_FILES, args.dry_run)
            print(f"[OK] {project}")
            for line in results:
                print(f"     {line}")
        except GitLabError as e:
            failed += 1
            print(f"[NG] {project}: {e}", file=sys.stderr)

    if args.dry_run:
        print("\n(--dry-run のため、実際には何も変更していません)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
