"""セッション開始時に、チーム共通ルールを Claude Code に読み込ませるフック。

- rules.md の内容を Claude の文脈に追加する(開始・再開・/clear・圧縮後のすべてで実行される)
- 手元の ruff のバージョンがチーム指定(tool-versions.txt)と違う、または自動更新が無効なら、
  ユーザーに /team:setup の実行を促す

出力は ASCII だけの JSON にする(Windows の文字コードの影響を受けないため)。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from setup_pc import MARKETPLACE, settings_path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent


def expected_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in (PLUGIN_ROOT / "tool-versions.txt").read_text(encoding="utf-8").splitlines():
        name, sep, version = line.strip().partition("==")
        if sep:
            versions[name.strip()] = version.strip()
    return versions


def installed_ruff_version() -> str | None:
    commands = [[sys.executable, "-m", "ruff", "--version"]]
    if shutil.which("ruff"):
        commands.insert(0, ["ruff", "--version"])
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.split()[-1]
    return None


def auto_update_enabled() -> bool:
    try:
        settings = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    entry = settings.get("extraKnownMarketplaces", {}).get(MARKETPLACE, {})
    return entry.get("autoUpdate") is True


def build_output() -> dict:
    rules = (PLUGIN_ROOT / "rules.md").read_text(encoding="utf-8")
    output: dict = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": (
                "以下は、このチームの全リポジトリに適用されるチーム共通ルールです"
                "(配布元: Claude Code プラグイン team)。作業ではこれに従ってください。\n\n" + rules
            ),
        }
    }

    warnings = []
    expected = expected_versions().get("ruff")
    installed = installed_ruff_version()
    if expected and installed != expected:
        found = f"手元は {installed}" if installed else "手元に見つかりません"
        warnings.append(f"ruff のバージョンがチーム指定({expected})と違います({found})。")
    if not auto_update_enabled():
        warnings.append("チーム標準(プラグイン team)の自動更新が有効になっていません。")
    if warnings:
        output["systemMessage"] = "".join(warnings) + "/team:setup を実行してください。"
    return output


def main() -> int:
    try:
        json.load(sys.stdin)
    except ValueError:
        pass
    print(json.dumps(build_output()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
