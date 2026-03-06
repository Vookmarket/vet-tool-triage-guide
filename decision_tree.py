"""
判定エンジンモジュール (decision_tree.py)

ルールベース（デシジョンツリー）による電話トリアージ緊急度判定。
安全側設計: 複数症状の組み合わせで重症度を上げる。迷ったらYELLOW以上に倒す。

判定基準:
- RED（すぐ来院）: 呼吸困難、意識消失、大量出血、けいれん重積、猫の排尿不能、
  胃捻転疑い、熱中症、致死性毒物、眼球突出/脱出、難産、後肢麻痺(猫)
- YELLOW（本日中に来院）: 24時間以上の嘔吐/下痢、食欲不振24時間以上、
  軽度外傷、持病悪化、毒物摂取、運動失調、血尿
- GREEN（緊急性低・診察推奨）: 1回の嘔吐+元気あり、軽い咳、軽度の目やに
"""

from __future__ import annotations

from dataclasses import dataclass, field

from terminology import (
    DISCLAIMER,
    Symptom,
    get_symptom_by_id,
)


# ---------------------------------------------------------------------------
# データ構造
# ---------------------------------------------------------------------------

@dataclass
class SymptomInput:
    """構造化された症状入力データ。"""
    species: str  # "犬" | "猫"
    symptoms: list[str]  # 症状IDのリスト
    onset_hours: int | None = None  # 発症からの時間（時間）
    age_group: str = "adult"  # "puppy_kitten" | "adult" | "senior"
    notes: str = ""  # 追加メモ


@dataclass
class TriageResult:
    """トリアージ判定結果。"""
    urgency: str  # "RED" | "YELLOW" | "GREEN"
    urgency_label: str  # "すぐ来院" etc.
    matched_rules: list[str] = field(default_factory=list)  # マッチしたルール名
    reasoning: str = ""  # 判定根拠（構造化テキスト）
    owner_message: str = ""  # 飼い主への伝達文面
    handoff_note: str = ""  # 獣医師への申し送り
    disclaimer: str = DISCLAIMER  # 免責事項
    symptom_details: list[dict[str, str]] = field(default_factory=list)  # 各症状の詳細


# ---------------------------------------------------------------------------
# 緊急度ラベル
# ---------------------------------------------------------------------------

URGENCY_LABELS: dict[str, str] = {
    "RED": "すぐ来院してください",
    "YELLOW": "本日中の受診をお勧めします",
    "GREEN": "緊急性は低い可能性がありますが、正確な判断には診察が必要です",
}

URGENCY_EMOJI: dict[str, str] = {
    "RED": "\U0001f534",     # 赤丸
    "YELLOW": "\U0001f7e1",  # 黄丸
    "GREEN": "\U0001f7e2",   # 緑丸
}


# ---------------------------------------------------------------------------
# 判定ルール
# ---------------------------------------------------------------------------

# critical症状 → 即RED
CRITICAL_SYMPTOM_IDS: set[str] = {
    "resp_dyspnea", "resp_open_mouth", "resp_cyanosis",
    "neuro_seizure", "neuro_seizure_cluster", "neuro_collapse",
    "gi_vomit_blood",
    "trauma_traffic", "trauma_fall", "trauma_bleeding_major",
    "uro_obstruction", "uro_dystocia",
    "temp_heatstroke", "temp_hypothermia",
    "tox_known_lethal",
    "cv_pale_gums", "cv_weak_pulse", "cv_collapse_exercise",
    "eye_proptosis", "eye_prolapse",
    "age_puppy_lethargy", "age_puppy_milk_refusal", "age_puppy_hypothermia",
    "cat_open_mouth_breathing", "cat_hindlimb_paralysis",
    "dog_gdv",
}

# urgent症状 → YELLOW
URGENT_SYMPTOM_IDS: set[str] = {
    "resp_cough_frequent", "resp_stridor",
    "neuro_ataxia", "neuro_head_tilt", "neuro_tremor", "neuro_disorientation",
    "gi_vomit_persistent", "gi_diarrhea_persistent", "gi_bloody_stool",
    "gi_anorexia_24h", "gi_bloat", "gi_foreign_body", "gi_dehydration",
    "trauma_bite", "trauma_fracture", "trauma_burn",
    "uro_straining", "uro_hematuria", "uro_vaginal_discharge",
    "temp_drooling",
    "eye_closed", "eye_opacity",
    "tox_ingestion",
    "cat_hiding",
    "derm_facial_swelling", "derm_hives",
}


