from app.logic import Trade, extract_large_trades


def test_閾値ちょうどは抽出対象に含む() -> None:
    trades = [Trade("A", 99), Trade("B", 100), Trade("C", 101)]
    result = extract_large_trades(trades, threshold=100)
    assert [t.trade_id for t in result] == ["B", "C"]


def test_0件なら空を返す() -> None:
    assert extract_large_trades([], threshold=100) == []
