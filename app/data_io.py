"""外部との読み書き(Excel・CSV・DB・フォルダ)。業務判定はここに書かない。"""

import csv
import logging
from pathlib import Path

from app.logic import Trade

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = ("trade_id", "amount")


def read_trades(path: Path) -> list[Trade]:
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルがありません: {path}")

    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} に必要な列がありません: {missing}")

        trades: list[Trade] = []
        for line_no, row in enumerate(reader, start=2):
            try:
                trades.append(Trade(trade_id=row["trade_id"], amount=int(row["amount"])))
            except ValueError:
                logger.warning("金額が数値でない行をスキップしました: %s 行%d", path.name, line_no)
    return trades


def write_trades(path: Path, trades: list[Trade]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(REQUIRED_COLUMNS)
        for trade in trades:
            writer.writerow([trade.trade_id, trade.amount])
