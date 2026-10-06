"""設定値の読み込み。パス・接続先・閾値はここ経由で取得し、コードに直接書かない。"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    input_dir: Path
    output_dir: Path
    amount_threshold: int
    log_level: str


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"環境変数 {name} が設定されていません。.env を確認してください")
    return value


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        input_dir=Path(_require("INPUT_DIR")),
        output_dir=Path(_require("OUTPUT_DIR")),
        amount_threshold=int(os.environ.get("AMOUNT_THRESHOLD", "100000000")),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