# ---------------------------------------------------------------------------
# 組み合わせルール（安全側設計）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CombinationRule:
    """複数症状の組み合わせで緊急度を上げるルール。"""
    name: str
    description: str
    required_any: list[set[str]]  # 各setから少なくとも1つマッチ
    escalate_to: str  # "RED" or "YELLOW"


COMBINATION_RULES: list[CombinationRule] = [
    # GREENの症状でも組み合わせでYELLOWへ
    CombinationRule(
        name="複数の軽度消化器症状",
        description="嘔吐+下痢+食欲不振の組み合わせは脱水リスク",
        required_any=[
            {"gi_vomit_single", "gi_vomit_persistent"},
            {"gi_diarrhea_single", "gi_diarrhea_persistent"},
        ],
        escalate_to="YELLOW",
    ),
    CombinationRule(
        name="消化器症状+元気消失",
        description="嘔吐/下痢に元気消失を伴う場合は要注意",
        required_any=[
            {"gi_vomit_single", "gi_vomit_persistent",
             "gi_diarrhea_single", "gi_diarrhea_persistent"},
            {"neuro_lethargy"},
        ],
        escalate_to="YELLOW",
    ),
    CombinationRule(
        name="食欲不振+元気消失",
        description="食欲不振に元気消失を伴う場合は要注意",
        required_any=[
            {"gi_anorexia", "gi_anorexia_24h"},
            {"neuro_lethargy"},
        ],
        escalate_to="YELLOW",
    ),
    CombinationRule(
        name="犬の腹部膨張+嘔吐",
        description="胃拡張・胃捻転症候群の疑い",
        required_any=[
            {"gi_bloat"},
            {"gi_vomit_single", "gi_vomit_persistent"},
        ],
        escalate_to="RED",
    ),
    CombinationRule(
        name="元気消失+発熱",
        description="感染症の疑い",
        required_any=[
            {"neuro_lethargy"},
            {"temp_fever"},
        ],
        escalate_to="YELLOW",
    ),
    CombinationRule(
        name="呼吸器症状+チアノーゼ",
        description="重度の呼吸不全",
        required_any=[
            {"resp_cough", "resp_cough_frequent", "resp_stridor",
             "resp_nasal_discharge"},
            {"resp_cyanosis"},
        ],
        escalate_to="RED",
    ),
    CombinationRule(
        name="軽度出血+元気消失",
        description="内出血の可能性",
        required_any=[
            {"trauma_bleeding_minor", "trauma_wound"},
            {"neuro_lethargy"},
        ],
        escalate_to="YELLOW",
    ),
    CombinationRule(
        name="充血+眼瞼閉鎖",
        description="重度の眼科疾患の疑い",
        required_any=[
            {"eye_redness"},
            {"eye_closed"},
        ],
        escalate_to="YELLOW",
    ),
    CombinationRule(
        name="多飲多尿+元気消失",
        description="腎疾患/糖尿病等の代謝疾患の疑い",
        required_any=[
            {"uro_polyuria"},
            {"neuro_lethargy"},
        ],
        escalate_to="YELLOW",
    ),
    CombinationRule(
        name="嘔吐+震え",
        description="中毒の疑い",
        required_any=[
            {"gi_vomit_single", "gi_vomit_persistent"},
            {"neuro_tremor"},
        ],
        escalate_to="RED",
    ),
]


# ---------------------------------------------------------------------------
# 飼い主向けメッセージテンプレート
# ---------------------------------------------------------------------------

