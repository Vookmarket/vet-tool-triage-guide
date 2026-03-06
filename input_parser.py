"""
入力パーサーモジュール (input_parser.py)

対話式入力から構造化データ（SymptomInput）に変換する。
- カテゴリ→症状の2段階番号選択
- 自由入力テキストからのキーワードマッチング
- 動物種、年齢区分、発症時間のパース
"""

from __future__ import annotations

import sys
from typing import TextIO

from decision_tree import SymptomInput
from terminology import (
    SYMPTOMS,
    Symptom,
    get_category_list,
    get_symptoms_in_category,
    search_by_alias,
)


# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

SPECIES_OPTIONS: dict[str, str] = {
    "1": "犬",
    "2": "猫",
}

AGE_GROUP_OPTIONS: dict[str, str] = {
    "1": "puppy_kitten",
    "2": "adult",
    "3": "senior",
}

AGE_GROUP_LABELS: dict[str, str] = {
    "puppy_kitten": "子犬・子猫（1歳未満）",
    "adult": "成犬・成猫（1〜7歳）",
    "senior": "高齢（7歳以上）",
}


# ---------------------------------------------------------------------------
# 入力ヘルパー
# ---------------------------------------------------------------------------

def _prompt_input(
    prompt: str,
    valid_options: set[str] | None = None,
    allow_empty: bool = False,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> str:
    """ユーザーに入力を求める。

    Args:
        prompt: 表示するプロンプト文字列
        valid_options: 有効な選択肢（Noneなら任意の入力を受け付ける）
        allow_empty: 空入力を許可するか
        input_stream: 入力ストリーム（テスト用）
        output_stream: 出力ストリーム（テスト用）

    Returns:
        ユーザーの入力値
    """
    out = output_stream or sys.stdout
    inp = input_stream or sys.stdin

    while True:
        out.write(prompt)
        out.flush()
        line = inp.readline()
        if not line:  # EOF
            raise EOFError("入力が終了しました")
        value = line.strip()
        if not value and not allow_empty:
            out.write("入力してください。\n")
            continue
        if valid_options and value not in valid_options:
            out.write(f"無効な選択です。次の中から選んでください: {', '.join(sorted(valid_options))}\n")
            continue
        return value


# ---------------------------------------------------------------------------
# 対話式パーサー
# ---------------------------------------------------------------------------

def parse_species(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> str:
    """動物種を対話的に選択する。

    Returns:
        "犬" or "猫"
    """
    out = output_stream or sys.stdout
    out.write("\n=== 動物種の選択 ===\n")
    for key, label in SPECIES_OPTIONS.items():
        out.write(f"  {key}. {label}\n")

    choice = _prompt_input(
        "番号を入力 > ",
        valid_options=set(SPECIES_OPTIONS.keys()),
        input_stream=input_stream,
        output_stream=output_stream,
    )
    return SPECIES_OPTIONS[choice]


def parse_age_group(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> str:
    """年齢区分を対話的に選択する。

    Returns:
        "puppy_kitten" | "adult" | "senior"
    """
    out = output_stream or sys.stdout
    out.write("\n=== 年齢区分の選択 ===\n")
    for key, age_key in AGE_GROUP_OPTIONS.items():
        out.write(f"  {key}. {AGE_GROUP_LABELS[age_key]}\n")

    choice = _prompt_input(
        "番号を入力 > ",
        valid_options=set(AGE_GROUP_OPTIONS.keys()),
        input_stream=input_stream,
        output_stream=output_stream,
    )
    return AGE_GROUP_OPTIONS[choice]


def parse_onset_hours(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int | None:
    """発症からの経過時間をパースする。

    Returns:
        時間（int）またはNone（不明の場合）
    """
    out = output_stream or sys.stdout
    out.write("\n=== 発症からの経過時間 ===\n")
    out.write("  時間で入力してください（不明な場合はEnterでスキップ）\n")

    value = _prompt_input(
        "時間 > ",
        allow_empty=True,
        input_stream=input_stream,
        output_stream=output_stream,
    )

    if not value:
        return None
    try:
        hours = int(value)
        if hours < 0:
            out.write("0以上の数値を入力してください。不明としてスキップします。\n")
            return None
        return hours
    except ValueError:
        out.write("数値を入力してください。不明としてスキップします。\n")
        return None


def parse_symptoms_interactive(
    species: str,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> list[str]:
    """対話式に症状を選択する（カテゴリ→症状の2段階）。

    Args:
        species: "犬" or "猫"

    Returns:
        選択された症状IDのリスト
    """
    out = output_stream or sys.stdout
    inp = input_stream

    selected_ids: list[str] = []
    species_key = "dog" if species == "犬" else "cat"

    while True:
        out.write("\n=== 症状の選択 ===\n")
        out.write("  カテゴリを選んでから症状を選択します。\n")
        out.write("  「t」でテキスト入力モード、「d」で選択完了\n")

        # カテゴリ一覧
        categories = get_category_list()
        for i, cat in enumerate(categories, 1):
            out.write(f"  {i}. {cat['label']}\n")
        out.write(f"  t. テキストで症状を入力\n")
        out.write(f"  d. 選択完了\n")

        if selected_ids:
            out.write(f"\n  現在選択中の症状: {len(selected_ids)}件\n")

        choice = _prompt_input(
            "番号を入力 > ",
            allow_empty=False,
            input_stream=inp,
            output_stream=output_stream,
        )

        if choice.lower() == "d":
            break

        if choice.lower() == "t":
            # テキスト入力モード
            text_ids = parse_symptoms_text(
                species, input_stream=inp, output_stream=output_stream
            )
            for sid in text_ids:
                if sid not in selected_ids:
                    selected_ids.append(sid)
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                cat_id = categories[idx]["id"]
                symptoms_in_cat = get_symptoms_in_category(cat_id)

                # 動物種でフィルタ
                filtered = [
                    s for s in symptoms_in_cat
                    if s.species_specific is None or s.species_specific == species_key
                ]

                if not filtered:
                    out.write("このカテゴリには該当する症状がありません。\n")
                    continue

                out.write(f"\n--- {categories[idx]['label']}の症状 ---\n")
                for j, sym in enumerate(filtered, 1):
                    selected_mark = " [選択済]" if sym.id in selected_ids else ""
                    severity_mark = {
                        "critical": "(!)",
                        "urgent": "(?)",
                        "mild": "",
                    }.get(sym.severity, "")
                    out.write(f"  {j}. {sym.name} {severity_mark}{selected_mark}\n")
                out.write(f"  0. 戻る\n")

                sym_choice = _prompt_input(
                    "番号を入力（カンマ区切りで複数選択可） > ",
                    allow_empty=False,
                    input_stream=inp,
                    output_stream=output_stream,
                )

                if sym_choice == "0":
                    continue

                # カンマ区切りで複数選択
                for part in sym_choice.split(","):
                    part = part.strip()
                    try:
                        sym_idx = int(part) - 1
                        if 0 <= sym_idx < len(filtered):
                            sid = filtered[sym_idx].id
                            if sid not in selected_ids:
                                selected_ids.append(sid)
                                out.write(f"  → {filtered[sym_idx].name} を追加しました\n")
                            else:
                                out.write(f"  → {filtered[sym_idx].name} は既に選択済みです\n")
                        else:
                            out.write(f"  → {part}: 無効な番号です\n")
                    except ValueError:
                        out.write(f"  → {part}: 数値を入力してください\n")
            else:
                out.write("無効な番号です。\n")
        except ValueError:
            out.write("番号を入力してください。\n")

    return selected_ids


def parse_symptoms_text(
    species: str,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> list[str]:
    """テキスト入力から症状を抽出する。

    terminologyのaliasesを使用してキーワードマッチングする。

    Args:
        species: "犬" or "猫"

    Returns:
        マッチした症状IDのリスト
    """
    out = output_stream or sys.stdout
    inp = input_stream

    out.write("\n=== テキスト入力モード ===\n")
    out.write("  症状を自由にテキストで入力してください。\n")
    out.write("  例: 「息が荒くてぐったりしてる」\n")

    text = _prompt_input(
        "症状を入力 > ",
        allow_empty=False,
        input_stream=inp,
        output_stream=output_stream,
    )

    species_key = "dog" if species == "犬" else "cat"
    matches = search_by_alias(text)

    # 動物種フィルタ
    filtered = [
        s for s in matches
        if s.species_specific is None or s.species_specific == species_key
    ]

    if not filtered:
        out.write("  該当する症状が見つかりませんでした。\n")
        out.write("  カテゴリ選択モードで選んでください。\n")
        return []

    out.write(f"\n  以下の症状が見つかりました:\n")
    for i, sym in enumerate(filtered, 1):
        out.write(f"  {i}. {sym.name}（{sym.severity}）\n")

    out.write("  全て採用しますか？ (y/n/番号をカンマ区切り) > ")
    out.flush()

    if inp:
        line = inp.readline().strip()
    else:
        line = input().strip()

    if line.lower() in ("y", "yes", "はい"):
        return [s.id for s in filtered]
    elif line.lower() in ("n", "no", "いいえ"):
        return []
    else:
        # 番号選択
        selected: list[str] = []
        for part in line.split(","):
            part = part.strip()
            try:
                idx = int(part) - 1
                if 0 <= idx < len(filtered):
                    selected.append(filtered[idx].id)
            except ValueError:
                pass
        return selected


def parse_notes(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> str:
    """追加メモを入力する。"""
    out = output_stream or sys.stdout
    out.write("\n=== 追加メモ ===\n")
    out.write("  その他気になる点があれば入力（なければEnterでスキップ）\n")

    return _prompt_input(
        "メモ > ",
        allow_empty=True,
        input_stream=input_stream,
        output_stream=output_stream,
    )


# ---------------------------------------------------------------------------
# メインパース関数
# ---------------------------------------------------------------------------

def parse_interactive(
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> SymptomInput:
    """対話式に全項目を入力し、SymptomInputを返す。

    Returns:
        構造化された症状入力データ
    """
    species = parse_species(input_stream=input_stream, output_stream=output_stream)
    age_group = parse_age_group(input_stream=input_stream, output_stream=output_stream)
    onset_hours = parse_onset_hours(input_stream=input_stream, output_stream=output_stream)
    symptoms = parse_symptoms_interactive(
        species, input_stream=input_stream, output_stream=output_stream
    )
    notes = parse_notes(input_stream=input_stream, output_stream=output_stream)

    return SymptomInput(
        species=species,
        symptoms=symptoms,
        onset_hours=onset_hours,
        age_group=age_group,
        notes=notes,
    )


def build_symptom_input(
    species: str,
    symptom_ids: list[str],
    onset_hours: int | None = None,
    age_group: str = "adult",
    notes: str = "",
) -> SymptomInput:
    """プログラマティックにSymptomInputを構築する（テスト/API用）。

    Args:
        species: "犬" or "猫"
        symptom_ids: 症状IDリスト
        onset_hours: 発症からの時間
        age_group: 年齢区分
        notes: 追加メモ

    Returns:
        構造化された症状入力データ
    """
    return SymptomInput(
        species=species,
        symptoms=symptom_ids,
        onset_hours=onset_hours,
        age_group=age_group,
        notes=notes,
    )
