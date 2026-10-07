"""入口。処理の呼び出し順だけを書く。実行: python -m app.main"""

import logging

from app.config import load_settings
from app.data_io import read_trades, write_trades
from app.logic import extract_large_trades

logger = logging.getLogger(__name__)


def main() -> None:
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    input_path = settings.input_dir / "trades.csv"
    output_path = settings.output_dir / "large_trades.csv"
    logger.info("開始: 入力=%s", input_path)

    trades = read_trades(input_path)
    large_trades = extract_large_trades(trades, settings.amount_threshold)
    write_trades(output_path, large_trades)

    logger.info("終了: 入力%d件 / 抽出%d件 / 出力=%s", len(trades), len(large_trades), output_path)


if __name__ == "__main__":
    main()
