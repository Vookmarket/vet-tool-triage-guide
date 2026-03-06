"""
テストスイート (test_tool.py)

電話トリアージガイドの包括的テスト。
pytest で実行: python3 -m pytest test_tool.py -v

テストカテゴリ:
- terminology: 用語辞書の整合性テスト
- decision_tree: 判定エンジンのテスト
- input_parser: 入力パーサーのテスト
- output_formatter: 出力フォーマッターのテスト
- integration: 統合テスト（シナリオベース）
"""

from __future__ import annotations

import json
import io
import sys
import os

import pytest

# テスト対象のディレクトリにパスを通す
sys.path.insert(0, os.path.dirname(__file__))

from terminology import (
    SYMPTOMS,
    Symptom,
    SymptomCategory,
    get_all_symptoms,
    get_symptom_by_id,
    get_symptoms_by_severity,
    get_symptoms_for_species,
    get_symptoms_for_age,
    search_by_alias,
    get_category_list,
    get_symptoms_in_category,
    DISCLAIMER,
)
from decision_tree import (
    SymptomInput,
    TriageResult,
    evaluate,
    CRITICAL_SYMPTOM_IDS,
    URGENT_SYMPTOM_IDS,
    URGENCY_LABELS,
)
from input_parser import (
    build_symptom_input,
    parse_species,
    parse_age_group,
    parse_onset_hours,
    parse_symptoms_text,
)
from output_formatter import (
    format_screen,
    format_owner_message,
    format_handoff_note,
    format_json,
    format_result,
)


# ===========================================================================
# terminology.py テスト
# ===========================================================================


class TestTerminologyIntegrity:
    """用語辞書の整合性テスト。"""

    def test_all_symptoms_have_required_fields(self) -> None:
        """全症状にid, name, severityが存在する。"""
        for cat in SYMPTOMS.values():
            for sym in cat.symptoms:
                assert sym.id, f"症状にidがない: {sym}"
                assert sym.name, f"症状にnameがない: {sym.id}"
                assert sym.severity in (
                    "critical", "urgent", "mild"
                ), f"不正なseverity: {sym.id} = {sym.severity}"

    def test_all_symptom_ids_unique(self) -> None:
        """全症状IDが一意である。"""
        all_symptoms = get_all_symptoms()
        ids = [s.id for s in all_symptoms]
        duplicates = [sid for sid in ids if ids.count(sid) > 1]
        assert len(duplicates) == 0, f"重複ID: {set(duplicates)}"

    def test_all_categories_have_symptoms(self) -> None:
        """全カテゴリに少なくとも1つの症状がある。"""
        for cat_id, cat in SYMPTOMS.items():
            assert len(cat.symptoms) > 0, f"カテゴリ {cat_id} に症状がない"

    def test_all_categories_have_label(self) -> None:
        """全カテゴリに日本語ラベルがある。"""
        for cat_id, cat in SYMPTOMS.items():
            assert cat.label, f"カテゴリ {cat_id} にラベルがない"

    def test_severity_distribution(self) -> None:
        """critical, urgent, mild の各重症度に少なくとも1つの症状がある。"""
        for severity in ("critical", "urgent", "mild"):
            symptoms = get_symptoms_by_severity(severity)
            assert len(symptoms) > 0, f"{severity} の症状が1つもない"

    def test_species_specific_values(self) -> None:
        """species_specificの値が有効である。"""
        for sym in get_all_symptoms():
            if sym.species_specific is not None:
                assert sym.species_specific in (
                    "dog", "cat"
                ), f"不正なspecies_specific: {sym.id} = {sym.species_specific}"

    def test_age_specific_values(self) -> None:
        """age_specificの値が有効である。"""
        for sym in get_all_symptoms():
            if sym.age_specific is not None:
                assert sym.age_specific in (
                    "puppy_kitten", "senior"
                ), f"不正なage_specific: {sym.id} = {sym.age_specific}"

    def test_aliases_are_lists(self) -> None:
        """全症状のaliasesがリストである。"""
        for sym in get_all_symptoms():
            assert isinstance(sym.aliases, list), f"{sym.id} のaliasesがlistでない"

    def test_minimum_symptom_count(self) -> None:
        """最低限の症状数（50以上）がある。"""
        all_symptoms = get_all_symptoms()
        assert len(all_symptoms) >= 50, f"症状数が少なすぎる: {len(all_symptoms)}"


