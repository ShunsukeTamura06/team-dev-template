"""ファイル同士の食い違いを防ぐテスト。名前やパスを変えたときに、直し漏れがあれば失敗する。"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PLUGIN = ROOT / "plugins" / "team"
TEMPLATE = PLUGIN / "templates" / "tool"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_マーケットプレイスとプラグインが一致する() -> None:
    marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    plugin = load_json(PLUGIN / ".claude-plugin" / "plugin.json")
    entry = marketplace["plugins"][0]
    assert entry["name"] == plugin["name"]
    assert (ROOT / entry["source"]).resolve() == PLUGIN.resolve()


def test_ひな形にチーム共通の設定を写していない() -> None:
    # 共通のものは中央で一元管理する。各ツールに写すと、変更のたびに全リポジトリの修正が要る
    assert not (TEMPLATE / ".claude" / "settings.json").exists()
    assert not (TEMPLATE / "AGENTS.md").exists()
    assert not (TEMPLATE / ".pr_agent.toml").exists()
    assert not (TEMPLATE / "ruff.toml").exists()
    claude_md = (TEMPLATE / "CLAUDE.md").read_text(encoding="utf-8")
    assert "## 1. 構成" not in claude_md


def test_プラグインにバージョンを書かない() -> None:
    # version を書くと、書き換えない限り各PCが更新を受け取らない。省略してコミットごとに更新させる
    assert "version" not in load_json(PLUGIN / ".claude-plugin" / "plugin.json")
    assert "version" not in load_json(ROOT / ".claude-plugin" / "marketplace.json")["plugins"][0]


def test_ひな形のCIが中央のCI定義を参照する() -> None:
    ci = yaml.safe_load((TEMPLATE / ".gitlab-ci.yml").read_text(encoding="utf-8"))
    include = ci["include"][0]
    assert include["project"] == "$TEAM_STANDARDS_PROJECT"
    assert (ROOT / include["file"].lstrip("/")).exists()


def test_フックが参照するスクリプトが存在する() -> None:
    hooks = load_json(PLUGIN / "hooks" / "hooks.json")["hooks"]
    for groups in hooks.values():
        for group in groups:
            for hook in group["hooks"]:
                for arg in hook["args"]:
                    path = arg.replace("${CLAUDE_PLUGIN_ROOT}", str(PLUGIN))
                    assert Path(path).exists(), arg


def test_チーム共通ルールは文脈の上限より十分短い() -> None:
    # フックで渡せる文脈は1万文字まで。超えると先頭2000文字しか渡らない
    assert len((PLUGIN / "rules.md").read_text(encoding="utf-8")) < 8000


def test_ツールのバージョンが固定されている() -> None:
    lines = (PLUGIN / "tool-versions.txt").read_text(encoding="utf-8").split()
    names = {line.split("==")[0] for line in lines if "==" in line}
    assert {"ruff", "pytest"} <= names


def test_各スキルに説明がある() -> None:
    skills = sorted((PLUGIN / "skills").glob("*/SKILL.md"))
    assert len(skills) >= 5
    for skill in skills:
        front = re.match(r"---\n(.*?)\n---\n", skill.read_text(encoding="utf-8"), re.S)
        assert front, skill
        meta = yaml.safe_load(front.group(1))
        assert meta["name"] == skill.parent.name
        assert meta["description"]


def test_設定ファイルが読める() -> None:
    tomllib.loads((ROOT / "pr-agent" / "pr_agent.toml").read_text(encoding="utf-8"))
    tomllib.loads((PLUGIN / "ruff.toml").read_text(encoding="utf-8"))
