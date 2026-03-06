"""
用語辞書モジュール (terminology.py)

獣医療電話トリアージにおける症状・用語の体系的辞書。
信頼できる獣医学文献（Merck Veterinary Manual, PMC NIH, 森田動物医療センター等）に基づく。

情報源:
- XABCDE primary survey (Merck Veterinary Manual)
- 色分けトリアージ: Red/Orange/Yellow/Green (PMC NIH)
- 5段階コード: White/Green/Yellow/Red/Black (Veterinary Emergency of Midlothian)
- 日本語症状分類（森田動物医療センター）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# データ構造
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Symptom:
    """個別症状の定義。"""
    id: str
    name: str  # 日本語表記
    aliases: list[str] = field(default_factory=list)
    severity: str = "mild"  # "critical" | "urgent" | "mild"
    species_specific: str | None = None  # "dog" | "cat" | None(共通)
    age_specific: str | None = None  # "puppy_kitten" | "senior" | None(共通)
    description: str = ""


@dataclass(frozen=True)
class SymptomCategory:
    """症状カテゴリ。"""
    id: str
    label: str  # 日本語ラベル
    symptoms: list[Symptom] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 症状辞書（SSOT）
# ---------------------------------------------------------------------------

SYMPTOMS: dict[str, SymptomCategory] = {
    # ── 呼吸器 ──
    "respiratory": SymptomCategory(
        id="respiratory",
        label="呼吸器",
        symptoms=[
            Symptom(
                id="resp_dyspnea",
                name="呼吸困難",
                aliases=["息が荒い", "息が荒くて", "息苦しそう", "ハアハアしてる",
                         "呼吸が速い", "呼吸が浅い", "呼吸が速く浅い",
                         "息が苦しそう", "ゼーゼー"],
                severity="critical",
                description="異常に速い・浅い・努力性の呼吸",
            ),
            Symptom(
                id="resp_open_mouth",
                name="開口呼吸",
                aliases=["口を開けて呼吸", "口で息してる", "口をあけてハアハア",
                         "パンティング"],
                severity="critical",
                description="口を開けた状態での呼吸（猫では特に異常所見）",
            ),
            Symptom(
                id="resp_cough",
                name="咳",
                aliases=["せき", "咳き込む", "ケホケホ", "コンコン", "咳が出る"],
                severity="mild",
                description="軽度の咳。頻繁な場合はurgentへ昇格",
            ),
            Symptom(
                id="resp_cough_frequent",
                name="頻繁な咳",
                aliases=["ずっと咳してる", "咳が止まらない", "何度も咳"],
                severity="urgent",
                species_specific="dog",
                description="犬で持続的・頻繁な咳（心疾患、気管虚脱等の疑い）",
            ),
            Symptom(
                id="resp_cyanosis",
                name="チアノーゼ",
                aliases=["舌が紫", "歯茎が青い", "粘膜が青白い", "舌の色が悪い"],
                severity="critical",
                description="粘膜の青紫色変化。重度の低酸素を示す",
            ),
            Symptom(
                id="resp_nasal_discharge",
                name="鼻汁",
                aliases=["鼻水", "鼻がジュルジュル", "鼻から液体"],
                severity="mild",
                description="鼻からの分泌物",
            ),
            Symptom(
                id="resp_stridor",
                name="喘鳴",
                aliases=["ヒューヒュー", "ゼーゼー音", "呼吸に音がする",
                         "呼吸がゴロゴロ"],
                severity="urgent",
                description="呼吸時の異常音",
            ),
        ],
    ),

    # ── 神経・意識 ──
    "neurological": SymptomCategory(
        id="neurological",
        label="神経・意識",
        symptoms=[
            Symptom(
                id="neuro_seizure",
                name="けいれん",
                aliases=["痙攣", "ひきつけ", "ガクガク", "けいれんしてる",
                         "体がピクピク", "全身が震えてる"],
                severity="critical",
                description="全身性または部分性の発作",
            ),
            Symptom(
                id="neuro_seizure_cluster",
                name="けいれん重積",
                aliases=["けいれんが止まらない", "続けて痙攣", "何度もけいれん",
                         "けいれんが5分以上"],
                severity="critical",
                description="5分以上持続、または短時間に連続するけいれん",
            ),
            Symptom(
                id="neuro_collapse",
                name="虚脱・意識消失",
                aliases=["突然倒れた", "意識がない", "反応がない", "ぐったり",
                         "動かない", "起き上がれない", "立てない"],
                severity="critical",
                description="突然の虚脱または意識レベルの著しい低下",
            ),
            Symptom(
                id="neuro_ataxia",
                name="運動失調",
                aliases=["フラフラ", "よろよろ", "ふらつき", "まっすぐ歩けない",
                         "よろめく"],
                severity="urgent",
                description="歩行時のふらつき・協調運動障害",
            ),
            Symptom(
                id="neuro_head_tilt",
                name="斜頸",
                aliases=["首が傾いてる", "頭が傾く", "首を傾げたまま"],
                severity="urgent",
                description="頭部が一方に傾く（前庭疾患の疑い）",
            ),
            Symptom(
                id="neuro_lethargy",
                name="元気消失",
                aliases=["元気がない", "ぐったり", "だるそう", "動きたがらない",
                         "いつもと違う", "元気ない"],
                severity="mild",
                description="活動性の低下。他の症状との組み合わせで昇格",
            ),
            Symptom(
                id="neuro_tremor",
                name="震え",
                aliases=["ブルブル震えてる", "体が震える", "急に震え出した",
                         "ガタガタ震えてる"],
                severity="urgent",
                species_specific="dog",
                description="犬の突然の震え（中毒、低血糖、疼痛等の疑い）",
            ),
            Symptom(
                id="neuro_disorientation",
                name="見当識障害",
                aliases=["ぼーっとしてる", "あちこちぶつかる", "目が見えてない感じ",
                         "壁に向かって歩く"],
                severity="urgent",
                description="方向感覚の喪失・認識障害",
            ),
        ],
    ),

    # ── 消化器 ──
    "gastrointestinal": SymptomCategory(
        id="gastrointestinal",
        label="消化器",
        symptoms=[
            Symptom(
                id="gi_vomit_single",
                name="嘔吐（1回）",
                aliases=["1回吐いた", "吐いた", "嘔吐した"],
                severity="mild",
                description="単回の嘔吐。元気・食欲あれば様子見可",
            ),
            Symptom(
                id="gi_vomit_persistent",
                name="嘔吐（持続）",
                aliases=["何度も吐く", "吐き続ける", "24時間以上吐いてる",
                         "ずっと吐いてる", "繰り返し嘔吐"],
                severity="urgent",
                description="24時間以上の持続的嘔吐",
            ),
            Symptom(
                id="gi_vomit_blood",
                name="吐血",
                aliases=["血を吐いた", "吐いたものに血", "赤いものを吐いた",
                         "コーヒー色の嘔吐"],
                severity="critical",
                description="嘔吐物への血液混入",
            ),
            Symptom(
                id="gi_diarrhea_single",
                name="下痢（1回）",
                aliases=["1回下痢した", "軟便", "うんちがゆるい"],
                severity="mild",
                description="単回の下痢。元気あれば様子見可",
            ),
            Symptom(
                id="gi_diarrhea_persistent",
                name="下痢（持続）",
                aliases=["何度も下痢", "下痢が続く", "24時間以上下痢",
                         "ずっと下痢"],
                severity="urgent",
                description="24時間以上の持続的下痢",
            ),
            Symptom(
                id="gi_bloody_stool",
                name="血便",
                aliases=["血が混じったうんち", "便に血", "赤い便", "黒い便",
                         "タール便"],
                severity="urgent",
                description="便への血液混入（鮮血またはタール状）",
            ),
            Symptom(
                id="gi_anorexia",
                name="食欲不振",
                aliases=["ご飯食べない", "食欲がない", "食べない",
                         "フードを残す", "食べたがらない"],
                severity="mild",
                description="食欲の低下。24時間以上続く場合はurgentへ昇格",
            ),
            Symptom(
                id="gi_anorexia_24h",
                name="食欲不振（24時間以上）",
                aliases=["丸一日食べてない", "昨日から食べない",
                         "24時間以上食べてない"],
                severity="urgent",
                description="24時間以上の食欲廃絶",
            ),
            Symptom(
                id="gi_bloat",
                name="腹部膨張",
                aliases=["お腹が膨れてる", "お腹がパンパン", "腹が張ってる",
                         "お腹が大きくなった"],
                severity="urgent",
                species_specific="dog",
                description="犬の腹部膨張（胃拡張・胃捻転の疑い）",
            ),
            Symptom(
                id="gi_foreign_body",
                name="異物摂取",
                aliases=["何か食べた", "おもちゃ飲んだ", "異物を飲み込んだ",
                         "変なもの食べた", "ひもを食べた"],
                severity="urgent",
                description="異物の誤食・誤飲",
            ),
            Symptom(
                id="gi_dehydration",
                name="脱水",
                aliases=["水飲まない", "皮膚がつまめる", "口が乾いてる",
                         "おしっこが少ない"],
                severity="urgent",
                description="脱水の徴候",
            ),
        ],
    ),

    # ── 外傷 ──
    "trauma": SymptomCategory(
        id="trauma",
        label="外傷",
        symptoms=[
            Symptom(
                id="trauma_traffic",
                name="交通事故",
                aliases=["車にひかれた", "車にぶつかった", "轢かれた",
                         "交通事故にあった"],
                severity="critical",
                description="交通外傷。内臓損傷の可能性",
            ),
            Symptom(
                id="trauma_fall",
                name="高所落下",
                aliases=["落ちた", "ベランダから落ちた", "高いところから落ちた",
                         "2階から落ちた", "窓から落ちた"],
                severity="critical",
                description="高所からの落下（猫の高層症候群含む）",
            ),
            Symptom(
                id="trauma_bite",
                name="咬傷",
                aliases=["噛まれた", "犬に噛まれた", "猫に噛まれた",
                         "他の動物に噛まれた", "ケンカした"],
                severity="urgent",
                description="他の動物による咬傷",
            ),
            Symptom(
                id="trauma_bleeding_major",
                name="大量出血",
                aliases=["血が止まらない", "大量に出血", "血がたくさん出てる",
                         "血が噴き出てる"],
                severity="critical",
                description="止血困難な出血",
            ),
            Symptom(
                id="trauma_bleeding_minor",
                name="軽度出血",
                aliases=["少し血が出てる", "傷から血", "ちょっと出血"],
                severity="mild",
                description="軽度の出血（圧迫で止血可能）",
            ),
            Symptom(
                id="trauma_fracture",
                name="骨折疑い",
                aliases=["足を引きずってる", "足がブラブラ", "足をつけない",
                         "足が曲がってる", "歩けない"],
                severity="urgent",
                description="骨折が疑われる所見",
            ),
            Symptom(
                id="trauma_wound",
                name="創傷",
                aliases=["傷がある", "切り傷", "擦り傷", "皮膚が裂けてる"],
                severity="mild",
                description="軽度の創傷（深部組織に達しない）",
            ),
            Symptom(
                id="trauma_burn",
                name="熱傷・化学損傷",
                aliases=["やけどした", "火傷", "熱いものに触れた",
                         "薬品がかかった"],
                severity="urgent",
                description="熱傷または化学物質による損傷",
            ),
        ],
    ),

    # ── 泌尿生殖器 ──
    "urogenital": SymptomCategory(
        id="urogenital",
        label="泌尿生殖器",
        symptoms=[
            Symptom(
                id="uro_obstruction",
                name="排尿不能",
                aliases=["おしっこが出ない", "トイレで鳴く", "何度もトイレに行くが出ない",
                         "尿が出ない", "頻繁にトイレも尿出ない"],
                severity="critical",
                species_specific="cat",
                description="猫の尿路閉塞。緊急度最高",
            ),
            Symptom(
                id="uro_straining",
                name="排尿困難",
                aliases=["おしっこしにくそう", "いきんでる", "排尿に時間がかかる",
                         "しぶり"],
                severity="urgent",
                description="排尿時の努責・不快感",
            ),
            Symptom(
                id="uro_hematuria",
                name="血尿",
                aliases=["おしっこに血", "赤いおしっこ", "ピンクのおしっこ"],
                severity="urgent",
                description="尿への血液混入",
            ),
            Symptom(
                id="uro_polyuria",
                name="多飲多尿",
                aliases=["水をたくさん飲む", "おしっこの量が多い", "頻尿",
                         "やたら水を飲む"],
                severity="mild",
                description="飲水量・排尿量の増加",
            ),
            Symptom(
                id="uro_vaginal_discharge",
                name="陰部からの分泌物",
                aliases=["陰部から膿", "おまたから出血", "陰部が腫れてる"],
                severity="urgent",
                description="陰部からの異常分泌（子宮蓄膿症の疑い）",
            ),
            Symptom(
                id="uro_dystocia",
                name="難産",
                aliases=["産めない", "陣痛が続いてるのに出てこない",
                         "出産が進まない"],
                severity="critical",
                description="分娩の停滞。緊急帝王切開の可能性",
            ),
        ],
    ),

    # ── 温度異常 ──
    "temperature": SymptomCategory(
        id="temperature",
        label="温度異常",
        symptoms=[
            Symptom(
                id="temp_heatstroke",
                name="熱中症",
                aliases=["暑さでぐったり", "高体温", "日射病", "熱射病",
                         "パンティングが止まらない", "よだれが大量",
                         "荒い呼吸で高体温"],
                severity="critical",
                description="高体温（>40.5度）+ 意識障害・嘔吐等",
            ),
            Symptom(
                id="temp_hypothermia",
                name="低体温",
                aliases=["体が冷たい", "ぐったりして冷たい", "震えて冷たい"],
                severity="critical",
                description="低体温（<37度）。子犬・子猫で特に危険",
            ),
            Symptom(
                id="temp_fever",
                name="発熱",
                aliases=["熱がある", "体が熱い", "耳が熱い", "鼻が乾いて熱い"],
                severity="mild",
                description="発熱の疑い。他の症状との組み合わせで昇格",
            ),
            Symptom(
                id="temp_drooling",
                name="よだれ（異常）",
                aliases=["よだれが止まらない", "大量のよだれ", "涎が多い",
                         "口からよだれ"],
                severity="urgent",
                description="異常なよだれ（中毒、熱中症、口腔疾患等）",
            ),
        ],
    ),

    # ── 眼科 ──
    "eye": SymptomCategory(
        id="eye",
        label="眼科",
        symptoms=[
            Symptom(
                id="eye_closed",
                name="眼瞼閉鎖",
                aliases=["目が開かない", "目を開けない", "目をつぶってる",
                         "片目が開かない"],
                severity="urgent",
                description="眼瞼の閉鎖（角膜潰瘍、眼内圧上昇等の疑い）",
            ),
            Symptom(
                id="eye_opacity",
                name="角膜白濁",
                aliases=["目が白い", "目が濁ってる", "白濁", "目が曇ってる"],
                severity="urgent",
                description="角膜の白濁（緑内障、角膜潰瘍等の疑い）",
            ),
            Symptom(
                id="eye_redness",
                name="充血",
                aliases=["目が赤い", "白目が赤い", "充血してる"],
                severity="mild",
                description="結膜・強膜の充血",
            ),
            Symptom(
                id="eye_discharge",
                name="目やに",
                aliases=["目やにが多い", "目から膿", "涙が多い", "目がベタベタ"],
                severity="mild",
                description="軽度の眼脂。膿性の場合はurgent",
            ),
            Symptom(
                id="eye_proptosis",
                name="眼球突出",
                aliases=["目が飛び出てる", "目が出てる", "眼球が出た"],
                severity="critical",
                description="眼球の突出（外傷性または緑内障性）",
            ),
            Symptom(
                id="eye_prolapse",
                name="眼球脱出",
                aliases=["目が外に出た", "目が完全に出てしまった"],
                severity="critical",
                description="眼球の完全脱出。緊急手術の可能性",
            ),
        ],
    ),

    # ── 中毒 ──
    "toxicology": SymptomCategory(
        id="toxicology",
        label="中毒",
        symptoms=[
            Symptom(
                id="tox_ingestion",
                name="毒物摂取",
                aliases=["チョコ食べた", "ユリを食べた", "薬を飲んだ",
                         "洗剤を舐めた", "殺虫剤", "不凍液",
                         "ぶどう食べた", "キシリトール", "タマネギ食べた",
                         "ネギ食べた", "人間の薬"],
                severity="urgent",
                description="中毒を起こす可能性のある物質の摂取",
            ),
            Symptom(
                id="tox_known_lethal",
                name="致死性毒物摂取",
                aliases=["不凍液飲んだ", "ユリを食べた猫", "殺鼠剤食べた"],
                severity="critical",
                description="致死性の高い毒物の摂取（不凍液、ユリ[猫]、殺鼠剤等）",
            ),
        ],
    ),

    # ── 循環器 ──
    "cardiovascular": SymptomCategory(
        id="cardiovascular",
        label="循環器",
        symptoms=[
            Symptom(
                id="cv_pale_gums",
                name="粘膜蒼白",
                aliases=["歯茎が白い", "白い歯茎", "歯茎の色が薄い",
                         "舌が白い", "粘膜が白い"],
                severity="critical",
                species_specific="dog",
                description="粘膜の蒼白化（貧血、ショック、内出血の疑い）",
            ),
            Symptom(
                id="cv_weak_pulse",
                name="脈拍微弱",
                aliases=["脈が弱い", "脈が取りにくい"],
                severity="critical",
                description="脈拍の微弱化（ショックの疑い）",
            ),
            Symptom(
                id="cv_collapse_exercise",
                name="運動時虚脱",
                aliases=["散歩中に倒れた", "運動したら倒れた", "走ったら動けなくなった"],
                severity="critical",
                description="運動に伴う虚脱（心疾患の疑い）",
            ),
        ],
    ),

    # ── 年齢特異症状 ──
    "age_specific": SymptomCategory(
        id="age_specific",
        label="年齢特異",
        symptoms=[
            Symptom(
                id="age_puppy_lethargy",
                name="子犬子猫の元気消失",
                aliases=["子犬がぐったり", "子猫がぐったり", "仔犬が元気ない",
                         "仔猫が元気ない"],
                severity="critical",
                age_specific="puppy_kitten",
                description="子犬・子猫の急な元気消失は低血糖・感染症等の疑い",
            ),
            Symptom(
                id="age_puppy_milk_refusal",
                name="ミルク拒否",
                aliases=["ミルクを飲まない", "母乳を飲まない", "哺乳しない",
                         "ミルク拒否"],
                severity="critical",
                age_specific="puppy_kitten",
                description="新生子のミルク拒否は急速に悪化する",
            ),
            Symptom(
                id="age_puppy_hypothermia",
                name="子犬子猫の低体温",
                aliases=["子犬が冷たい", "子猫が冷たい", "赤ちゃんが冷たい"],
                severity="critical",
                age_specific="puppy_kitten",
                description="新生子の低体温は致死的",
            ),
            Symptom(
                id="age_senior_walk_refusal",
                name="散歩拒否（高齢）",
                aliases=["散歩に行きたがらない", "歩きたがらない"],
                severity="mild",
                age_specific="senior",
                description="高齢犬の散歩拒否（関節疾患等の疑い）",
            ),
            Symptom(
                id="age_senior_stair_avoidance",
                name="階段回避（高齢）",
                aliases=["階段を上がらない", "階段を降りない", "段差を嫌がる"],
                severity="mild",
                age_specific="senior",
                description="高齢犬の階段回避（整形外科的疾患の疑い）",
            ),
        ],
    ),

    # ── 猫特有 ──
    "cat_specific": SymptomCategory(
        id="cat_specific",
        label="猫特有",
        symptoms=[
            Symptom(
                id="cat_hiding",
                name="隠れて出てこない",
                aliases=["隠れたまま出てこない", "押し入れから出ない",
                         "ベッドの下にいる", "いつもの場所にいない"],
                severity="urgent",
                species_specific="cat",
                description="猫が隠れて出てこない（疼痛・体調不良のサイン）",
            ),
            Symptom(
                id="cat_open_mouth_breathing",
                name="猫の開口呼吸",
                aliases=["猫が口で呼吸", "猫がハアハア"],
                severity="critical",
                species_specific="cat",
                description="猫の開口呼吸は犬と異なり常に異常所見",
            ),
            Symptom(
                id="cat_hindlimb_paralysis",
                name="後肢麻痺",
                aliases=["後ろ足が動かない", "後ろ足を引きずってる",
                         "後ろ足が冷たい", "突然歩けなくなった"],
                severity="critical",
                species_specific="cat",
                description="猫の急性後肢麻痺（動脈血栓塞栓症の疑い）",
            ),
        ],
    ),

    # ── 犬特有 ──
    "dog_specific": SymptomCategory(
        id="dog_specific",
        label="犬特有",
        symptoms=[
            Symptom(
                id="dog_gdv",
                name="胃捻転疑い",
                aliases=["お腹パンパンで吐く", "腹部膨張と嘔吐",
                         "お腹が膨れて苦しそう", "吐こうとするが出ない"],
                severity="critical",
                species_specific="dog",
                description="胃拡張・胃捻転症候群の疑い。大型犬で特に注意",
            ),
            Symptom(
                id="dog_reverse_sneeze",
                name="逆くしゃみ",
                aliases=["フガフガ", "ブーブー鳴る", "鼻を鳴らす"],
                severity="mild",
                species_specific="dog",
                description="逆くしゃみ（通常は無害だが持続する場合は受診）",
            ),
        ],
    ),

    # ── 皮膚 ──
    "dermatological": SymptomCategory(
        id="dermatological",
        label="皮膚",
        symptoms=[
            Symptom(
                id="derm_itching",
                name="掻痒",
                aliases=["かゆがってる", "体を掻いてる", "ずっと掻いてる"],
                severity="mild",
                description="掻痒感。通常は緊急ではない",
            ),
            Symptom(
                id="derm_swelling",
                name="腫脹",
                aliases=["腫れてる", "パンパンに腫れた", "ふくらんでる",
                         "しこりがある"],
                severity="mild",
                description="局所的な腫脹",
            ),
            Symptom(
                id="derm_facial_swelling",
                name="顔面腫脹",
                aliases=["顔が腫れた", "まぶたが腫れた", "口が腫れてる",
                         "蜂に刺された"],
                severity="urgent",
                description="顔面の腫脹（アナフィラキシー、蜂刺傷等の疑い）",
            ),
            Symptom(
                id="derm_hives",
                name="蕁麻疹",
                aliases=["ボツボツ", "ブツブツが出た", "全身に発疹"],
                severity="urgent",
                description="蕁麻疹・全身性発疹（アレルギー反応の疑い）",
            ),
        ],
    ),
}


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

def get_all_symptoms() -> list[Symptom]:
    """全カテゴリの全症状をフラットなリストで返す。"""
    result: list[Symptom] = []
    for cat in SYMPTOMS.values():
        result.extend(cat.symptoms)
    return result


def get_symptom_by_id(symptom_id: str) -> Symptom | None:
    """症状IDで検索。見つからなければNone。"""
    for cat in SYMPTOMS.values():
        for sym in cat.symptoms:
            if sym.id == symptom_id:
                return sym
    return None


def get_symptoms_by_severity(severity: str) -> list[Symptom]:
    """指定された重症度の全症状を返す。"""
    return [s for s in get_all_symptoms() if s.severity == severity]


def get_symptoms_for_species(species: str) -> list[Symptom]:
    """指定動物種に該当する症状（共通+種特異）を返す。

    Args:
        species: "dog" or "cat"
    """
    return [
        s for s in get_all_symptoms()
        if s.species_specific is None or s.species_specific == species
    ]


def get_symptoms_for_age(age_group: str) -> list[Symptom]:
    """指定年齢群に該当する症状（共通+年齢特異）を返す。

    Args:
        age_group: "puppy_kitten", "adult", or "senior"
    """
    return [
        s for s in get_all_symptoms()
        if s.age_specific is None or s.age_specific == age_group
    ]


def search_by_alias(text: str) -> list[Symptom]:
    """テキストからaliasマッチで症状を検索する。

    部分一致で検索し、マッチした症状のリストを返す。

    Args:
        text: 飼い主が述べた症状テキスト
    """
    text_lower = text.lower()
    matched: list[Symptom] = []
    seen_ids: set[str] = set()
    for sym in get_all_symptoms():
        if sym.id in seen_ids:
            continue
        # 名前での完全一致/部分一致
        if sym.name in text:
            matched.append(sym)
            seen_ids.add(sym.id)
            continue
        # aliasでの部分一致
        for alias in sym.aliases:
            if alias in text or alias.lower() in text_lower:
                matched.append(sym)
                seen_ids.add(sym.id)
                break
    return matched


def get_category_list() -> list[dict[str, str]]:
    """カテゴリ一覧を返す（UI表示用）。"""
    return [
        {"id": cat.id, "label": cat.label}
        for cat in SYMPTOMS.values()
    ]


def get_symptoms_in_category(category_id: str) -> list[Symptom]:
    """指定カテゴリの症状一覧を返す。"""
    cat = SYMPTOMS.get(category_id)
    if cat is None:
        return []
    return list(cat.symptoms)


# ---------------------------------------------------------------------------
# 免責事項
# ---------------------------------------------------------------------------

DISCLAIMER = (
    "【免責事項】このツールは電話トリアージの参考補助を目的としており、"
    "獣医師による診断の代替ではありません。最終的な判断は必ず獣医師が行ってください。"
    "緊急性に疑いがある場合は、常に安全側（より高い緊急度）に判断してください。"
)