class TestTerminologyHelpers:
    """用語辞書のヘルパー関数テスト。"""

    def test_get_symptom_by_id_found(self) -> None:
        """既存IDで症状を取得できる。"""
        sym = get_symptom_by_id("resp_dyspnea")
        assert sym is not None
        assert sym.name == "呼吸困難"

    def test_get_symptom_by_id_not_found(self) -> None:
        """存在しないIDでNoneが返る。"""
        sym = get_symptom_by_id("nonexistent_id")
        assert sym is None

    def test_get_symptoms_for_species_dog(self) -> None:
        """犬向けの症状が取得できる（猫特有は含まない）。"""
        dog_symptoms = get_symptoms_for_species("dog")
        ids = {s.id for s in dog_symptoms}
        assert "dog_gdv" in ids, "犬特有の胃捻転が含まれるべき"
        assert "uro_obstruction" not in ids, "猫特有の尿路閉塞が含まれるべきでない"

    def test_get_symptoms_for_species_cat(self) -> None:
        """猫向けの症状が取得できる（犬特有は含まない）。"""
        cat_symptoms = get_symptoms_for_species("cat")
        ids = {s.id for s in cat_symptoms}
        assert "uro_obstruction" in ids, "猫特有の尿路閉塞が含まれるべき"
        assert "dog_gdv" not in ids, "犬特有の胃捻転が含まれるべきでない"

    def test_search_by_alias_match(self) -> None:
        """aliasでの検索がマッチする。"""
        matches = search_by_alias("息が荒い")
        ids = {s.id for s in matches}
        assert "resp_dyspnea" in ids

    def test_search_by_alias_multiple(self) -> None:
        """複数のaliasが同時にマッチする。"""
        matches = search_by_alias("息が荒くてぐったりしてる")
        ids = {s.id for s in matches}
        assert "resp_dyspnea" in ids
        assert "neuro_collapse" in ids or "neuro_lethargy" in ids

    def test_search_by_alias_no_match(self) -> None:
        """マッチしないテキストで空リスト。"""
        matches = search_by_alias("今日は天気がいい")
        assert len(matches) == 0

    def test_get_category_list(self) -> None:
        """カテゴリ一覧が取得できる。"""
        categories = get_category_list()
        assert len(categories) > 0
        for cat in categories:
            assert "id" in cat
            assert "label" in cat

    def test_get_symptoms_in_category(self) -> None:
        """指定カテゴリの症状が取得できる。"""
        symptoms = get_symptoms_in_category("respiratory")
        assert len(symptoms) > 0
        assert all(isinstance(s, Symptom) for s in symptoms)

    def test_get_symptoms_in_nonexistent_category(self) -> None:
        """存在しないカテゴリで空リスト。"""
        symptoms = get_symptoms_in_category("nonexistent")
        assert symptoms == []


# ===========================================================================
# decision_tree.py テスト
# ===========================================================================


