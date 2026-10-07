"""プラグインのフック(scripts/)を、Claude Code と同じ形(stdin に JSON)で実行して確かめる。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "plugins" / "team" / "scripts"
RULES = ROOT / "plugins" / "team" / "rules.md"


def run(script: str, payload: dict, env: dict | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        input=json.dumps(payload).encode(),
        capture_output=True,
        env=env,
    )


def fake_ruff_env(tmp_path: Path, version: str, auto_update: bool = True) -> dict:
    """指定のバージョンを名乗る偽の ruff と、Claude Code のユーザー設定を用意した環境を作る。"""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ruff = bin_dir / "ruff"
    ruff.write_text(f"#!/bin/sh\necho 'ruff {version}'\n")
    ruff.chmod(0o755)
    config = tmp_path / "claude-config"
    config.mkdir()
    marketplace = {"source": {"source": "git", "url": "u"}, "autoUpdate": auto_update}
    (config / "settings.json").write_text(
        json.dumps({"extraKnownMarketplaces": {"team-dev": marketplace}}), encoding="utf-8"
    )
    return {
        **os.environ,
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "CLAUDE_CONFIG_DIR": str(config),
    }


def test_セッション開始時にチーム共通ルールが文脈に入る() -> None:
    result = run("session_start.py", {"hook_event_name": "SessionStart", "source": "startup"})
    assert result.returncode == 0
    assert result.stdout.isascii()  # Windows の文字コードに左右されない
    output = json.loads(result.stdout)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert RULES.read_text(encoding="utf-8") in context


def test_設定が整っていれば警告しない(tmp_path: Path) -> None:
    expected = "0.16.10"
    result = run("session_start.py", {}, env=fake_ruff_env(tmp_path, expected))
    assert "systemMessage" not in json.loads(result.stdout)


def test_ruffのバージョンが違えば警告する(tmp_path: Path) -> None:
    result = run("session_start.py", {}, env=fake_ruff_env(tmp_path, "0.1.0"))
    message = json.loads(result.stdout)["systemMessage"]
    assert "0.1.0" in message
    assert "/team:setup" in message


def test_自動更新が無効なら警告する(tmp_path: Path) -> None:
    env = fake_ruff_env(tmp_path, "0.16.10", auto_update=False)
    message = json.loads(run("session_start.py", {}, env=env).stdout)["systemMessage"]
    assert "自動更新" in message
    assert "/team:setup" in message


@pytest.fixture
def py_file(tmp_path: Path):
    def make(name: str, body: str) -> Path:
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        return path

    return make


def test_編集後に整形される(py_file) -> None:
    path = py_file("a.py", "import sys\ndef g( a ):\n  return a\n")
    result = run("ruff_after_edit.py", {"tool_input": {"file_path": str(path)}})
    assert result.returncode == 0
    # 未使用 import は編集途中の正常な状態なので消さない
    assert path.read_text() == "import sys\n\n\ndef g(a):\n    return a\n"


def test_自動修正できない指摘はexit2でClaudeに返す(py_file) -> None:
    path = py_file("b.py", "def f():\n    return undefined_name\n")
    result = run("ruff_after_edit.py", {"tool_input": {"file_path": str(path)}})
    assert result.returncode == 2
    assert "undefined_name" in result.stderr.decode("utf-8")


def test_py以外は対象外(py_file) -> None:
    path = py_file("c.md", "# memo\n")
    result = run("ruff_after_edit.py", {"tool_input": {"file_path": str(path)}})
    assert result.returncode == 0


@pytest.mark.parametrize(
    ("tool", "key", "target", "ok"),
    [
        ("Read", "file_path", ".env", False),
        ("Read", "file_path", "sub/.env", False),
        ("Read", "file_path", ".env.example", True),
        ("Read", "file_path", "data/2026-10 明細.xlsx", False),
        ("Write", "file_path", "output/result.csv", False),
        ("Grep", "path", "data", False),
        ("Glob", "path", "./output/", False),
        ("Read", "file_path", "app/data_io.py", True),
        ("Read", "file_path", "tests/fixtures/trades.csv", True),
        ("Grep", "path", "..", True),
        ("Grep", "glob", "data/**/*.csv", False),
        ("Grep", "glob", "*.py", True),
        ("Glob", "pattern", "output/*.xlsx", False),
        ("Glob", "pattern", "**/*.py", True),
        ("Glob", "pattern", ".env", False),
    ],
)
def test_実データと秘密情報は読み書きさせない(
    tmp_path: Path, tool: str, key: str, target: str, ok: bool
) -> None:
    payload = {"tool_name": tool, "tool_input": {key: target}, "cwd": str(tmp_path)}
    result = run("guard_paths.py", payload)
    assert (result.returncode == 0) is ok, result.stderr.decode()


def test_絶対パスでも止める(tmp_path: Path) -> None:
    payload = {"tool_input": {"file_path": str(tmp_path / "data" / "x.csv")}, "cwd": str(tmp_path)}
    result = run("guard_paths.py", payload)
    assert result.returncode == 2
    assert "data/" in result.stderr.decode("utf-8")


def test_初期設定で自動更新が有効になる(tmp_path: Path) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "extraKnownMarketplaces": {"team-dev": {"source": {"source": "git", "url": "u"}}},
                "enabledPlugins": {"team@team-dev": True},
                "model": "x",
            }
        ),
        encoding="utf-8",
    )
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(tmp_path)}
    cmd = [sys.executable, str(SCRIPTS / "setup_pc.py"), "--skip-pip"]
    first = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stdout
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["extraKnownMarketplaces"]["team-dev"]["autoUpdate"] is True
    assert data["model"] == "x"  # 他の設定は消さない
    second = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert "すでに有効" in second.stdout


def test_マーケットプレイス未登録なら初期設定は失敗する(tmp_path: Path) -> None:
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(tmp_path)}
    cmd = [sys.executable, str(SCRIPTS / "setup_pc.py"), "--skip-pip"]
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert "marketplace add" in result.stdout
