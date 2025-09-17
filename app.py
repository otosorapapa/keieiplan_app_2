from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, Tuple

import pandas as pd
import streamlit as st

from accounting import AccountingConfig, AccountingConnector, render_accounting_preview
from export import export_plan_to_excel, export_plan_to_pdf, export_plan_to_ppt
from forecast import render_forecast_section
from milestones import render_milestone_manager
from onboarding import show_onboarding_tour
from styles import inject_custom_style, section_header
from utils import (
    FinancialInputs,
    calc_cashflow_projection,
    calc_income_statement,
    format_currency,
    format_percentage,
    generate_financial_narrative,
    initialize_session_state,
    plan_to_financial_inputs,
    save_encrypted_payload,
    validate_required_fields,
)
from wizard import run_plan_wizard


NAVIGATION_OPTIONS = [
    "概要",
    "3C分析",
    "SWOT分析",
    "PEST分析",
    "4P",
    "財務計画",
    "マイルストーン",
    "進捗ダッシュボード",
]


def process_actions(
    section_key: str,
    new_values: Dict[str, str | float],
    required: Iterable[Tuple[str, str]] = (),
    *,
    back_clicked: bool,
    save_clicked: bool,
    next_clicked: bool,
    back_target: str | None = None,
    next_target: str | None = None,
) -> None:
    if not (back_clicked or save_clicked or next_clicked):
        return

    errors = validate_required_fields(new_values, required)
    if errors:
        for message in errors.values():
            st.error(message)
        return

    st.session_state["plan_data"][section_key].update(new_values)
    save_encrypted_payload(st.session_state["plan_data"])

    if save_clicked:
        st.success("保存しました。")
    if back_clicked and back_target:
        st.session_state["navigation"] = back_target
        st.experimental_rerun()
    if next_clicked and next_target:
        st.session_state["navigation"] = next_target
        st.experimental_rerun()


