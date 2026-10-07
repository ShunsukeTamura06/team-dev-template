"""各自の PC の初期設定(/team:setup から呼ばれる)。何度実行しても同じ結果になる。

1. Claude Code のユーザー設定で、マーケットプレイス team-dev の自動更新を有効にする
2. チーム共通のバージョンの ruff と pytest を入れる
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = "team-dev"


def settings_path() -> Path:
    base = os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"
    return Path(base) / "settings.json"


def enable_auto_update(path: Path) -> str:
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    entry = settings.get("extraKnownMarketplaces", {}).get(MARKETPLACE)
    if entry is None:
        return (
            f"[NG] {path} に {MARKETPLACE} がありません。"
            "先に `claude plugin marketplace add <URL>` を実行してください"
        )
    if entry.get("autoUpdate") is True:
        return f"[OK] 自動更新はすでに有効です({path})"
    entry["autoUpdate"] = True
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"[OK] 自動更新を有効にしました({path})"


def install_tools() -> str:
    req = PLUGIN_ROOT / "tool-versions.txt"
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"[NG] ruff / pytest のインストールに失敗しました:\n{result.stderr[-1500:]}"
    pinned = req.read_text(encoding="utf-8").split()
    return "[OK] インストール済み: " + ", ".join(pinned)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    lines = [enable_auto_update(settings_path())]
    if "--skip-pip" not in argv:
        lines.append(install_tools())
    print("\n".join(lines))
    return 1 if any(line.startswith("[NG]") for line in lines) else 0


if __name__ == "__main__":
    sys.exit(main())
