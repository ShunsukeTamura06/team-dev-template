"""Claude Code がファイルを編集した直後に ruff で整形・lint する hook。

- 対象は .py ファイルのみ
- 自動修正できない lint エラーが残った場合は exit 2 で Claude に伝え、修正させる
- ruff が見つからない場合は何もしない(作業を止めない)
"""

import json
import shutil
import subprocess
import sys


def ruff_command() -> list[str] | None:
    if shutil.which("ruff"):
        return ["ruff"]
    try:
        subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            capture_output=True,
            check=True,
        )
        return [sys.executable, "-m", "ruff"]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def main() -> int:
    payload = json.load(sys.stdin)
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path.endswith(".py"):
        return 0

    ruff = ruff_command()
    if ruff is None:
        print("ruff が見つからないため整形をスキップしました", file=sys.stderr)
        return 0

    # 未使用import/変数(F401/F841)は編集の途中では正常な状態なので、ここでは扱わない。
    # 最終的なチェックは /self-review と CI の ruff で行う。
    result = subprocess.run(
        [*ruff, "check", "--fix", "--quiet", "--ignore", "F401,F841", file_path],
        capture_output=True,
        text=True,
    )
    subprocess.run([*ruff, "format", "--quiet", file_path], capture_output=True)
    if result.returncode != 0:
        print(
            f"ruff check で自動修正できない指摘があります。修正してください:\n{result.stdout}",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
