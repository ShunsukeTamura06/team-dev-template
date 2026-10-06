"""業務判定・計算。ファイルやDBには触らない(テストしやすくするため)。

サンプル: 金額が閾値以上の明細を抽出する。実際の業務ロジックに置き換えて使う。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Trade:
    trade_id: str
    amount: int


def extract_large_trades(trades: list[Trade], threshold: int) -> list[Trade]:
    """金額が閾値「以上」の明細を返す(閾値ちょうどを含む)。"""
    return [trade for trade in trades if trade.amount >= threshold]
