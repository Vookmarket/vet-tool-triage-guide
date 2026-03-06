"""
出力フォーマッターモジュール (output_formatter.py)

TriageResult（構造化データ）を人間向けテキストに変換する。

出力形式:
a. 画面表示（色付き緊急度 + 判定根拠 + 伝達文面）
b. 飼い主への伝達文面（そのまま読み上げ可能）
c. 獣医師への申し送りメモ（コピペ用）
d. JSON出力（--json フラグ用）
"""

from __future__ import annotations

import json
from dataclasses import asdict

from decision_tree import TriageResult


# ---------------------------------------------------------------------------
# ANSI カラーコード（ターミナル表示用）
# ---------------------------------------------------------------------------

class _Colors:
    """ANSIカラーコード。Windows等でサポートされない場合はフォールバック。"""
    RED = "\033[91m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    DIM = "\033[2m"


def _urgency_color(urgency: str) -> str:
    """緊急度に対応するANSIカラーコードを返す。"""
    match urgency:
        case "RED":
            return _Colors.RED
        case "YELLOW":
            return _Colors.YELLOW
        case "GREEN":
            return _Colors.GREEN
        case _:
            return ""


# ---------------------------------------------------------------------------
# 画面表示フォーマット
# ---------------------------------------------------------------------------

def format_screen(result: TriageResult) -> str:
    """画面表示用のフォーマット。

    色付きの緊急度表示、判定根拠、飼い主への伝達文面を含む。

    Args:
        result: トリアージ判定結果

    Returns:
        画面表示用テキスト
    """
    color = _urgency_color(result.urgency)
    reset = _Colors.RESET
    bold = _Colors.BOLD
    dim = _Colors.DIM

    lines: list[str] = []

    # ヘッダー
    lines.append("")
    lines.append(f"{bold}{'=' * 60}{reset}")
    lines.append(f"{bold}  電話トリアージ判定結果{reset}")
    lines.append(f"{bold}{'=' * 60}{reset}")

    # 緊急度
    lines.append("")
    lines.append(f"  {color}{bold}判定: {result.urgency_label}{reset}")
    lines.append("")

    # 判定根拠
    lines.append(f"{bold}--- 判定根拠 ---{reset}")
    for line in result.reasoning.split("\n"):
        lines.append(f"  {line}")
    lines.append("")

    # 症状サマリ
    if result.symptom_details:
        lines.append(f"{bold}--- 報告された症状 ---{reset}")
        for detail in result.symptom_details:
            severity_color = _urgency_color(
                {"critical": "RED", "urgent": "YELLOW", "mild": "GREEN"}.get(
                    detail["severity"], ""
                )
            )
            lines.append(
                f"  {severity_color}[{detail['severity']}]{reset} "
                f"{detail['name']}: {detail['description']}"
            )
        lines.append("")

    # 飼い主への伝達文面
    lines.append(f"{bold}--- 飼い主への伝達文面（読み上げ用）---{reset}")
    lines.append(f"  {result.owner_message}")
    lines.append("")

    # 獣医師への申し送り
    lines.append(f"{bold}--- 獣医師への申し送り ---{reset}")
    for line in result.handoff_note.split("\n"):
        lines.append(f"  {line}")
    lines.append("")

    # 免責事項
    lines.append(f"{dim}{result.disclaimer}{reset}")
    lines.append(f"{bold}{'=' * 60}{reset}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 飼い主伝達文面フォーマット
# ---------------------------------------------------------------------------

def format_owner_message(result: TriageResult) -> str:
    """飼い主への伝達文面（そのまま読み上げ可能）。

    Args:
        result: トリアージ判定結果

    Returns:
        読み上げ用テキスト
    """
    lines: list[str] = []

    lines.append(f"【電話トリアージ: {result.urgency_label}】")
    lines.append("")
    lines.append(result.owner_message)
    lines.append("")
    lines.append(result.disclaimer)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 獣医師申し送りフォーマット
# ---------------------------------------------------------------------------

def format_handoff_note(result: TriageResult) -> str:
    """獣医師への申し送りメモ（コピペ用）。

    Args:
        result: トリアージ判定結果

    Returns:
        申し送りメモテキスト
    """
    lines: list[str] = []

    lines.append(result.handoff_note)
    lines.append("")
    lines.append(f"判定: {result.urgency}")
    lines.append("")
    lines.append("マッチしたルール:")
    for rule in result.matched_rules:
        lines.append(f"  - {rule}")
    lines.append("")
    lines.append(result.disclaimer)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON フォーマット
# ---------------------------------------------------------------------------

def format_json(result: TriageResult) -> str:
    """JSON形式で出力する。

    Args:
        result: トリアージ判定結果

    Returns:
        JSON文字列（整形済み）
    """
    data = asdict(result)
    return json.dumps(data, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def format_result(result: TriageResult, mode: str = "screen") -> str:
    """指定モードでフォーマットして返す。

    Args:
        result: トリアージ判定結果
        mode: "screen" | "owner" | "handoff" | "json"

    Returns:
        フォーマット済みテキスト

    Raises:
        ValueError: 不明なmodeの場合
    """
    match mode:
        case "screen":
            return format_screen(result)
        case "owner":
            return format_owner_message(result)
        case "handoff":
            return format_handoff_note(result)
        case "json":
            return format_json(result)
        case _:
            raise ValueError(
                f"不明な出力モードです: {mode}。"
                f"'screen', 'owner', 'handoff', 'json' のいずれかを指定してください。"
            )
