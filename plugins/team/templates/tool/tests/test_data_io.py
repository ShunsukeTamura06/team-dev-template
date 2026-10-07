from pathlib import Path

import pytest
from app.data_io import read_trades

FIXTURES = Path(__file__).parent / "fixtures"


def test_ダミーデータを読み込める() -> None:
    trades = read_trades(FIXTURES / "trades.csv")
    assert len(trades) == 3


def test_必要な列が無ければ原因が分かるエラーで止まる(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("id,amount\n1,100\n", encoding="utf-8")
    with pytest.raises(ValueError, match="trade_id"):
        read_trades(path)
