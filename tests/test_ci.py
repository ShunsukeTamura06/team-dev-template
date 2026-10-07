"""ci/python-tool.yml に書かれたスクリプトを、そのまま取り出して実行し、動きを確かめる。"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml
from fake_gitlab import FakeGitLab, serve

ROOT = Path(__file__).resolve().parent.parent
CI_FILE = ROOT / "ci" / "python-tool.yml"


class GitLabLoader(yaml.SafeLoader):
    """GitLab 独自の !reference タグを読めるようにする。"""


GitLabLoader.add_constructor("!reference", lambda loader, node: loader.construct_sequence(node))


@pytest.fixture(scope="module")
def ci() -> dict:
    return yaml.load(CI_FILE.read_text(encoding="utf-8"), Loader=GitLabLoader)


def fetch_script(ci: dict) -> str:
    return ci[".team_fetch"]["script"][0]


def bash(script: str, cwd: Path, env: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-eo", "pipefail", "-c", script], cwd=cwd, env=env, capture_output=True, text=True
    )


def test_各ジョブが共通設定の取得を参照している(ci: dict) -> None:
    for job, key in [("lint", "before_script"), ("test", "before_script"), ("ai_review", "script")]:
        assert ci[job][key][0] == [".team_fetch", "script"], job


def test_AIレビューはモデル未登録なら動かない(ci: dict) -> None:
    assert "$AI_REVIEW_MODEL" in ci["ai_review"]["rules"][0]["if"]
    assert ci["ai_review"]["allow_failure"] is True


@pytest.mark.parametrize("ref", [None, "ci-try"])
def test_共通設定の取得(ci: dict, tmp_path: Path, ref: str | None) -> None:
    fake = FakeGitLab(token="bot-token")
    fake.ref = ref or "main"
    project = "grp/team-dev-template"
    for path in [
        "plugins/team/rules.md",
        "plugins/team/ruff.toml",
        "plugins/team/tool-versions.txt",
        "pr-agent/pr_agent.toml",
    ]:
        fake.files[(project, path)] = (ROOT / path).read_bytes()
    url, shutdown = serve(fake)
    try:
        env = {
            **os.environ,
            "CI_API_V4_URL": f"{url}/api/v4",
            "TEAM_STANDARDS_PROJECT": project,
            "TEAM_BOT_TOKEN": "bot-token",
            "CI_PROJECT_DIR": str(tmp_path),
        }
        env.pop("TEAM_STANDARDS_REF", None)
        if ref:
            env["TEAM_STANDARDS_REF"] = ref  # 共通 CI の変更を試すとき(OPERATIONS.md 3-3)
        result = bash(fetch_script(ci), tmp_path, env)
    finally:
        shutdown()
    assert result.returncode == 0, result.stderr
    for name, source in [
        ("rules.md", "plugins/team/rules.md"),
        ("ruff.toml", "plugins/team/ruff.toml"),
        ("tool-versions.txt", "plugins/team/tool-versions.txt"),
        ("pr_agent.toml", "pr-agent/pr_agent.toml"),
    ]:
        assert (tmp_path / ".team" / name).read_bytes() == (ROOT / source).read_bytes()


def test_取得するファイルはすべてリポジトリに存在する(ci: dict) -> None:
    for line in fetch_script(ci).splitlines():
        line = line.strip().rstrip(",").strip('"')
        if line.startswith(("plugins/", "pr-agent/")):
            assert (ROOT / line).exists(), line


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """ルールに合わない既存コードを持つツールのリポジトリ。"""
    repo = tmp_path / "tool"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "legacy.py").write_text("import os,sys\ndef old( x ):\n  return x\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "legacy")
    (repo / ".team").mkdir()
    shutil.copy(ROOT / "plugins" / "team" / "ruff.toml", repo / ".team" / "ruff.toml")
    return repo


def run_lint(ci: dict, repo: Path, base: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "CI_MERGE_REQUEST_DIFF_BASE_SHA": base}
    return bash(ci["lint"]["script"][0], repo, env)


def test_lintはMRで変更したファイルだけを確認する(ci: dict, repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "新しい 処理.py").write_text("def new(x: int) -> int:\n    return x\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "add")
    result = run_lint(ci, repo, base)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "新しい 処理.py" in result.stdout
    assert "legacy.py" not in result.stdout


def test_lintは変更したファイルの違反で失敗する(ci: dict, repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "legacy.py").write_text("import os,sys\ndef old( x ):\n  return x\n\n# 追記\n")
    git(repo, "commit", "-q", "-am", "touch legacy")
    assert run_lint(ci, repo, base).returncode != 0


def test_lintは対象が無ければ成功する(ci: dict, repo: Path) -> None:
    base = git(repo, "rev-parse", "HEAD")
    (repo / "README.md").write_text("doc\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "doc")
    result = run_lint(ci, repo, base)
    assert result.returncode == 0
    assert "変更された .py ファイルはありません" in result.stdout


@pytest.mark.parametrize(
    ("tests", "ok"),
    [
        ({}, True),
        ({"test_a.py": "def test_a():\n    assert True\n"}, True),
        ({"test_b.py": "def test_b():\n    assert False\n"}, False),
    ],
)
def test_testジョブはテスト0件を成功扱いにする(
    ci: dict, tmp_path: Path, tests: dict, ok: bool
) -> None:
    for name, body in tests.items():
        (tmp_path / name).write_text(body)
    result = bash(ci["test"]["script"][-1], tmp_path, dict(os.environ))
    assert (result.returncode == 0) is ok