OWNER_MESSAGES: dict[str, str] = {
    "RED": (
        "お電話ありがとうございます。お話いただいた症状から判断しますと、"
        "できるだけ早く、すぐに病院にお連れいただく必要があります。"
        "移動中もなるべく安静にして、すぐにお越しください。"
        "到着までの間に準備いたしますので、到着予定時刻をお知らせいただけますか？"
    ),
    "YELLOW": (
        "お電話ありがとうございます。お話いただいた症状ですと、"
        "本日中に一度診察を受けていただいたほうがよいかと思います。"
        "ご都合のよいお時間にお越しいただけますか？"
        "症状が急に悪化した場合は、すぐにお電話ください。"
    ),
    "GREEN": (
        "お電話ありがとうございます。現時点でお伺いした症状からは、"
        "緊急性は高くないと思われます。"
        "ただし、お電話でのご相談だけでは正確な判断が難しいため、"
        "症状が続く場合や少しでもご不安がある場合は、お早めにご来院ください。"
    ),
}


# ---------------------------------------------------------------------------
# 判定エンジン
# ---------------------------------------------------------------------------

def _resolve_symptoms(symptom_ids: list[str]) -> list[Symptom]:
    """症状IDリストからSymptomオブジェクトを解決する。"""
    result: list[Symptom] = []
    for sid in symptom_ids:
        sym = get_symptom_by_id(sid)
        if sym is not None:
            result.append(sym)
    return result


def _check_combination_rules(
    symptom_ids: set[str],
) -> list[tuple[CombinationRule, str]]:
    """組み合わせルールをチェックし、マッチしたルールと昇格先を返す。"""
    matches: list[tuple[CombinationRule, str]] = []
    for rule in COMBINATION_RULES:
        all_groups_match = True
        for group in rule.required_any:
            if not group.intersection(symptom_ids):
                all_groups_match = False
                break
        if all_groups_match:
            matches.append((rule, rule.escalate_to))
    return matches


def _determine_base_urgency(symptoms: list[Symptom]) -> tuple[str, list[str]]:
    """各症状の重症度タグから基本緊急度を決定する。

    Returns:
        (urgency, matched_rule_names)
    """
    matched_rules: list[str] = []
    has_critical = False
    has_urgent = False

    for sym in symptoms:
        if sym.id in CRITICAL_SYMPTOM_IDS or sym.severity == "critical":
            has_critical = True
            matched_rules.append(f"[RED] {sym.name}（{sym.id}）: critical症状")
        elif sym.id in URGENT_SYMPTOM_IDS or sym.severity == "urgent":
            has_urgent = True
            matched_rules.append(f"[YELLOW] {sym.name}（{sym.id}）: urgent症状")
        else:
            matched_rules.append(f"[GREEN] {sym.name}（{sym.id}）: mild症状")

    if has_critical:
        return "RED", matched_rules
    if has_urgent:
        return "YELLOW", matched_rules
    return "GREEN", matched_rules


def _build_handoff_note(
    symptom_input: SymptomInput,
    symptoms: list[Symptom],
    urgency: str,
) -> str:
    """獣医師への申し送りメモを構築する。"""
    species_map = {"犬": "犬", "猫": "猫"}
    species_label = species_map.get(symptom_input.species, symptom_input.species)

    age_map = {
        "puppy_kitten": "幼齢",
        "adult": "成犬/成猫",
        "senior": "高齢",
    }
    age_label = age_map.get(symptom_input.age_group, symptom_input.age_group)

    lines: list[str] = [
        f"【電話トリアージ申し送り】",
        f"動物種: {species_label}",
        f"年齢区分: {age_label}",
    ]

    if symptom_input.onset_hours is not None:
        lines.append(f"発症からの経過: 約{symptom_input.onset_hours}時間")

    lines.append(f"緊急度判定: {urgency}")
    lines.append(f"報告された症状:")

    for sym in symptoms:
        category_note = ""
        if sym.species_specific:
            category_note = f"（{sym.species_specific}特有）"
        if sym.age_specific:
            category_note = f"（{sym.age_specific}）"
        lines.append(f"  - {sym.name} [{sym.severity}]{category_note}")

    if symptom_input.notes:
        lines.append(f"追加メモ: {symptom_input.notes}")

    return "\n".join(lines)


