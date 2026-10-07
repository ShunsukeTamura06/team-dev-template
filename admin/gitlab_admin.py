"""チーム標準を導入したツールの GitLab プロジェクトに、マージの決まりを設定する管理用スクリプト。

設定する内容:
  - main ブランチの保護
    (直接 push は誰もできない / MR からのマージは Developer 以上 / 強制 push は禁止)
    中央リポジトリ(team-dev-template)には --merge-level maintainer を付け、
    マージできる人を Maintainer(チーフ)に限る
  - マージの条件(パイプラインが成功していないとマージできない)

使う人: 対象プロジェクトの Maintainer 以上の権限を持つ人(推進担当)
使う場所: 自分の PC で、社内 GitLab の team-dev-template を clone したフォルダ

準備(最初に1回):
    自分の GitLab アカウントで個人アクセストークン(スコープ: api)を作り、環境変数に入れる。
    Windows(PowerShell):
        $env:GITLAB_URL = "https://gitlab.example.local"
        $env:GITLAB_TOKEN = "glpat-..."

使い方(プロジェクトは「グループ名/プロジェクト名」で、いくつでも並べられる):
    python admin/gitlab_admin.py protect my-group/bond-reconcile --dry-run   # 内容の確認だけ
    python admin/gitlab_admin.py protect my-group/bond-reconcile             # 実行
    python admin/gitlab_admin.py protect my-group/team-dev-template --merge-level maintainer
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

NO_ONE = 0
DEVELOPER = 30  # 「Developers + Maintainers」
MAINTAINER = 40  # 「Maintainers」
MERGE_LEVELS = {
    "developer": (DEVELOPER, "Developers + Maintainers"),
    "maintainer": (MAINTAINER, "Maintainers"),
}


def settings(merge_level: str) -> list[str]:
    label = MERGE_LEVELS[merge_level][1]
    return [
        f"main: 直接push=No one / マージ={label} / 強制push=禁止",
        "マージ条件: パイプライン成功が必須",
    ]


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


def _check(status: int, payload: object, action: str, ok: tuple[int, ...]) -> None:
    if status not in ok:
        raise GitLabError(f"{action} に失敗しました (HTTP {status}): {payload}")


def protect(gl: GitLab, project: str, merge_level: str = "developer") -> None:
    ref = urllib.parse.quote(project, safe="")

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
            "merge_access_level": MERGE_LEVELS[merge_level][0],
            "allow_force_push": False,
        },
    )
    _check(status, payload, "main の保護", (201,))

    status, payload = gl.request(
        "PUT", f"/projects/{ref}", {"only_allow_merge_if_pipeline_succeeds": True}
    )
    _check(status, payload, "「パイプライン成功が必須」の設定", (200,))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("protect", help="main ブランチの保護とマージ条件を設定する")
    p.add_argument("projects", nargs="+", help="対象プロジェクト(例: my-group/bond-reconcile)")
    p.add_argument(
        "--merge-level",
        choices=sorted(MERGE_LEVELS),
        default="developer",
        help="マージできる人(既定: developer。中央リポジトリには maintainer)",
    )
    p.add_argument("--dry-run", action="store_true", help="変更せずに内容だけ表示する")
    args = parser.parse_args(argv)

    if args.dry_run:
        for project in args.projects:
            print(f"[予定] {project}")
            for line in settings(args.merge_level):
                print(f"       {line}")
        print("\n(--dry-run のため、実際には何も変更していません)")
        return 0

    url, token = os.environ.get("GITLAB_URL"), os.environ.get("GITLAB_TOKEN")
    if not url or not token:
        print("環境変数 GITLAB_URL と GITLAB_TOKEN を設定してください", file=sys.stderr)
        return 1
    gl = GitLab(url, token)

    failed = 0
    for project in args.projects:
        try:
            protect(gl, project, args.merge_level)
            print(f"[OK] {project}")
            for line in settings(args.merge_level):
                print(f"     {line}")
        except GitLabError as e:
            failed += 1
            print(f"[NG] {project}: {e}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
