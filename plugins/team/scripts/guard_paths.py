"""PreToolUse フック: protected-paths.txt に書かれたパスを、Claude Code が読み書きするのを止める。

各ツールのリポジトリに deny 設定を置かずに済むよう、プラグイン側で一元管理する。
注意: 次は止められない。最終的な防御は .gitignore と運用による。
  - Bash 経由のコマンド(cat など)
  - 範囲を指定しない検索(例: リポジトリ全体への Grep。結果に data/ の中身が含まれうる)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def load_patterns() -> tuple[list[str], list[str]]:
    dirs, names = [], []
    for raw in (PLUGIN_ROOT / "protected-paths.txt").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith("/"):
            dirs.append(line.rstrip("/"))
        else:
            names.append(line)
    return dirs, names


def blocked(target: str, cwd: str) -> str | None:
    base = Path(cwd).resolve()
    path = Path(target)
    path = (path if path.is_absolute() else base / path).resolve()
    try:
        rel = path.relative_to(base)
    except ValueError:
        return None  # リポジトリの外は対象外
    dirs, names = load_patterns()
    rel_posix = rel.as_posix()
    for d in dirs:
        if rel_posix == d or rel_posix.startswith(d + "/"):
            return d + "/"
    if path.name in names:
        return path.name
    return None


def literal_prefix(pattern: str) -> str:
    """glob パターンのうち、ワイルドカードより前の部分(例: "data/**/*.csv" → "data/")。"""
    for i, ch in enumerate(pattern):
        if ch in "*?[{":
            return pattern[:i]
    return pattern


def targets(data: dict) -> list[str]:
    tool_input = data.get("tool_input") or {}
    found = [
        str(tool_input[k]) for k in ("file_path", "path", "notebook_path") if tool_input.get(k)
    ]
    globs = [tool_input.get("glob")]
    if data.get("tool_name") == "Glob":
        globs.append(tool_input.get("pattern"))
    for pattern in globs:
        prefix = literal_prefix(str(pattern)) if pattern else ""
        if prefix.strip("./"):
            found.append(prefix)
    return found


def main() -> int:
    data = json.load(sys.stdin)
    cwd = data.get("cwd") or "."
    for target in targets(data):
        hit = blocked(target, cwd)
        if hit:
            sys.stderr.reconfigure(encoding="utf-8")
            print(
                f"チーム共通ルールにより「{hit}」は読み書きできません(実データ・秘密情報の保護)。"
                "動作確認は tests/fixtures/ のダミーデータで行ってください。",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