def _build_reasoning(
    base_urgency: str,
    final_urgency: str,
    matched_rules: list[str],
    combination_matches: list[tuple[CombinationRule, str]],
) -> str:
    """判定根拠テキストを構築する。"""
    lines: list[str] = ["【判定根拠】"]

    for rule_desc in matched_rules:
        lines.append(f"  {rule_desc}")

    if combination_matches:
        lines.append("")
        lines.append("【組み合わせルール適用】")
        for rule, escalate_to in combination_matches:
            lines.append(f"  {rule.name}: {rule.description} → {escalate_to}へ昇格")

    if base_urgency != final_urgency:
        lines.append("")
        lines.append(
            f"基本判定: {base_urgency} → 組み合わせルールにより {final_urgency} に昇格"
        )

    return "\n".join(lines)


def evaluate(symptom_input: SymptomInput) -> TriageResult:
    """トリアージ判定を実行する。

    入力された症状データからルールベースで緊急度を判定し、
    構造化された結果を返す。

    安全側設計:
    - critical症状が1つでもあれば RED
    - urgent症状が1つでもあれば YELLOW
    - 組み合わせルールで昇格
    - 症状が0件の場合は YELLOW（安全側）

    Args:
        symptom_input: 構造化された症状入力データ

    Returns:
        TriageResult: 判定結果
    """
    # 症状なしの場合 → 安全側でYELLOW
    if not symptom_input.symptoms:
        return TriageResult(
            urgency="YELLOW",
            urgency_label=f"{URGENCY_EMOJI['YELLOW']} {URGENCY_LABELS['YELLOW']}",
            matched_rules=["症状の特定ができないため、安全側でYELLOW判定"],
            reasoning="症状が特定できませんでした。安全のため本日中の来院を推奨します。",
            owner_message=OWNER_MESSAGES["YELLOW"],
            handoff_note="【電話トリアージ申し送り】\n症状の特定ができず、安全側でYELLOW判定",
            symptom_details=[],
        )

    # 症状を解決
    symptoms = _resolve_symptoms(symptom_input.symptoms)
    symptom_id_set = set(symptom_input.symptoms)

    # 基本緊急度を決定
    base_urgency, matched_rules = _determine_base_urgency(symptoms)

    # 組み合わせルールを適用
    combination_matches = _check_combination_rules(symptom_id_set)

    # 最終緊急度を決定（最も高い緊急度を採用）
    urgency_order = {"RED": 3, "YELLOW": 2, "GREEN": 1}
    final_urgency = base_urgency

    for _, escalate_to in combination_matches:
        if urgency_order.get(escalate_to, 0) > urgency_order.get(final_urgency, 0):
            final_urgency = escalate_to

    # 安全側設計: 複数のmild症状がある場合、YELLOWに昇格
    mild_count = sum(1 for s in symptoms if s.severity == "mild")
    if final_urgency == "GREEN" and mild_count >= 3:
        final_urgency = "YELLOW"
        matched_rules.append(
            "[YELLOW] 軽度症状が3つ以上: 複合症状のため安全側でYELLOW判定"
        )

    # 年齢による昇格
    if symptom_input.age_group == "puppy_kitten" and final_urgency == "GREEN":
        final_urgency = "YELLOW"
        matched_rules.append(
            "[YELLOW] 幼齢動物: 子犬・子猫は急変リスクが高いため安全側でYELLOW判定"
        )

    # 発症時間による補正
    if (
        symptom_input.onset_hours is not None
        and symptom_input.onset_hours >= 24
        and final_urgency == "GREEN"
    ):
        final_urgency = "YELLOW"
        matched_rules.append(
            "[YELLOW] 発症から24時間以上経過: 長期化しているため安全側でYELLOW判定"
        )

    # 症状詳細を構築
    symptom_details = [
        {
            "id": sym.id,
            "name": sym.name,
            "severity": sym.severity,
            "description": sym.description,
        }
        for sym in symptoms
    ]

    # 根拠テキスト
    reasoning = _build_reasoning(
        base_urgency, final_urgency, matched_rules, combination_matches
    )

    # 申し送り
    handoff_note = _build_handoff_note(symptom_input, symptoms, final_urgency)

    return TriageResult(
        urgency=final_urgency,
        urgency_label=f"{URGENCY_EMOJI[final_urgency]} {URGENCY_LABELS[final_urgency]}",
        matched_rules=matched_rules,
        reasoning=reasoning,
        owner_message=OWNER_MESSAGES[final_urgency],
        handoff_note=handoff_note,
        symptom_details=symptom_details,
    )
