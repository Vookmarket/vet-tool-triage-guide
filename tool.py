#!/usr/bin/env python3
"""
電話トリアージガイド - メインCLIオーケストレーター (tool.py)

動物病院の受付スタッフ・看護師が、飼い主からの電話中に使う緊急度判定ツール。
ルールベース（デシジョンツリー）で即時判定。

使い方:
  python3 tool.py           # 対話モード
  python3 tool.py --json    # JSON出力モード
"""

from __future__ import annotations

import argparse
import sys

from decision_tree import evaluate
from input_parser import parse_interactive
from output_formatter import format_result
from terminology import DISCLAIMER


# ---------------------------------------------------------------------------
# CLIエントリポイント
# ---------------------------------------------------------------------------

def main() -> None:
    """メインエントリポイント。"""
    parser = argparse.ArgumentParser(
        description="電話トリアージガイド — 獣医療緊急度判定ツール",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON形式で結果を出力",
    )
    args = parser.parse_args()

    output_mode = "json" if args.json else "screen"

    # 起動時の免責事項表示
    print()
    print("=" * 60)
    print("  電話トリアージガイド — 獣医療緊急度判定ツール")
    print("=" * 60)
    print()
    print(DISCLAIMER)
    print()

    try:
        while True:
            # 入力パース
            symptom_input = parse_interactive()

            # 判定実行
            result = evaluate(symptom_input)

            # 結果出力
            formatted = format_result(result, mode=output_mode)
            print(formatted)

            # 続行確認
            print()
            cont = input("続けて判定しますか？ (y/n) > ").strip().lower()
            if cont not in ("y", "yes", "はい"):
                print("\nご利用ありがとうございました。")
                break

    except (KeyboardInterrupt, EOFError):
        print("\n\n終了します。")
        sys.exit(0)


if __name__ == "__main__":
    main()