class TestDecisionTreeCritical:
    """RED判定のテスト。"""

    def test_respiratory_distress_red(self) -> None:
        """呼吸困難 → RED。"""
        inp = SymptomInput(species="犬", symptoms=["resp_dyspnea"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_seizure_red(self) -> None:
        """けいれん → RED。"""
        inp = SymptomInput(species="犬", symptoms=["neuro_seizure"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_collapse_red(self) -> None:
        """意識消失 → RED。"""
        inp = SymptomInput(species="猫", symptoms=["neuro_collapse"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_major_bleeding_red(self) -> None:
        """大量出血 → RED。"""
        inp = SymptomInput(species="犬", symptoms=["trauma_bleeding_major"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_cat_urinary_obstruction_red(self) -> None:
        """猫の排尿不能 → RED。"""
        inp = SymptomInput(species="猫", symptoms=["uro_obstruction"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_gdv_suspicion_red(self) -> None:
        """犬の胃捻転疑い → RED。"""
        inp = SymptomInput(species="犬", symptoms=["dog_gdv"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_heatstroke_red(self) -> None:
        """熱中症 → RED。"""
        inp = SymptomInput(species="犬", symptoms=["temp_heatstroke"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_vomiting_blood_red(self) -> None:
        """吐血 → RED。"""
        inp = SymptomInput(species="犬", symptoms=["gi_vomit_blood"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_traffic_accident_red(self) -> None:
        """交通事故 → RED。"""
        inp = SymptomInput(species="犬", symptoms=["trauma_traffic"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_cat_hindlimb_paralysis_red(self) -> None:
        """猫の後肢麻痺 → RED。"""
        inp = SymptomInput(species="猫", symptoms=["cat_hindlimb_paralysis"])
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_puppy_lethargy_red(self) -> None:
        """子犬の元気消失 → RED。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["age_puppy_lethargy"],
            age_group="puppy_kitten",
        )
        result = evaluate(inp)
        assert result.urgency == "RED"


class TestDecisionTreeUrgent:
    """YELLOW判定のテスト。"""

    def test_persistent_vomiting_yellow(self) -> None:
        """持続的嘔吐 → YELLOW。"""
        inp = SymptomInput(species="犬", symptoms=["gi_vomit_persistent"])
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_persistent_diarrhea_yellow(self) -> None:
        """持続的下痢 → YELLOW。"""
        inp = SymptomInput(species="猫", symptoms=["gi_diarrhea_persistent"])
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_anorexia_24h_yellow(self) -> None:
        """24時間以上の食欲不振 → YELLOW。"""
        inp = SymptomInput(species="犬", symptoms=["gi_anorexia_24h"])
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_bite_wound_yellow(self) -> None:
        """咬傷 → YELLOW。"""
        inp = SymptomInput(species="犬", symptoms=["trauma_bite"])
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_toxin_ingestion_yellow(self) -> None:
        """毒物摂取 → YELLOW。"""
        inp = SymptomInput(species="犬", symptoms=["tox_ingestion"])
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_ataxia_yellow(self) -> None:
        """運動失調 → YELLOW。"""
        inp = SymptomInput(species="犬", symptoms=["neuro_ataxia"])
        result = evaluate(inp)
        assert result.urgency == "YELLOW"


class TestDecisionTreeGreen:
    """GREEN判定のテスト。"""

    def test_single_vomit_green(self) -> None:
        """1回の嘔吐 → GREEN。"""
        inp = SymptomInput(species="猫", symptoms=["gi_vomit_single"])
        result = evaluate(inp)
        assert result.urgency == "GREEN"

    def test_mild_cough_green(self) -> None:
        """軽い咳 → GREEN。"""
        inp = SymptomInput(species="犬", symptoms=["resp_cough"])
        result = evaluate(inp)
        assert result.urgency == "GREEN"

    def test_mild_eye_discharge_green(self) -> None:
        """軽度の目やに → GREEN。"""
        inp = SymptomInput(species="猫", symptoms=["eye_discharge"])
        result = evaluate(inp)
        assert result.urgency == "GREEN"


class TestDecisionTreeCombination:
    """組み合わせルールのテスト（安全側設計）。"""

    def test_vomit_plus_diarrhea_escalate_to_yellow(self) -> None:
        """嘔吐+下痢 → GREEN→YELLOW昇格。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["gi_vomit_single", "gi_diarrhea_single"],
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_vomit_plus_lethargy_escalate_to_yellow(self) -> None:
        """嘔吐+元気消失 → GREEN→YELLOW昇格。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["gi_vomit_single", "neuro_lethargy"],
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_bloat_plus_vomit_escalate_to_red(self) -> None:
        """腹部膨張+嘔吐 → YELLOW→RED昇格（胃捻転疑い）。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["gi_bloat", "gi_vomit_single"],
        )
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_lethargy_plus_fever_escalate_to_yellow(self) -> None:
        """元気消失+発熱 → GREEN→YELLOW昇格。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["neuro_lethargy", "temp_fever"],
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_three_mild_symptoms_escalate_to_yellow(self) -> None:
        """軽度症状3つ以上 → GREEN→YELLOW昇格。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["resp_cough", "eye_discharge", "gi_anorexia"],
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_vomit_plus_tremor_escalate_to_red(self) -> None:
        """嘔吐+震え → RED昇格（中毒疑い）。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["gi_vomit_single", "neuro_tremor"],
        )
        result = evaluate(inp)
        assert result.urgency == "RED"


class TestDecisionTreeSafetyDesign:
    """安全側設計のテスト。"""

    def test_no_symptoms_defaults_to_yellow(self) -> None:
        """症状なし → YELLOW（安全側）。"""
        inp = SymptomInput(species="犬", symptoms=[])
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_puppy_green_escalates_to_yellow(self) -> None:
        """子犬の軽度症状 → GREEN→YELLOW昇格。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["resp_cough"],
            age_group="puppy_kitten",
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_onset_24h_escalates_to_yellow(self) -> None:
        """24時間以上経過の軽度症状 → GREEN→YELLOW昇格。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["resp_cough"],
            onset_hours=25,
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"


class TestDecisionTreeResultStructure:
    """TriageResultの構造テスト。"""

    def test_result_has_all_fields(self) -> None:
        """結果に全フィールドが含まれる。"""
        inp = SymptomInput(species="犬", symptoms=["resp_dyspnea"])
        result = evaluate(inp)
        assert result.urgency in ("RED", "YELLOW", "GREEN")
        assert result.urgency_label
        assert isinstance(result.matched_rules, list)
        assert result.reasoning
        assert result.owner_message
        assert result.handoff_note
        assert result.disclaimer

    def test_result_symptom_details(self) -> None:
        """結果のsymptom_detailsが正しい構造を持つ。"""
        inp = SymptomInput(species="犬", symptoms=["resp_dyspnea", "neuro_lethargy"])
        result = evaluate(inp)
        assert len(result.symptom_details) == 2
        for detail in result.symptom_details:
            assert "id" in detail
            assert "name" in detail
            assert "severity" in detail
            assert "description" in detail

    def test_result_matched_rules_not_empty(self) -> None:
        """マッチしたルールが空でない。"""
        inp = SymptomInput(species="犬", symptoms=["resp_dyspnea"])
        result = evaluate(inp)
        assert len(result.matched_rules) > 0

    def test_handoff_note_contains_species(self) -> None:
        """申し送りに動物種が含まれる。"""
        inp = SymptomInput(species="猫", symptoms=["resp_dyspnea"])
        result = evaluate(inp)
        assert "猫" in result.handoff_note

    def test_handoff_note_contains_onset(self) -> None:
        """発症時間が申し送りに含まれる。"""
        inp = SymptomInput(species="犬", symptoms=["resp_cough"], onset_hours=12)
        result = evaluate(inp)
        assert "12" in result.handoff_note


# ===========================================================================
# input_parser.py テスト
# ===========================================================================


class TestInputParser:
    """入力パーサーのテスト。"""

    def test_build_symptom_input(self) -> None:
        """プログラマティックにSymptomInputを構築できる。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["resp_dyspnea", "neuro_lethargy"],
            onset_hours=6,
            age_group="adult",
            notes="大型犬",
        )
        assert inp.species == "犬"
        assert inp.symptoms == ["resp_dyspnea", "neuro_lethargy"]
        assert inp.onset_hours == 6
        assert inp.age_group == "adult"
        assert inp.notes == "大型犬"

    def test_parse_species_dog(self) -> None:
        """犬の選択をパースできる。"""
        inp_stream = io.StringIO("1\n")
        out_stream = io.StringIO()
        species = parse_species(input_stream=inp_stream, output_stream=out_stream)
        assert species == "犬"

    def test_parse_species_cat(self) -> None:
        """猫の選択をパースできる。"""
        inp_stream = io.StringIO("2\n")
        out_stream = io.StringIO()
        species = parse_species(input_stream=inp_stream, output_stream=out_stream)
        assert species == "猫"

    def test_parse_age_group_puppy(self) -> None:
        """子犬子猫の年齢区分をパースできる。"""
        inp_stream = io.StringIO("1\n")
        out_stream = io.StringIO()
        age = parse_age_group(input_stream=inp_stream, output_stream=out_stream)
        assert age == "puppy_kitten"

    def test_parse_age_group_senior(self) -> None:
        """高齢の年齢区分をパースできる。"""
        inp_stream = io.StringIO("3\n")
        out_stream = io.StringIO()
        age = parse_age_group(input_stream=inp_stream, output_stream=out_stream)
        assert age == "senior"

    def test_parse_onset_hours(self) -> None:
        """発症時間をパースできる。"""
        inp_stream = io.StringIO("12\n")
        out_stream = io.StringIO()
        hours = parse_onset_hours(input_stream=inp_stream, output_stream=out_stream)
        assert hours == 12

    def test_parse_onset_hours_skip(self) -> None:
        """発症時間のスキップ。"""
        inp_stream = io.StringIO("\n")
        out_stream = io.StringIO()
        hours = parse_onset_hours(input_stream=inp_stream, output_stream=out_stream)
        assert hours is None

    def test_parse_onset_hours_invalid(self) -> None:
        """不正な発症時間 → None。"""
        inp_stream = io.StringIO("abc\n")
        out_stream = io.StringIO()
        hours = parse_onset_hours(input_stream=inp_stream, output_stream=out_stream)
        assert hours is None

    def test_parse_symptoms_text_match(self) -> None:
        """テキスト入力で症状がマッチする。"""
        inp_stream = io.StringIO("息が荒い\ny\n")
        out_stream = io.StringIO()
        ids = parse_symptoms_text("犬", input_stream=inp_stream, output_stream=out_stream)
        assert "resp_dyspnea" in ids

    def test_parse_symptoms_text_no_match(self) -> None:
        """マッチしないテキスト。"""
        inp_stream = io.StringIO("元気にしてる\n")
        out_stream = io.StringIO()
        ids = parse_symptoms_text("犬", input_stream=inp_stream, output_stream=out_stream)
        assert len(ids) == 0


# ===========================================================================
# output_formatter.py テスト
# ===========================================================================


class TestOutputFormatter:
    """出力フォーマッターのテスト。"""

    def _make_result(self) -> TriageResult:
        """テスト用のTriageResultを作成する。"""
        inp = SymptomInput(
            species="犬",
            symptoms=["resp_dyspnea", "neuro_lethargy"],
            onset_hours=6,
        )
        return evaluate(inp)

    def test_format_screen(self) -> None:
        """画面表示フォーマットが生成される。"""
        result = self._make_result()
        text = format_screen(result)
        assert "電話トリアージ判定結果" in text
        assert "判定根拠" in text
        assert "飼い主への伝達文面" in text
        assert "獣医師への申し送り" in text

    def test_format_owner_message(self) -> None:
        """飼い主伝達文面が生成される。"""
        result = self._make_result()
        text = format_owner_message(result)
        assert "お電話ありがとうございます" in text
        assert "免責事項" in text

    def test_format_handoff_note(self) -> None:
        """獣医師申し送りが生成される。"""
        result = self._make_result()
        text = format_handoff_note(result)
        assert "電話トリアージ申し送り" in text
        assert "犬" in text

    def test_format_json_valid(self) -> None:
        """JSON出力が有効なJSONである。"""
        result = self._make_result()
        text = format_json(result)
        data = json.loads(text)
        assert "urgency" in data
        assert "matched_rules" in data
        assert "owner_message" in data

    def test_format_json_contains_urgency(self) -> None:
        """JSON出力に緊急度が含まれる。"""
        result = self._make_result()
        text = format_json(result)
        data = json.loads(text)
        assert data["urgency"] == "RED"

    def test_format_result_screen(self) -> None:
        """format_result(mode='screen')が動作する。"""
        result = self._make_result()
        text = format_result(result, mode="screen")
        assert len(text) > 0

    def test_format_result_json(self) -> None:
        """format_result(mode='json')が動作する。"""
        result = self._make_result()
        text = format_result(result, mode="json")
        data = json.loads(text)
        assert "urgency" in data

    def test_format_result_invalid_mode(self) -> None:
        """不正なモードでValueError。"""
        result = self._make_result()
        with pytest.raises(ValueError, match="不明な出力モード"):
            format_result(result, mode="invalid")


# ===========================================================================
# 統合テスト（シナリオベース）
# ===========================================================================


class TestIntegrationScenarios:
    """実際の電話相談を想定したシナリオテスト。"""

    def test_scenario_dog_hematemesis_collapse(self) -> None:
        """シナリオ: 犬+吐血+ぐったり → RED。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["gi_vomit_blood", "neuro_collapse"],
        )
        result = evaluate(inp)
        assert result.urgency == "RED"
        formatted = format_json(result)
        data = json.loads(formatted)
        assert data["urgency"] == "RED"

    def test_scenario_cat_single_vomit_energetic(self) -> None:
        """シナリオ: 猫+1回嘔吐+元気あり → GREEN。"""
        inp = build_symptom_input(
            species="猫",
            symptom_ids=["gi_vomit_single"],
        )
        result = evaluate(inp)
        assert result.urgency == "GREEN"

    def test_scenario_dog_diarrhea_slight_lethargy(self) -> None:
        """シナリオ: 犬+下痢+やや元気ない → YELLOW（安全側）。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["gi_diarrhea_single", "neuro_lethargy"],
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"

    def test_scenario_cat_urinary_emergency(self) -> None:
        """シナリオ: 猫+何度もトイレも尿出ない → RED。"""
        inp = build_symptom_input(
            species="猫",
            symptom_ids=["uro_obstruction"],
        )
        result = evaluate(inp)
        assert result.urgency == "RED"
        assert "すぐ" in result.owner_message or "早く" in result.owner_message

    def test_scenario_dog_bloat_vomiting(self) -> None:
        """シナリオ: 犬+腹部膨張+嘔吐 → RED（胃捻転疑い）。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["gi_bloat", "gi_vomit_persistent"],
        )
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_scenario_puppy_not_eating(self) -> None:
        """シナリオ: 子犬がミルクを飲まない → RED。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["age_puppy_milk_refusal"],
            age_group="puppy_kitten",
        )
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_scenario_senior_dog_walk_refusal(self) -> None:
        """シナリオ: 高齢犬が散歩拒否 → GREEN。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["age_senior_walk_refusal"],
            age_group="senior",
        )
        result = evaluate(inp)
        assert result.urgency == "GREEN"

    def test_scenario_full_pipeline_json(self) -> None:
        """シナリオ: フルパイプライン（入力→判定→JSON出力）。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["resp_dyspnea", "neuro_seizure"],
            onset_hours=1,
            age_group="adult",
            notes="ゴールデンレトリバー 5歳",
        )
        result = evaluate(inp)
        json_output = format_json(result)
        data = json.loads(json_output)

        assert data["urgency"] == "RED"
        assert len(data["matched_rules"]) >= 2
        assert len(data["symptom_details"]) == 2
        assert data["disclaimer"]

    def test_scenario_lethal_toxin(self) -> None:
        """シナリオ: 致死性毒物摂取 → RED。"""
        inp = build_symptom_input(
            species="猫",
            symptom_ids=["tox_known_lethal"],
        )
        result = evaluate(inp)
        assert result.urgency == "RED"

    def test_scenario_mild_itching(self) -> None:
        """シナリオ: 軽度の掻痒のみ → GREEN。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["derm_itching"],
        )
        result = evaluate(inp)
        assert result.urgency == "GREEN"

    def test_scenario_facial_swelling(self) -> None:
        """シナリオ: 顔面腫脹（アナフィラキシー疑い） → YELLOW。"""
        inp = build_symptom_input(
            species="犬",
            symptom_ids=["derm_facial_swelling"],
        )
        result = evaluate(inp)
        assert result.urgency == "YELLOW"


class TestCriticalAndUrgentSets:
    """CRITICAL/URGENT IDセットとterminologyの整合性テスト。"""

    def test_all_critical_ids_exist_in_terminology(self) -> None:
        """CRITICALセットの全IDがterminologyに存在する。"""
        all_ids = {s.id for s in get_all_symptoms()}
        for sid in CRITICAL_SYMPTOM_IDS:
            assert sid in all_ids, f"CRITICAL ID {sid} がterminologyに存在しない"

    def test_all_urgent_ids_exist_in_terminology(self) -> None:
        """URGENTセットの全IDがterminologyに存在する。"""
        all_ids = {s.id for s in get_all_symptoms()}
        for sid in URGENT_SYMPTOM_IDS:
            assert sid in all_ids, f"URGENT ID {sid} がterminologyに存在しない"

    def test_no_overlap_critical_urgent(self) -> None:
        """CRITICALとURGENTに重複がない。"""
        overlap = CRITICAL_SYMPTOM_IDS & URGENT_SYMPTOM_IDS
        assert len(overlap) == 0, f"CRITICALとURGENTに重複: {overlap}"

    def test_critical_symptoms_have_critical_severity(self) -> None:
        """CRITICALセットの症状はseverity='critical'である。"""
        for sid in CRITICAL_SYMPTOM_IDS:
            sym = get_symptom_by_id(sid)
            assert sym is not None, f"ID {sid} が見つからない"
            assert sym.severity == "critical", (
                f"{sid} は severity={sym.severity} だが critical であるべき"
            )

    def test_urgent_symptoms_have_urgent_severity(self) -> None:
        """URGENTセットの症状はseverity='urgent'である。"""
        for sid in URGENT_SYMPTOM_IDS:
            sym = get_symptom_by_id(sid)
            assert sym is not None, f"ID {sid} が見つからない"
            assert sym.severity == "urgent", (
                f"{sid} は severity={sym.severity} だが urgent であるべき"
            )


# ===========================================================================
# メイン
# ===========================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
