"""Interactive wizard for guiding users through business plan creation."""
from __future__ import annotations

from typing import Callable, Dict, List, Tuple

import streamlit as st

from utils import (
    FinancialInputs,
    calc_income_statement,
    generate_financial_narrative,
    save_encrypted_payload,
    validate_required_fields,
)


Renderer = Callable[[Dict[str, str]], Tuple[Dict[str, str], List[Tuple[str, str]]]]


def _render_overview_step(values: Dict[str, str]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    st.write(
        "企業アイデンティティを一気通貫で言語化し、投資家や金融機関へブレないメッセージを届けます。"
    )
    company_name = st.text_input(
        "会社名",
        value=values.get("company_name", ""),
        help="商号とブランドネーム。法人成り前は予定名でも構いません。",
        key="wizard_company_name",
    )
    vision = st.text_area(
        "ビジョン",
        value=values.get("vision", ""),
        help="3〜5年後のありたい姿を端的に。顧客・社会への価値提供を記述します。",
        height=120,
        key="wizard_vision",
    )
    mission = st.text_area(
        "ミッション",
        value=values.get("mission", ""),
        help="ビジョン実現のための存在意義を1〜2文で表現しましょう。",
        height=120,
        key="wizard_mission",
    )
    value_proposition = st.text_area(
        "バリュープロポジション",
        value=values.get("value_proposition", ""),
        help="顧客課題に対して提供する独自価値。プロダクトやサービス特徴ではなく効用を記述。",
        height=120,
        key="wizard_value_proposition",
    )
    target_market = st.text_area(
        "ターゲット市場",
        value=values.get("target_market", ""),
        help="主要顧客セグメント、規模、意思決定者像を具体的に示します。",
        height=120,
        key="wizard_target_market",
    )
    data = {
        "company_name": company_name,
        "vision": vision,
        "mission": mission,
        "value_proposition": value_proposition,
        "target_market": target_market,
    }
    required = [
        ("company_name", "会社名"),
        ("vision", "ビジョン"),
        ("mission", "ミッション"),
        ("value_proposition", "バリュープロポジション"),
    ]
    return data, required


def _render_three_c_step(values: Dict[str, str]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    st.write("3C分析で市場・競合・自社の立ち位置を俯瞰し、勝ち筋を特定します。")
    customer = st.text_area(
        "Customer｜顧客",
        value=values.get("customer", ""),
        help="顧客インサイト・購買動機・意思決定フローを具体的に記述します。",
        height=150,
        key="wizard_customer",
    )
    company = st.text_area(
        "Company｜自社",
        value=values.get("company", ""),
        help="経営資源・アセット・ケイパビリティを棚卸ししましょう。",
        height=150,
        key="wizard_company",
    )
    competitor = st.text_area(
        "Competitor｜競合",
        value=values.get("competitor", ""),
        help="直接・間接競合のポジショニングや価格帯、強み・弱みを整理します。",
        height=150,
        key="wizard_competitor",
    )
    data = {
        "customer": customer,
        "company": company,
        "competitor": competitor,
    }
    required = [("customer", "顧客"), ("company", "自社"), ("competitor", "競合")]
    return data, required


def _render_swot_step(values: Dict[str, str]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    st.write("SWOTのクロス分析で攻めと守りの戦略オプションを抽出します。")
    strengths = st.text_area(
        "Strengths｜強み",
        value=values.get("strengths", ""),
        help="他社に真似されにくいコアコンピタンスを明文化します。",
        height=130,
        key="wizard_strengths",
    )
    weaknesses = st.text_area(
        "Weaknesses｜弱み",
        value=values.get("weaknesses", ""),
        help="構造的課題やリソース不足を正直に洗い出します。",
        height=130,
        key="wizard_weaknesses",
    )
    opportunities = st.text_area(
        "Opportunities｜機会",
        value=values.get("opportunities", ""),
        help="市場成長、制度変更、顧客課題の顕在化などポジティブ要因を列挙。",
        height=130,
        key="wizard_opportunities",
    )
    threats = st.text_area(
        "Threats｜脅威",
        value=values.get("threats", ""),
        help="競争激化、規制強化、マクロ要因などリスク要素を可視化します。",
        height=130,
        key="wizard_threats",
    )
    data = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
    }
    required = [("strengths", "強み"), ("opportunities", "機会"), ("threats", "脅威")]
    return data, required


def _render_pest_step(values: Dict[str, str]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    st.write("マクロ環境をPESTの4視点で俯瞰し、シナリオプランニングを支えます。")
    political = st.text_area(
        "Political｜政治",
        value=values.get("political", ""),
        help="政策、規制、補助金動向など事業に影響する制度面を整理します。",
        height=120,
        key="wizard_political",
    )
    economic = st.text_area(
        "Economic｜経済",
        value=values.get("economic", ""),
        help="為替、金利、景気動向、業界特有の経済指標を記述。",
        height=120,
        key="wizard_economic",
    )
    social = st.text_area(
        "Social｜社会",
        value=values.get("social", ""),
        help="働き方、消費者マインド、人口動態など社会トレンドを示します。",
        height=120,
        key="wizard_social",
    )
    technological = st.text_area(
        "Technological｜技術",
        value=values.get("technological", ""),
        help="技術革新、デジタル化、特許動向などを整理しましょう。",
        height=120,
        key="wizard_technological",
    )
    data = {
        "political": political,
        "economic": economic,
        "social": social,
        "technological": technological,
    }
    required = [("political", "政治"), ("economic", "経済"), ("technological", "技術")]
    return data, required


def _render_four_p_step(values: Dict[str, str]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    st.write("マーケティング4Pで提供価値とチャネル戦略を統合設計します。")
    product = st.text_area(
        "Product",
        value=values.get("product", ""),
        help="サービス仕様、提供プロセス、差別化要素を具体的に。",
        height=110,
        key="wizard_product",
    )
    price = st.text_area(
        "Price",
        value=values.get("price", ""),
        help="価格モデル、収益性設計、値付けロジックを整理します。",
        height=110,
        key="wizard_price",
    )
    place = st.text_area(
        "Place",
        value=values.get("place", ""),
        help="販売チャネル、配送・導入プロセス、パートナー戦略を記述。",
        height=110,
        key="wizard_place",
    )
    promotion = st.text_area(
        "Promotion",
        value=values.get("promotion", ""),
        help="リード獲得と育成のアクションプランを明文化します。",
        height=110,
        key="wizard_promotion",
    )
    data = {
        "product": product,
        "price": price,
        "place": place,
        "promotion": promotion,
    }
    required = [("product", "Product"), ("price", "Price")]
    return data, required


def _render_financial_step(values: Dict[str, str]) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    st.write("財務KPIを入力すると損益計算書とサマリーを自動生成します。")
    cols = st.columns(2)
    with cols[0]:
        sales = st.number_input(
            "年間売上高",
            value=float(values.get("sales", 0.0)),
            min_value=0.0,
            step=1_000_000.0,
            help="単年の売上計画（税抜）。大口案件は別途メモを残すと精度が上がります。",
            key="wizard_sales",
        )
        cogs_rate = st.number_input(
            "売上原価率",
            value=float(values.get("cogs_rate", 0.4)),
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            help="材料費や外注費など変動費の比率。0.4なら売上の40%が原価。",
            key="wizard_cogs_rate",
        )
        personnel_cost = st.number_input(
            "人件費",
            value=float(values.get("personnel_cost", 0.0)),
            min_value=0.0,
            step=500_000.0,
            help="役員報酬・給与・賞与・社会保険料の合計。",
            key="wizard_personnel",
        )
        marketing_cost = st.number_input(
            "マーケティング費",
            value=float(values.get("marketing_cost", 0.0)),
            min_value=0.0,
            step=200_000.0,
            help="広告費・イベント費・広報制作費など。",
            key="wizard_marketing",
        )
        general_admin_cost = st.number_input(
            "一般管理費",
            value=float(values.get("general_admin_cost", 0.0)),
            min_value=0.0,
            step=200_000.0,
            help="家賃・水道光熱・通信・外注業務委託等の固定費。",
            key="wizard_admin",
        )
    with cols[1]:
        depreciation = st.number_input(
            "減価償却費",
            value=float(values.get("depreciation", 0.0)),
            min_value=0.0,
            step=100_000.0,
            help="設備・システム投資の按分費用。",
            key="wizard_depreciation",
        )
        other_income = st.number_input(
            "営業外収益",
            value=float(values.get("other_income", 0.0)),
            min_value=0.0,
            step=100_000.0,
            help="補助金、助成金、雑収入などの見込み。",
            key="wizard_other_income",
        )
        interest_payment = st.number_input(
            "支払利息",
            value=float(values.get("interest_payment", 0.0)),
            min_value=0.0,
            step=50_000.0,
            help="金融機関への利払い。変動金利は金利上昇リスクに注意。",
            key="wizard_interest",
        )
        tax_rate = st.number_input(
            "実効税率",
            value=float(values.get("tax_rate", 0.3)),
            min_value=0.0,
            max_value=0.6,
            step=0.01,
            help="法人税・住民税・事業税の実効税率。中小企業は0.25〜0.32が目安。",
            key="wizard_tax_rate",
        )
        initial_cash = st.number_input(
            "期首現金",
            value=float(values.get("initial_cash", 0.0)),
            min_value=0.0,
            step=500_000.0,
            help="前期繰越の現預金残高。",
            key="wizard_initial_cash",
        )
        capital_expenditure = st.number_input(
            "設備投資",
            value=float(values.get("capital_expenditure", 0.0)),
            min_value=0.0,
            step=500_000.0,
            help="今年予定する大きめの設備・システム投資額。",
            key="wizard_capex",
        )
    fiscal_year = st.number_input(
        "対象年度",
        value=int(values.get("fiscal_year", 2025)),
        min_value=2020,
        max_value=2100,
        step=1,
        help="計画対象の会計年度。",
        key="wizard_fiscal_year",
    )
    data = {
        "sales": sales,
        "cogs_rate": cogs_rate,
        "personnel_cost": personnel_cost,
        "marketing_cost": marketing_cost,
        "general_admin_cost": general_admin_cost,
        "depreciation": depreciation,
        "other_income": other_income,
        "interest_payment": interest_payment,
        "tax_rate": tax_rate,
        "initial_cash": initial_cash,
        "capital_expenditure": capital_expenditure,
        "fiscal_year": fiscal_year,
    }
    required = [("sales", "年間売上高"), ("cogs_rate", "売上原価率")]
    return data, required


STEP_FLOW: List[Tuple[str, str, str, Callable[[Dict[str, str]], Tuple[Dict[str, str], List[Tuple[str, str]]]]]] = [
    ("overview", "STEP1", "事業コンセプト", _render_overview_step),
    ("three_c", "STEP2", "3C分析", _render_three_c_step),
    ("swot", "STEP3", "SWOT分析", _render_swot_step),
    ("pest", "STEP4", "PEST分析", _render_pest_step),
    ("four_p", "STEP5", "4Pマーケティング", _render_four_p_step),
    ("financials", "STEP6", "財務計画", _render_financial_step),
]


def run_plan_wizard() -> None:
    """Launch the guided wizard for business plan preparation."""

    plan_data = st.session_state["plan_data"]
    step_index = st.session_state.get("wizard_step", 0)
    total_steps = len(STEP_FLOW)
    current_section, step_code, step_title, renderer = STEP_FLOW[step_index]

    st.markdown(
        """
        <div class="hero-banner">
            <h1>事業計画ウィザード</h1>
            <p>フレームワークごとの入力を順番にナビゲートし、整合性のとれた経営ストーリーを自動生成します。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress((step_index + 1) / total_steps)
    st.caption(f"{step_code}｜{step_title}")

    with st.form(f"wizard_form_{step_index}"):
        new_values, required = renderer(plan_data[current_section])
        col_back, col_save, col_next = st.columns(3)
        back_clicked = col_back.form_submit_button(
            "← 戻る",
            disabled=step_index == 0,
            use_container_width=True,
        )
        save_clicked = col_save.form_submit_button(
            "💾 保存",
            use_container_width=True,
        )
        next_label = "完了" if step_index == total_steps - 1 else "次へ →"
        next_clicked = col_next.form_submit_button(
            next_label,
            use_container_width=True,
        )

    if back_clicked or save_clicked or next_clicked:
        errors = validate_required_fields(new_values, required)
        if errors:
            for message in errors.values():
                st.error(message)
            return
        plan_data[current_section].update(new_values)
        st.session_state["plan_data"] = plan_data
        save_encrypted_payload(plan_data)

        if back_clicked:
            st.session_state["wizard_step"] = max(0, step_index - 1)
            st.experimental_rerun()
        elif next_clicked:
            if step_index == total_steps - 1:
                st.success("ウィザード完了。事業計画が更新されました。")
                st.session_state["wizard_step"] = 0
                st.session_state["show_wizard"] = False
            else:
                st.session_state["wizard_step"] = min(total_steps - 1, step_index + 1)
            st.experimental_rerun()
        else:
            st.success("保存しました。次のステップへ進む準備が整いました。")

    if current_section == "financials":
        financial_inputs = FinancialInputs(**plan_data["financials"])
        try:
            _, summary = calc_income_statement(financial_inputs)
            narrative = generate_financial_narrative(financial_inputs, summary)
            st.info(narrative)
        except ValueError as exc:
            st.warning(str(exc))

    st.button(
        "ウィザードを終了",
        on_click=lambda: st.session_state.update({"show_wizard": False, "wizard_step": 0}),
        type="secondary",
    )
