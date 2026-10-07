"""Claude Code がファイルを編集した直後に、チーム共通の設定(ruff.toml)で整形・lint するフック。

- 対象は .py ファイルのみ
- 未使用 import/変数(F401/F841)は編集の途中では正常な状態なので、ここでは扱わない
  (最終的なチェックは /team:self-review と CI で行う)
- 自動修正できない指摘が残った場合は exit 2 で Claude に伝え、修正させる
- ruff が見つからない場合は何もしない(作業を止めない。セッション開始時に警告を出している)
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "ruff.toml"


def ruff_command() -> list[str] | None:
    if shutil.which("ruff"):
        return ["ruff"]
    try:
        subprocess.run([sys.executable, "-m", "ruff", "--version"], capture_output=True, check=True)
        return [sys.executable, "-m", "ruff"]
    except (subprocess.CalledProcessError, OSError):
        return None


def main() -> int:
    sys.stderr.reconfigure(encoding="utf-8")
    payload = json.load(sys.stdin)
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path.endswith(".py"):
        return 0

    ruff = ruff_command()
    if ruff is None:
        return 0

    config = ["--config", str(CONFIG)]
    result = subprocess.run(
        [*ruff, "check", *config, "--fix", "--quiet", "--ignore", "F401,F841", file_path],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    subprocess.run([*ruff, "format", *config, "--quiet", file_path], capture_output=True)
    if result.returncode != 0:
        print(
            f"ruff check で自動修正できない指摘があります。修正してください:\n{result.stdout}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