def render_overview(income_statement: pd.DataFrame, narrative: str, forecast_df: pd.DataFrame) -> None:
    section_header("Overview", "ビジョン・ミッションを整理し、戦略ストーリーの土台を固めます。")
    overview = st.session_state["plan_data"]["overview"]

    with st.form("overview_form"):
        company_name = st.text_input(
            "会社名",
            value=overview.get("company_name", ""),
            help="法人名または屋号。金融機関への提出資料にそのまま表示されます。",
        )
        vision = st.text_area(
            "ビジョン",
            value=overview.get("vision", ""),
            help="3〜5年後のありたい姿を端的に記述します。",
            height=120,
        )
        mission = st.text_area(
            "ミッション",
            value=overview.get("mission", ""),
            help="存在意義・提供価値。組織内で共有したいキーメッセージ。",
            height=120,
        )
        value_proposition = st.text_area(
            "バリュープロポジション",
            value=overview.get("value_proposition", ""),
            help="顧客課題と提供価値のフィット感を明文化します。",
            height=120,
        )
        target_market = st.text_area(
            "ターゲット市場",
            value=overview.get("target_market", ""),
            help="主要顧客セグメントや案件規模を定義。",
            height=120,
        )
        col_back, col_save, col_next = st.columns(3)
        back_clicked = col_back.form_submit_button("← 戻る", disabled=True, use_container_width=True)
        save_clicked = col_save.form_submit_button("💾 保存", use_container_width=True)
        next_clicked = col_next.form_submit_button("次へ →", use_container_width=True)

    new_values = {
        "company_name": company_name,
        "vision": vision,
        "mission": mission,
        "value_proposition": value_proposition,
        "target_market": target_market,
    }
    process_actions(
        "overview",
        new_values,
        (
            ("company_name", "会社名"),
            ("vision", "ビジョン"),
            ("mission", "ミッション"),
            ("value_proposition", "バリュープロポジション"),
        ),
        back_clicked=back_clicked,
        save_clicked=save_clicked,
        next_clicked=next_clicked,
        next_target="3C分析",
    )

    if narrative:
        st.info(narrative)
    if not income_statement.empty:
        st.dataframe(income_statement, use_container_width=True)

    milestones_state = st.session_state.get("milestones")
    if isinstance(milestones_state, pd.DataFrame):
        milestones_df = milestones_state.copy()
    else:
        milestones_df = pd.DataFrame(milestones_state or [])
    if forecast_df.empty:
        st.caption("シナリオ分析を実行すると売上予測が表示されます。")
    else:
        chart_df = forecast_df.pivot(index="月", columns="シナリオ", values="売上")
        st.line_chart(chart_df, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    excel_bytes = export_plan_to_excel(
        st.session_state["plan_data"], income_statement, forecast_df, milestones_df
    )
    col1.download_button(
        "Excel出力",
        data=excel_bytes,
        file_name="business_plan.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    pdf_bytes = export_plan_to_pdf(st.session_state["plan_data"], narrative, income_statement)
    col2.download_button(
        "PDF出力",
        data=pdf_bytes,
        file_name="business_plan.pdf",
        mime="application/pdf",
    )
    ppt_bytes = export_plan_to_ppt(st.session_state["plan_data"], narrative, income_statement)
    col3.download_button(
        "PowerPoint出力",
        data=ppt_bytes,
        file_name="business_plan.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


def render_three_c() -> None:
    section_header("3C分析", "市場・競合・自社の視点から勝ち筋を抽出します。")
    data = st.session_state["plan_data"]["three_c"]
    with st.form("three_c_form"):
        customer = st.text_area(
            "Customer",
            value=data.get("customer", ""),
            help="顧客インサイト、意思決定プロセス、未充足ニーズを記述。",
            height=150,
        )
        company = st.text_area(
            "Company",
            value=data.get("company", ""),
            help="提供価値の源泉、組織能力、独自資産を明文化します。",
            height=150,
        )
        competitor = st.text_area(
            "Competitor",
            value=data.get("competitor", ""),
            help="直接・間接競合のポジショニングと差別化要素。",
            height=150,
        )
        col_back, col_save, col_next = st.columns(3)
        back_clicked = col_back.form_submit_button("← 戻る", use_container_width=True)
        save_clicked = col_save.form_submit_button("💾 保存", use_container_width=True)
        next_clicked = col_next.form_submit_button("次へ →", use_container_width=True)
    new_values = {
        "customer": customer,
        "company": company,
        "competitor": competitor,
    }
    process_actions(
        "three_c",
        new_values,
        (("customer", "顧客"), ("company", "自社"), ("competitor", "競合")),
        back_clicked=back_clicked,
        save_clicked=save_clicked,
        next_clicked=next_clicked,
        back_target="概要",
        next_target="SWOT分析",
    )


def render_swot() -> None:
    section_header("SWOT分析", "内部資源と外部機会のクロスで戦略シナリオを描きます。")
    data = st.session_state["plan_data"]["swot"]
    with st.form("swot_form"):
        strengths = st.text_area(
            "Strengths",
            value=data.get("strengths", ""),
            help="競争優位性や独自の資産を明記します。",
            height=120,
        )
        weaknesses = st.text_area(
            "Weaknesses",
            value=data.get("weaknesses", ""),
            help="組織やプロダクトの改善余地。",
            height=120,
        )
        opportunities = st.text_area(
            "Opportunities",
            value=data.get("opportunities", ""),
            help="市場トレンド、政策、技術変化などポジティブ要素。",
            height=120,
        )
        threats = st.text_area(
            "Threats",
            value=data.get("threats", ""),
            help="競争激化、法規制、マクロリスク等。",
            height=120,
        )
        col_back, col_save, col_next = st.columns(3)
        back_clicked = col_back.form_submit_button("← 戻る", use_container_width=True)
        save_clicked = col_save.form_submit_button("💾 保存", use_container_width=True)
        next_clicked = col_next.form_submit_button("次へ →", use_container_width=True)
    new_values = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
    }
    process_actions(
        "swot",
        new_values,
        (("strengths", "強み"), ("opportunities", "機会"), ("threats", "脅威")),
        back_clicked=back_clicked,
        save_clicked=save_clicked,
        next_clicked=next_clicked,
        back_target="3C分析",
        next_target="PEST分析",
    )


def render_pest() -> None:
    section_header("PEST分析", "マクロ環境を四象限で捉え、外部シナリオを準備します。")
    data = st.session_state["plan_data"]["pest"]
    with st.form("pest_form"):
        political = st.text_area(
            "Political",
            value=data.get("political", ""),
            help="政策・規制・補助金の動向。",
            height=110,
        )
        economic = st.text_area(
            "Economic",
            value=data.get("economic", ""),
            help="景気動向、為替、金利、業界固有指標。",
            height=110,
        )
        social = st.text_area(
            "Social",
            value=data.get("social", ""),
            help="人口動態、価値観、働き方など社会的要素。",
            height=110,
        )
        technological = st.text_area(
            "Technological",
            value=data.get("technological", ""),
            help="技術革新やデジタル化の潮流。",
            height=110,
        )
        col_back, col_save, col_next = st.columns(3)
        back_clicked = col_back.form_submit_button("← 戻る", use_container_width=True)
        save_clicked = col_save.form_submit_button("💾 保存", use_container_width=True)
        next_clicked = col_next.form_submit_button("次へ →", use_container_width=True)
    new_values = {
        "political": political,
        "economic": economic,
        "social": social,
        "technological": technological,
    }
    process_actions(
        "pest",
        new_values,
        (("political", "政治"), ("economic", "経済"), ("technological", "技術")),
        back_clicked=back_clicked,
        save_clicked=save_clicked,
        next_clicked=next_clicked,
        back_target="SWOT分析",
        next_target="4P",
    )


def render_four_p() -> None:
    section_header("4Pマーケティング", "マーケティングミックスを統合し、実行計画へ落とし込みます。")
    data = st.session_state["plan_data"]["four_p"]
    with st.form("four_p_form"):
        product = st.text_area(
            "Product",
            value=data.get("product", ""),
            help="サービス仕様、UX、差別化ポイント。",
            height=110,
        )
        price = st.text_area(
            "Price",
            value=data.get("price", ""),
            help="収益モデル、値付け戦略、ディスカウント方針。",
            height=110,
        )
        place = st.text_area(
            "Place",
            value=data.get("place", ""),
            help="販売チャネル、供給体制、物流設計。",
            height=110,
        )
        promotion = st.text_area(
            "Promotion",
            value=data.get("promotion", ""),
            help="リード獲得、育成、ブランディング施策。",
            height=110,
        )
        col_back, col_save, col_next = st.columns(3)
        back_clicked = col_back.form_submit_button("← 戻る", use_container_width=True)
        save_clicked = col_save.form_submit_button("💾 保存", use_container_width=True)
        next_clicked = col_next.form_submit_button("次へ →", use_container_width=True)
    new_values = {
        "product": product,
        "price": price,
        "place": place,
        "promotion": promotion,
    }
    process_actions(
        "four_p",
        new_values,
        (("product", "Product"), ("price", "Price")),
        back_clicked=back_clicked,
        save_clicked=save_clicked,
        next_clicked=next_clicked,
        back_target="PEST分析",
        next_target="財務計画",
    )


def render_financial_section(
    financial_inputs: FinancialInputs,
    income_statement: pd.DataFrame,
    summary: Dict[str, float],
    cashflow_df: pd.DataFrame,
) -> None:
    section_header("財務計画", "収益性とキャッシュを両面でマネジメントします。")
    data = st.session_state["plan_data"]["financials"]
    with st.form("financial_form"):
        col_left, col_right = st.columns(2)
        with col_left:
            sales = st.number_input(
                "年間売上高",
                value=float(data.get("sales", 0.0)),
                min_value=0.0,
                step=1_000_000.0,
                help="想定する年間売上高（税抜）。",
            )
            cogs_rate = st.number_input(
                "売上原価率",
                value=float(data.get("cogs_rate", 0.0)),
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                help="材料費・外注費など変動費の割合。",
            )
            personnel_cost = st.number_input(
                "人件費",
                value=float(data.get("personnel_cost", 0.0)),
                min_value=0.0,
                step=500_000.0,
                help="給与・賞与・社会保険料など。",
            )
            marketing_cost = st.number_input(
                "マーケティング費",
                value=float(data.get("marketing_cost", 0.0)),
                min_value=0.0,
                step=200_000.0,
                help="広告宣伝や展示会費用。",
            )
            general_admin_cost = st.number_input(
                "一般管理費",
                value=float(data.get("general_admin_cost", 0.0)),
                min_value=0.0,
                step=200_000.0,
                help="家賃・水道光熱・システム費など固定費。",
            )
        with col_right:
            depreciation = st.number_input(
                "減価償却費",
                value=float(data.get("depreciation", 0.0)),
                min_value=0.0,
                step=100_000.0,
                help="設備・システム投資の償却費。",
            )
            other_income = st.number_input(
                "営業外収益",
                value=float(data.get("other_income", 0.0)),
                min_value=0.0,
                step=100_000.0,
                help="補助金・助成金などの収益。",
            )
            interest_payment = st.number_input(
                "支払利息",
                value=float(data.get("interest_payment", 0.0)),
                min_value=0.0,
                step=50_000.0,
                help="借入金の利息支払い。",
            )
            tax_rate = st.number_input(
                "実効税率",
                value=float(data.get("tax_rate", 0.3)),
                min_value=0.0,
                max_value=0.6,
                step=0.01,
                help="法人税等の実効税率。",
            )
            initial_cash = st.number_input(
                "期首現金",
                value=float(data.get("initial_cash", 0.0)),
                min_value=0.0,
                step=500_000.0,
                help="期首の現預金残高。",
            )
            capital_expenditure = st.number_input(
                "設備投資",
                value=float(data.get("capital_expenditure", 0.0)),
                min_value=0.0,
                step=500_000.0,
                help="今年予定している投資額。",
            )
        fiscal_year = st.number_input(
            "対象年度",
            value=int(data.get("fiscal_year", 2024)),
            min_value=2020,
            max_value=2100,
            step=1,
            help="計画対象となる会計年度。",
        )
        col_back, col_save, col_next = st.columns(3)
        back_clicked = col_back.form_submit_button("← 戻る", use_container_width=True)
        save_clicked = col_save.form_submit_button("💾 保存", use_container_width=True)
        next_clicked = col_next.form_submit_button("次へ →", use_container_width=True)

    new_values = {
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
    process_actions(
        "financials",
        new_values,
        (("sales", "年間売上高"), ("cogs_rate", "売上原価率")),
        back_clicked=back_clicked,
        save_clicked=save_clicked,
        next_clicked=next_clicked,
        back_target="4P",
        next_target="マイルストーン",
    )

    if income_statement.empty or not summary:
        st.warning("財務指標に異常値が含まれています。入力値をご確認ください。")
    else:
        st.dataframe(income_statement, use_container_width=True)
        metrics = st.columns(4)
        metrics[0].metric("営業利益率", format_percentage(summary["operating_margin"]))
        metrics[1].metric("経常利益率", format_percentage(summary["ordinary_margin"]))
        break_even = summary.get("break_even_sales")
        if break_even is None or pd.isna(break_even):
            break_even = 0.0
        metrics[2].metric("損益分岐点売上高", format_currency(break_even))
        labor_ratio = summary.get("labor_distribution_ratio")
        labor_ratio = 0 if labor_ratio is None or pd.isna(labor_ratio) else labor_ratio
        metrics[3].metric("労働分配率", format_percentage(labor_ratio))

    forecast_df = render_forecast_section(financial_inputs)
    st.session_state["forecast_df"] = forecast_df

    if not cashflow_df.empty:
        st.line_chart(cashflow_df.set_index("月")["累計現金残高"], height=320)


def render_dashboard(
    income_statement: pd.DataFrame,
    summary: Dict[str, float],
    cashflow_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    milestones_df: pd.DataFrame,
) -> None:
    section_header("進捗ダッシュボード", "KPIとキャッシュ状況を定点観測します。")
    if income_statement.empty:
        st.warning("財務データが不足しています。『財務計画』タブを更新してください。")
        return

    kpi_columns = st.columns(4)
    kpi_columns[0].metric("売上高", format_currency(income_statement.loc[0, "金額"]))
    kpi_columns[1].metric("営業利益", format_currency(summary["operating_profit"]))
    kpi_columns[2].metric("当期純利益", format_currency(summary["net_income"]))
    kpi_columns[3].metric("営業利益率", format_percentage(summary["operating_margin"]))

    if not cashflow_df.empty:
        st.area_chart(cashflow_df.set_index("月")[["営業キャッシュフロー", "累計現金残高"]])

    if not milestones_df.empty:
        progress = milestones_df["進捗率"].mean()
        st.metric("平均進捗率", f"{progress:.1f}%")
    else:
        st.caption("マイルストーン情報が未入力です。")

    connector = AccountingConnector(AccountingConfig(provider="dummy"))
    render_accounting_preview(connector)


def main() -> None:
    st.set_page_config(page_title="統合経営計画ダッシュボード", page_icon="📊", layout="wide")
    inject_custom_style()
    initialize_session_state()
    show_onboarding_tour()

    st.sidebar.title("ナビゲーション")
    nav = st.sidebar.radio("メニュー", NAVIGATION_OPTIONS, key="navigation")
    if st.sidebar.button("ウィザードを起動", use_container_width=True):
        st.session_state["show_wizard"] = True
    st.sidebar.caption("入力内容は暗号化してローカル保存されます。")

    if st.session_state.get("show_wizard"):
        run_plan_wizard()
        return

    plan_data = st.session_state["plan_data"]
    financial_inputs = plan_to_financial_inputs(plan_data)
    income_statement = pd.DataFrame()
    summary: Dict[str, float] = {}
    narrative = ""
    cashflow_df = pd.DataFrame()
    try:
        income_statement, summary = calc_income_statement(financial_inputs)
        narrative = generate_financial_narrative(financial_inputs, summary)
        cashflow_df = calc_cashflow_projection(financial_inputs)
    except ValueError as exc:
        st.warning(str(exc))

    forecast_df = st.session_state.get("forecast_df", pd.DataFrame())
    milestones_state = st.session_state.get("milestones")
    if isinstance(milestones_state, pd.DataFrame):
        milestones_df = milestones_state.copy()
    else:
        milestones_df = pd.DataFrame(
            milestones_state or [],
            columns=["マイルストーン", "予定日", "実績日", "担当者", "進捗率"],
        )

    if nav == "概要":
        render_overview(income_statement, narrative, forecast_df)
    elif nav == "3C分析":
        render_three_c()
    elif nav == "SWOT分析":
        render_swot()
    elif nav == "PEST分析":
        render_pest()
    elif nav == "4P":
        render_four_p()
    elif nav == "財務計画":
        render_financial_section(financial_inputs, income_statement, summary, cashflow_df)
    elif nav == "マイルストーン":
        milestones_df = render_milestone_manager()
    elif nav == "進捗ダッシュボード":
        render_dashboard(income_statement, summary, cashflow_df, forecast_df, milestones_df)


if __name__ == "__main__":
    main()
