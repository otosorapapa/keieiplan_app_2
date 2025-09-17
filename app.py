import json
import io
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Literal, Optional, Tuple
import datetime as dt

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st


st.set_page_config(
    page_title="経営計画ダッシュボード",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@dataclass
class PlanInputs:
    """Container for baseline plan assumptions."""

    period: Literal["monthly", "quarterly", "yearly"]
    periods: int
    sales: float
    var_cost_rate: float
    fixed_cost: float
    opening_cash: float = 0.0
    capex: float = 0.0


@dataclass
class Scenario:
    """Definition of a sensitivity scenario."""

    name: str
    sales_multiplier: float = 1.0
    var_cost_rate_pp: float = 0.0
    fixed_cost_multiplier: float = 1.0
    price_up_ratio: float = 0.0


I18N: Dict[str, Dict[str, str]] = {
    "ja": {
        "tab_start": "はじめる",
        "tab_detail": "詳細入力",
        "tab_scenario": "シナリオ",
        "tab_analysis": "分析",
        "tab_export": "レポート/エクスポート",
        "wizard_title": "3ステップで損益分岐点を把握",
        "step1": "ステップ1：事業スコープ",
        "step2": "ステップ2：基本値入力",
        "step3": "ステップ3：結果と次アクション",
        "business_name": "事業名",
        "currency": "通貨",
        "start_month": "開始月",
        "period_type": "期間粒度",
        "periods": "期間数",
        "sales_label": "想定売上（期間合計）",
        "var_rate_label": "変動費率",
        "fixed_cost_label": "固定費",
        "fixed_cost_mode": "固定費の入力単位",
        "opening_cash": "期首現金",
        "capex": "設備投資（期間合計）",
        "fte": "人員数/FTE（任意）",
        "labor_cost": "人件費（期間合計・任意）",
        "next": "次へ",
        "back": "戻る",
        "go_detail": "詳細タブで深掘り",
        "sales": "売上",
        "gross_margin": "粗利率",
        "operating_profit": "営業利益",
        "bep": "損益分岐点売上高",
        "bep_rate": "BEP達成率",
        "cash_balance": "期末現金残高",
        "bep_gauge": "BEP達成度",
        "sales_vs_bep": "売上とBEPの比較",
        "cash_projection": "キャッシュフロー予測",
        "anomaly_alerts": "改善ヒント",
        "detail_costs": "費用カテゴリのカスタマイズ",
        "apply_detail": "表の値を計画に反映",
        "detail_summary": "集計結果",
        "scenario_title": "シナリオ比較",
        "add_scenario": "カスタムシナリオを追加",
        "scenario_json_download": "シナリオJSONを保存",
        "scenario_json_upload": "JSONから読込",
        "analysis_title": "経営指標分析",
        "export_title": "出力",
        "download_excel": "Excelダウンロード",
        "download_html": "HTMLレポートダウンロード",
        "pdf_hint": "PDF化するにはブラウザの印刷ダイアログから保存してください。",
        "labor_share": "労働分配率",
        "price_mode_total": "期間合計",
        "price_mode_monthly": "月額ベース",
        "price_mode_yearly": "年額ベース",
        "wizard_ready": "主要KPIが計算されました。詳細タブで施策を検討しましょう。",
        "complete_plan": "プラン確定",
    },
    "en": {
        "tab_start": "Quick start",
        "tab_detail": "Detailed inputs",
        "tab_scenario": "Scenarios",
        "tab_analysis": "Analysis",
        "tab_export": "Export",
        "wizard_title": "Build a break-even plan in 3 steps",
        "step1": "Step 1: Scope",
        "step2": "Step 2: Core assumptions",
        "step3": "Step 3: Results & next actions",
        "business_name": "Business name",
        "currency": "Currency",
        "start_month": "Start month",
        "period_type": "Period granularity",
        "periods": "Number of periods",
        "sales_label": "Total sales for plan horizon",
        "var_rate_label": "Variable cost ratio",
        "fixed_cost_label": "Fixed costs",
        "fixed_cost_mode": "Fixed cost input mode",
        "opening_cash": "Opening cash",
        "capex": "Capex (total)",
        "fte": "Headcount/FTE (optional)",
        "labor_cost": "Labour cost (total, optional)",
        "next": "Next",
        "back": "Back",
        "go_detail": "Open detailed tabs",
        "sales": "Sales",
        "gross_margin": "Gross margin",
        "operating_profit": "Operating profit",
        "bep": "Break-even sales",
        "bep_rate": "BEP coverage",
        "cash_balance": "Closing cash",
        "bep_gauge": "BEP attainment",
        "sales_vs_bep": "Sales vs BEP",
        "cash_projection": "Cash projection",
        "anomaly_alerts": "Improvement ideas",
        "detail_costs": "Customise cost categories",
        "apply_detail": "Apply table to plan",
        "detail_summary": "Summary",
        "scenario_title": "Scenario comparison",
        "add_scenario": "Add custom scenario",
        "scenario_json_download": "Download scenarios JSON",
        "scenario_json_upload": "Load scenarios from JSON",
        "analysis_title": "KPI analysis",
        "export_title": "Exports",
        "download_excel": "Download Excel",
        "download_html": "Download HTML report",
        "pdf_hint": "To save as PDF, print the HTML report from your browser.",
        "labor_share": "Labour share",
        "price_mode_total": "Plan total",
        "price_mode_monthly": "Monthly",
        "price_mode_yearly": "Annual",
        "wizard_ready": "KPI summary is ready. Continue exploring in the detailed tabs.",
        "complete_plan": "Plan locked in",
    },
}

CURRENCY_OPTIONS: Dict[str, str] = {
    "JPY": "¥",
    "USD": "$",
    "EUR": "€",
}

PERIOD_CONFIG: Dict[str, Dict[str, Any]] = {
    "monthly": {"label": "月次", "min": 3, "max": 36, "unit": "ヶ月"},
    "quarterly": {"label": "四半期", "min": 2, "max": 12, "unit": "四半期"},
    "yearly": {"label": "年次", "min": 1, "max": 5, "unit": "年"},
}

PERIOD_MONTHS: Dict[str, int] = {"monthly": 1, "quarterly": 3, "yearly": 12}

PRESET_SCENARIOS: List[Scenario] = [
    Scenario(name="A. 売上+10%", sales_multiplier=1.10),
    Scenario(name="A2. 売上-10%", sales_multiplier=0.90),
    Scenario(name="B. 変動費率+3pp", var_cost_rate_pp=0.03),
    Scenario(name="C. 人件費+5%", fixed_cost_multiplier=1.05),
    Scenario(name="D. 固定費+10%", fixed_cost_multiplier=1.10),
    Scenario(name="E. 価格改定+5%", price_up_ratio=0.05),
]

CSS_STYLE = """
<style>
:root {
    --ink: #1F2937;
    --muted: #6B7280;
    --accent: #2563EB;
    --surface: #FFFFFF;
    --surface-alt: #EFF4FF;
}

html, body, [data-testid="stAppViewContainer"] {
    background-color: #F3F4F6;
    color: var(--ink);
    font-family: "Noto Sans JP", "Hiragino Sans", "Helvetica Neue", sans-serif;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111827 0%, #1F2937 100%);
    color: #F9FAFB;
}

[data-testid="stSidebar"] * {
    color: #E5E7EB !important;
}

.metric-card {
    background: linear-gradient(135deg, #FFFFFF 0%, #EFF6FF 100%);
    padding: 1.2rem 1.4rem;
    border-radius: 18px;
    box-shadow: 0 18px 32px rgba(37, 99, 235, 0.12);
}

.hero-card {
    background: linear-gradient(135deg, rgba(37, 99, 235, 0.95) 0%, rgba(14, 165, 233, 0.92) 100%);
    color: #FFFFFF;
    padding: 2rem 2.6rem;
    border-radius: 28px;
    margin-bottom: 1.2rem;
}

.hero-card h1 {
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 0.8rem;
}

.hero-card p {
    font-size: 1.05rem;
    margin: 0;
}

section.card {
    background-color: var(--surface);
    padding: 1.4rem 1.6rem;
    border-radius: 18px;
    box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
    margin-bottom: 1.4rem;
}

.badge {
    display: inline-block;
    background: rgba(37, 99, 235, 0.1);
    color: var(--accent);
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-right: 0.4rem;
}
</style>
"""


HELP_TEXTS: Dict[str, str] = {
    "sales": "期間全体の売上見込みです。既存顧客＋新規獲得の合計を入力してください。",
    "var_rate": "売上に連動して増減する仕入・決済手数料などの割合です。",
    "fixed_cost": "賃料・人件費など売上に関係なく発生する費用の期間合計です。",
    "opening_cash": "スタート時点の現金残高です。",
    "capex": "期間内に予定している設備投資の総額です。",
    "fte": "正社員換算の人数です。兼務やアルバイトは0.5などで入力します。",
    "labor_cost": "人件費の合計です。労働分配率の計算に利用します。",
}


LABOR_KEYWORDS = ("人件", "給与", "賞与", "賃金", "labor", "wage")


def t(key: str, fallback: Optional[str] = None) -> str:
    """Return translated text for the active language."""

    lang = st.session_state.get("language", "ja")
    return I18N.get(lang, {}).get(key, fallback if fallback is not None else key)


def inject_css() -> None:
    """Inject shared CSS tokens into the app."""

    st.markdown(CSS_STYLE, unsafe_allow_html=True)


def format_currency(value: float, currency: str, digits: int = 0) -> str:
    """Format numbers as currency string."""

    if value is None or np.isnan(value):
        return "N/A"
    formatted = f"{abs(value):,.{digits}f}"
    sign = "-" if value < 0 else ""
    return f"{sign}{currency}{formatted}"


def format_percent(value: float, digits: int = 1) -> str:
    """Format ratios as percentages."""

    if value is None or np.isnan(value):
        return "N/A"
    return f"{value * 100:.{digits}f}%"


def plan_to_tuple(plan: PlanInputs) -> Tuple[Any, ...]:
    """Convert plan inputs into a hashable tuple for caching."""

    return (
        plan.period,
        plan.periods,
        float(plan.sales),
        float(plan.var_cost_rate),
        float(plan.fixed_cost),
        float(plan.opening_cash),
        float(plan.capex),
    )


def total_months(period: str, periods: int) -> int:
    """Return number of calendar months covered by the plan."""

    return PERIOD_MONTHS.get(period, 1) * periods


def period_labels(period: str, periods: int, start_month: int) -> List[str]:
    """Generate labels for timeline charts based on the start month."""

    labels: List[str] = []
    month_names = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
    for idx in range(periods):
        if period == "monthly":
            month = ((start_month - 1 + idx) % 12)
            labels.append(month_names[month])
        elif period == "quarterly":
            labels.append(f"第{idx + 1}四半期")
        else:
            labels.append(f"Year {idx + 1}")
    return labels


def compute_summary(plan: PlanInputs) -> Dict[str, float]:
    """Compute break-even and profitability metrics.

    Gross profit = sales × (1 − var_cost_rate).
    Contribution margin ratio = 1 − var_cost_rate.
    Break-even sales = fixed_cost ÷ contribution_margin_ratio.
    Operating profit = gross_profit − fixed_cost.
    """

    cm_ratio = 1.0 - plan.var_cost_rate
    gross_profit = plan.sales * cm_ratio
    operating_profit = gross_profit - plan.fixed_cost

    if cm_ratio > 0:
        # Break-even sales based on contribution margin ratio.
        bep_sales = plan.fixed_cost / cm_ratio
        bep_gap = plan.sales - bep_sales
        bep_rate = plan.sales / bep_sales if bep_sales else np.nan
    else:
        bep_sales = np.nan
        bep_gap = np.nan
        bep_rate = np.nan

    operating_margin = operating_profit / plan.sales if plan.sales else np.nan
    safety_margin = bep_gap / plan.sales if plan.sales and not np.isnan(bep_gap) else np.nan

    return {
        "sales": plan.sales,
        "var_cost_rate": plan.var_cost_rate,
        "cm_ratio": cm_ratio,
        "gross_profit": gross_profit,
        "fixed_cost": plan.fixed_cost,
        "operating_profit": operating_profit,
        "operating_margin": operating_margin,
        "bep_sales": bep_sales,
        "bep_gap": bep_gap,
        "bep_rate": bep_rate,
        "safety_margin": safety_margin,
    }


def monthly_projection(plan: PlanInputs) -> Dict[str, List[float]]:
    """Return per-period projection including cash balance.

    Sales, fixed cost, and capex are distributed evenly.
    Cash(t) = Cash(t-1) + sales_t × (1 − var_cost_rate) − fixed_cost_t − capex_t.
    """

    if plan.periods <= 0:
        return {
            "sales": [],
            "variable_cost": [],
            "gross_profit": [],
            "fixed_cost": [],
            "operating_profit": [],
            "capex": [],
            "cash_balance": [],
        }

    sales_per_period = plan.sales / plan.periods
    variable_cost_per_period = sales_per_period * plan.var_cost_rate
    contribution_per_period = sales_per_period - variable_cost_per_period
    fixed_per_period = plan.fixed_cost / plan.periods
    capex_per_period = plan.capex / plan.periods

    sales_list: List[float] = []
    variable_list: List[float] = []
    gross_list: List[float] = []
    fixed_list: List[float] = []
    op_list: List[float] = []
    capex_list: List[float] = []
    cash_list: List[float] = []

    cash_balance = plan.opening_cash
    for _ in range(plan.periods):
        operating_profit = contribution_per_period - fixed_per_period
        cash_balance = cash_balance + contribution_per_period - fixed_per_period - capex_per_period

        sales_list.append(sales_per_period)
        variable_list.append(variable_cost_per_period)
        gross_list.append(contribution_per_period)
        fixed_list.append(fixed_per_period)
        op_list.append(operating_profit)
        capex_list.append(capex_per_period)
        cash_list.append(cash_balance)

    return {
        "sales": sales_list,
        "variable_cost": variable_list,
        "gross_profit": gross_list,
        "fixed_cost": fixed_list,
        "operating_profit": op_list,
        "capex": capex_list,
        "cash_balance": cash_list,
    }


def apply_scenario(plan: PlanInputs, scenario: Scenario) -> PlanInputs:
    """Apply scenario multipliers to the baseline plan."""

    adjusted_sales = plan.sales * scenario.sales_multiplier * (1.0 + scenario.price_up_ratio)
    adjusted_var_rate = float(np.clip(plan.var_cost_rate + scenario.var_cost_rate_pp, 0.0, 0.99))
    adjusted_fixed = plan.fixed_cost * scenario.fixed_cost_multiplier
    return PlanInputs(
        period=plan.period,
        periods=plan.periods,
        sales=adjusted_sales,
        var_cost_rate=adjusted_var_rate,
        fixed_cost=adjusted_fixed,
        opening_cash=plan.opening_cash,
        capex=plan.capex,
    )


def detect_anomalies(summary: Dict[str, float]) -> List[Dict[str, Any]]:
    """Return rule-based anomaly detections and improvement hints."""

    findings: List[Dict[str, Any]] = []
    cm_ratio = summary.get("cm_ratio", 0.0)
    operating_profit = summary.get("operating_profit", 0.0)
    fixed_cost = summary.get("fixed_cost", 0.0)
    sales = summary.get("sales", 0.0)
    gross_profit = summary.get("gross_profit", 0.0)
    labor_cost = summary.get("labor_cost", 0.0)
    fte = summary.get("fte", 0.0)

    if operating_profit < 0:
        if cm_ratio > 0:
            reduced_fixed = fixed_cost * 0.9
            new_bep = reduced_fixed / cm_ratio
            bep_delta = summary.get("bep_sales", np.nan) - new_bep
        else:
            new_bep = np.nan
            bep_delta = np.nan
        findings.append(
            {
                "score": 90,
                "title": "営業利益が赤字",
                "message": "営業利益がマイナスのためコスト構造の見直しが必要です。",
                "hint": {
                    "action": "reduce_fixed",
                    "bep_delta": bep_delta,
                    "new_bep": new_bep,
                    "reduction_pct": 10,
                },
            }
        )

    if gross_profit > 0 and labor_cost > 0:
        labor_share = labor_cost / gross_profit
        summary["labor_share"] = labor_share
        if labor_share > 0.45:
            findings.append(
                {
                    "score": 75,
                    "title": "労働分配率が高い",
                    "message": "労働分配率が45%を超えています。生産性向上や価格改定を検討しましょう。",
                    "hint": {
                        "action": "labor_share",
                        "labor_share": labor_share,
                        "target": 0.45,
                        "fte": fte,
                    },
                }
            )

    if cm_ratio < 0.25:
        findings.append(
            {
                "score": 65,
                "title": "粗利率が低い",
                "message": "変動費率が高く粗利率が25%未満です。仕入条件や価格設定を再確認してください。",
                "hint": {
                    "action": "improve_cm",
                    "current_cm": cm_ratio,
                    "target": 0.3,
                },
            }
        )

    if not findings:
        # Provide at least one proactive suggestion to satisfy requirement.
        projected_gain = sales * 0.03 * cm_ratio
        findings.append(
            {
                "score": 25,
                "title": "健全な収益構造",
                "message": "現状は健全です。さらなる利益向上策を検討しましょう。",
                "hint": {
                    "action": "price_up",
                    "price_increase": 0.03,
                    "estimated_profit_gain": projected_gain,
                },
            }
        )

    return findings


def calculate_costs_from_table(cost_df: pd.DataFrame, sales: float) -> Dict[str, float]:
    """Aggregate variable, fixed, and labour costs from editable table."""

    variable_total = 0.0
    fixed_total = 0.0
    labor_total = 0.0

    for _, row in cost_df.iterrows():
        mode = row.get("入力タイプ", "金額")
        category = row.get("区分", "Fixed")
        rate = row.get("率(売上比)", 0.0) or 0.0
        quantity = row.get("数量", 0.0) or 0.0
        unit_price = row.get("単価", 0.0) or 0.0
        amount = row.get("金額(固定)", 0.0) or 0.0

        if mode == "率×売上":
            total_amount = sales * float(rate)
        elif mode == "単価×数量":
            total_amount = float(quantity) * float(unit_price)
        else:
            total_amount = float(amount)

        if category == "Variable":
            variable_total += total_amount
        else:
            fixed_total += total_amount

        is_labor = bool(row.get("労務費?", False))
        if not is_labor:
            name = str(row.get("名称", "")).lower()
            is_labor = any(keyword in name for keyword in LABOR_KEYWORDS)
        if is_labor:
            labor_total += total_amount

    var_rate = variable_total / sales if sales else 0.0
    return {
        "variable": variable_total,
        "fixed": fixed_total,
        "labor": labor_total,
        "var_rate": var_rate,
    }


@st.cache_data(show_spinner=False)
def cached_summary(plan_tuple: Tuple[Any, ...]) -> Dict[str, float]:
    """Cached wrapper around compute_summary."""

    plan = PlanInputs(*plan_tuple)
    return compute_summary(plan)


@st.cache_data(show_spinner=False)
def cached_projection(plan_tuple: Tuple[Any, ...]) -> Dict[str, List[float]]:
    """Cached wrapper around monthly_projection."""

    plan = PlanInputs(*plan_tuple)
    return monthly_projection(plan)


def build_projection_frame(
    plan: PlanInputs,
    projection: Dict[str, List[float]],
    start_month: int,
) -> pd.DataFrame:
    """Create a tidy DataFrame for projections."""

    labels = period_labels(plan.period, plan.periods, start_month)
    frame = pd.DataFrame(
        {
            "期間": labels,
            "売上": projection["sales"],
            "変動費": projection["variable_cost"],
            "粗利": projection["gross_profit"],
            "固定費": projection["fixed_cost"],
            "営業利益": projection["operating_profit"],
            "設備投資": projection["capex"],
            "期末現金": projection["cash_balance"],
        }
    )
    return frame


def scenario_dataframe(plan: PlanInputs, scenarios: List[Scenario]) -> pd.DataFrame:
    """Build a comparison table for the provided scenarios."""

    records: List[Dict[str, Any]] = []

    baseline_summary = cached_summary(plan_to_tuple(plan))
    baseline_summary.update({"scenario": "ベース"})
    records.append(
        {
            "シナリオ": "ベース",
            "売上": baseline_summary["sales"],
            "変動費率": baseline_summary["var_cost_rate"],
            "BEP": baseline_summary["bep_sales"],
            "BEP達成率": baseline_summary["bep_rate"],
            "営業利益": baseline_summary["operating_profit"],
            "営業利益率": baseline_summary["operating_margin"],
        }
    )

    for scenario in scenarios:
        scenario_plan = apply_scenario(plan, scenario)
        summary = cached_summary(plan_to_tuple(scenario_plan))
        records.append(
            {
                "シナリオ": scenario.name,
                "売上": summary["sales"],
                "変動費率": summary["var_cost_rate"],
                "BEP": summary["bep_sales"],
                "BEP達成率": summary["bep_rate"],
                "営業利益": summary["operating_profit"],
                "営業利益率": summary["operating_margin"],
            }
        )
    return pd.DataFrame(records)


def generate_excel_bytes(
    plan: PlanInputs,
    summary: Dict[str, float],
    projection_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    cost_df: pd.DataFrame,
    metadata: Dict[str, Any],
) -> bytes:
    """Create an Excel workbook with summary, KPI, scenario, and detail sheets."""

    output = io.BytesIO()
    with pd.ExcelWriter(output) as writer:
        summary_table = pd.DataFrame(
            [
                {"指標": "売上", "値": summary["sales"]},
                {"指標": "粗利", "値": summary["gross_profit"]},
                {"指標": "営業利益", "値": summary["operating_profit"]},
                {"指標": "損益分岐点売上高", "値": summary["bep_sales"]},
                {"指標": "BEP達成率", "値": summary["bep_rate"]},
                {"指標": "粗利率", "値": summary["cm_ratio"]},
                {"指標": "営業利益率", "値": summary["operating_margin"]},
            ]
        )
        summary_table.to_excel(writer, sheet_name="サマリ", index=False)

        projection_df.to_excel(writer, sheet_name="月次推移", index=False)

        scenario_df.to_excel(writer, sheet_name="シナリオ比較", index=False)

        cost_df.to_excel(writer, sheet_name="費用カテゴリ", index=False)

        meta_df = pd.DataFrame([
            {"項目": "事業名", "値": metadata.get("business_name", "")},
            {"項目": "通貨", "値": metadata.get("currency", "")},
            {"項目": "期間", "値": metadata.get("period_label", "")},
            {"項目": "作成日", "値": metadata.get("created_at", "")},
        ])
        meta_df.to_excel(writer, sheet_name="プラン情報", index=False)

    output.seek(0)
    return output.getvalue()


def generate_html_report(
    plan: PlanInputs,
    summary: Dict[str, float],
    scenario_df: pd.DataFrame,
    projection_fig: go.Figure,
    bep_fig: go.Figure,
    anomalies: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    currency: str,
) -> str:
    """Generate a single-file HTML report with inline CSS and Plotly charts."""

    if projection_fig is None:
        projection_fig = go.Figure()
    if bep_fig is None:
        bep_fig = go.Figure()

    bep_html = pio.to_html(bep_fig, include_plotlyjs="inline", full_html=False)
    cash_html = pio.to_html(projection_fig, include_plotlyjs=False, full_html=False)

    scenario_display = scenario_df.copy()
    scenario_display["売上"] = scenario_display["売上"].map(lambda v: format_currency(v, currency))
    scenario_display["変動費率"] = scenario_display["変動費率"].map(lambda v: format_percent(v))
    scenario_display["BEP"] = scenario_display["BEP"].map(lambda v: format_currency(v, currency))
    scenario_display["BEP達成率"] = scenario_display["BEP達成率"].map(lambda v: format_percent(v))
    scenario_display["営業利益"] = scenario_display["営業利益"].map(lambda v: format_currency(v, currency))
    scenario_display["営業利益率"] = scenario_display["営業利益率"].map(lambda v: format_percent(v))

    anomaly_items = "".join(
        f"<li><strong>{item['title']}</strong> — {item['message']}</li>" for item in anomalies
    )

    html = f"""<!DOCTYPE html>
<html lang=\"ja\">
<head>
<meta charset=\"utf-8\" />
<title>経営サマリレポート</title>
<style>
body {{ font-family: 'Noto Sans JP', sans-serif; background-color: #F8FAFC; color: #1F2937; margin: 0; padding: 2rem; }}
section {{ background: #FFFFFF; border-radius: 18px; padding: 1.6rem 2rem; margin-bottom: 1.8rem; box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08); }}
h1 {{ margin-top: 0; }}
.table {{ width: 100%; border-collapse: collapse; }}
.table th, .table td {{ padding: 0.6rem 0.8rem; border-bottom: 1px solid #E5E7EB; text-align: left; }}
.badge {{ display: inline-block; background: rgba(37, 99, 235, 0.12); color: #2563EB; padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.75rem; }}
</style>
</head>
<body>
<section>
  <h1>経営サマリ</h1>
  <p class=\"badge\">{metadata.get('business_name', '')}</p>
  <p>{metadata.get('period_label', '')}｜作成日: {metadata.get('created_at', '')}</p>
  <ul>
    <li>{t('sales')} : {format_currency(summary['sales'], currency)}</li>
    <li>{t('gross_margin')} : {format_percent(summary['cm_ratio'])}</li>
    <li>{t('operating_profit')} : {format_currency(summary['operating_profit'], currency)}</li>
    <li>{t('bep')} : {format_currency(summary['bep_sales'], currency)}</li>
  </ul>
</section>
<section>
  <h2>KPIグラフ</h2>
  {bep_html}
  {cash_html}
</section>
<section>
  <h2>シナリオ比較</h2>
  {scenario_display.to_html(index=False, classes='table')}
</section>
<section>
  <h2>改善提案</h2>
  <ul>{anomaly_items}</ul>
  <p style=\"color:#6B7280\">PDF化するにはブラウザの印刷ダイアログから保存してください。</p>
</section>
</body>
</html>"""
    return html


def ensure_session_defaults() -> None:
    """Populate session_state with default values on first load."""

    if "language" not in st.session_state:
        st.session_state["language"] = "ja"

    if "wizard_step" not in st.session_state:
        st.session_state["wizard_step"] = 1

    if "plan_inputs" not in st.session_state:
        st.session_state["plan_inputs"] = asdict(
            PlanInputs(
                period="monthly",
                periods=12,
                sales=1000.0,
                var_cost_rate=0.45,
                fixed_cost=450.0,
                opening_cash=200.0,
                capex=0.0,
            )
        )

    if "business_name" not in st.session_state:
        st.session_state["business_name"] = "サンプル事業"

    if "currency" not in st.session_state:
        st.session_state["currency"] = "JPY"

    if "start_month" not in st.session_state:
        st.session_state["start_month"] = 4

    if "fte" not in st.session_state:
        st.session_state["fte"] = 8.0

    if "labor_cost" not in st.session_state:
        st.session_state["labor_cost"] = 240.0

    if "fixed_cost_mode" not in st.session_state:
        st.session_state["fixed_cost_mode"] = "total"

    if "custom_scenarios" not in st.session_state:
        st.session_state["custom_scenarios"] = []

    if "cost_table" not in st.session_state:
        st.session_state["cost_table"] = pd.DataFrame(
            [
                {
                    "名称": "原材料費",
                    "区分": "Variable",
                    "入力タイプ": "率×売上",
                    "数量": 0.0,
                    "単価": 0.0,
                    "率(売上比)": 0.45,
                    "金額(固定)": 0.0,
                    "労務費?": False,
                },
                {
                    "名称": "人件費",
                    "区分": "Fixed",
                    "入力タイプ": "金額",
                    "数量": 10.0,
                    "単価": 0.0,
                    "率(売上比)": 0.0,
                    "金額(固定)": 240.0,
                    "労務費?": True,
                },
                {
                    "名称": "オフィス賃料",
                    "区分": "Fixed",
                    "入力タイプ": "金額",
                    "数量": 0.0,
                    "単価": 0.0,
                    "率(売上比)": 0.0,
                    "金額(固定)": 120.0,
                    "労務費?": False,
                },
            ]
        )


def render_language_switch() -> None:
    """Render language toggle in the sidebar."""

    with st.sidebar:
        st.selectbox(
            "Language",
            options=list(I18N.keys()),
            format_func=lambda lang: {"ja": "日本語", "en": "English"}.get(lang, lang),
            key="language",
        )
        st.markdown(
            "<small>Powered by Streamlit — 小規模事業者のための経営ダッシュボード</small>",
            unsafe_allow_html=True,
        )


def render_wizard(plan: PlanInputs) -> None:
    """Render three-step onboarding wizard."""

    step = st.session_state.get("wizard_step", 1)

    st.markdown(
        f"<div class='hero-card'><h1>{t('wizard_title')}</h1><p>"
        "必要な数字は売上・変動費率・固定費の3つだけ。3分で損益分岐点とキャッシュの見通しが分かります。"
        "</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown(f"### {t('step' + str(step))}")

    if step == 1:
        col1, col2 = st.columns(2)
        period_options = list(PERIOD_CONFIG.keys())
        period_labels = [PERIOD_CONFIG[p]["label"] for p in period_options]
        period_index = period_options.index(plan.period)
        selected_period = col1.selectbox(
            t("period_type", "期間粒度"),
            options=period_options,
            format_func=lambda p: PERIOD_CONFIG[p]["label"],
            index=period_index,
        )
        st.session_state["plan_inputs"]["period"] = selected_period

        config = PERIOD_CONFIG[selected_period]
        periods_value = int(
            col1.slider(
                t("periods", "期間数"),
                min_value=config["min"],
                max_value=config["max"],
                value=int(st.session_state["plan_inputs"].get("periods", config["min"])),
                help=f"{config['label']}単位での期間数です。",
            )
        )
        st.session_state["plan_inputs"]["periods"] = periods_value

        start_month = col2.selectbox(
            t("start_month", "開始月"),
            options=list(range(1, 13)),
            format_func=lambda m: f"{m}月",
            index=st.session_state.get("start_month", 4) - 1,
        )
        st.session_state["start_month"] = start_month

        business_name = col2.text_input(
            t("business_name", "事業名"),
            value=st.session_state.get("business_name", ""),
        )
        st.session_state["business_name"] = business_name

        currency_codes = list(CURRENCY_OPTIONS.keys())
        currency_index = currency_codes.index(st.session_state.get("currency", "JPY"))
        currency_code = col2.selectbox(
            t("currency", "通貨"),
            options=currency_codes,
            format_func=lambda code: f"{code} ({CURRENCY_OPTIONS[code]})",
            index=currency_index,
        )
        st.session_state["currency"] = currency_code

    elif step == 2:
        plan_data = st.session_state["plan_inputs"]
        total_periods = plan_data["periods"]
        col1, col2 = st.columns(2)

        sales_value = col1.number_input(
            t("sales_label", "想定売上（期間合計）"),
            min_value=0.0,
            step=10.0,
            value=float(plan_data.get("sales", 0.0)),
            help=HELP_TEXTS["sales"],
        )
        st.session_state["plan_inputs"]["sales"] = float(sales_value)

        var_rate_value = col1.slider(
            t("var_rate_label", "変動費率"),
            min_value=0.0,
            max_value=0.95,
            step=0.01,
            value=float(plan_data.get("var_cost_rate", 0.0)),
            help=HELP_TEXTS["var_rate"],
        )
        st.session_state["plan_inputs"]["var_cost_rate"] = float(var_rate_value)

        fixed_mode_options = ["total", "monthly", "yearly"]
        fixed_mode_labels = {
            "total": t("price_mode_total", "期間合計"),
            "monthly": t("price_mode_monthly", "月額ベース"),
            "yearly": t("price_mode_yearly", "年額ベース"),
        }
        fixed_mode = col2.selectbox(
            t("fixed_cost_mode", "固定費の入力単位"),
            options=fixed_mode_options,
            format_func=lambda mode: fixed_mode_labels[mode],
            index=fixed_mode_options.index(st.session_state.get("fixed_cost_mode", "total")),
        )
        st.session_state["fixed_cost_mode"] = fixed_mode

        months_total = total_months(plan.period, plan.periods)
        if fixed_mode == "total":
            default_fixed = float(plan_data.get("fixed_cost", 0.0))
        elif fixed_mode == "monthly":
            default_fixed = float(plan_data.get("fixed_cost", 0.0)) / total_periods if total_periods else 0.0
        else:
            default_fixed = (
                float(plan_data.get("fixed_cost", 0.0)) / (months_total / 12.0) if months_total else 0.0
            )

        fixed_value = col2.number_input(
            t("fixed_cost_label", "固定費"),
            min_value=0.0,
            step=10.0,
            value=default_fixed,
            help=HELP_TEXTS["fixed_cost"],
        )

        if fixed_mode == "total":
            total_fixed = fixed_value
        elif fixed_mode == "monthly":
            total_fixed = fixed_value * total_periods
        else:
            total_fixed = fixed_value * (months_total / 12.0)
        st.session_state["plan_inputs"]["fixed_cost"] = float(total_fixed)

        opening_cash = col1.number_input(
            t("opening_cash", "期首現金"),
            min_value=0.0,
            step=10.0,
            value=float(st.session_state.get("plan_inputs", {}).get("opening_cash", 0.0)),
            help=HELP_TEXTS["opening_cash"],
        )
        st.session_state["plan_inputs"]["opening_cash"] = float(opening_cash)

        capex = col2.number_input(
            t("capex", "設備投資（期間合計）"),
            min_value=0.0,
            step=10.0,
            value=float(st.session_state.get("plan_inputs", {}).get("capex", 0.0)),
            help=HELP_TEXTS["capex"],
        )
        st.session_state["plan_inputs"]["capex"] = float(capex)

        fte = col1.number_input(
            t("fte", "人員数/FTE（任意）"),
            min_value=0.0,
            step=0.5,
            value=float(st.session_state.get("fte", 0.0)),
            help=HELP_TEXTS["fte"],
        )
        st.session_state["fte"] = float(fte)

        labor_cost = col2.number_input(
            t("labor_cost", "人件費（期間合計・任意）"),
            min_value=0.0,
            step=10.0,
            value=float(st.session_state.get("labor_cost", 0.0)),
            help=HELP_TEXTS["labor_cost"],
        )
        st.session_state["labor_cost"] = float(labor_cost)

        if sales_value == 0:
            st.warning("売上が0のためKPIが計算できません。値を入力してください。")

    elif step == 3:
        st.success(t("wizard_ready", "主要KPIが計算されました。詳細タブで施策を検討しましょう。"))
        st.write(" ")
        plan_tuple = plan_to_tuple(plan)
        summary = cached_summary(plan_tuple)
        summary["labor_cost"] = st.session_state.get("labor_cost", 0.0)
        summary["fte"] = st.session_state.get("fte", 0.0)

        currency_symbol = CURRENCY_OPTIONS.get(st.session_state.get("currency", "JPY"), "¥")
        kpi_cols = st.columns(4)
        kpi_cols[0].metric(t("sales", "売上"), format_currency(summary["sales"], currency_symbol))
        kpi_cols[1].metric(
            t("gross_margin", "粗利率"),
            format_percent(summary["cm_ratio"]),
        )
        kpi_cols[2].metric(
            t("operating_profit", "営業利益"),
            format_currency(summary["operating_profit"], currency_symbol),
            format_percent(summary.get("operating_margin", np.nan)),
        )
        kpi_cols[3].metric(t("bep", "損益分岐点売上高"), format_currency(summary["bep_sales"], currency_symbol))

        projection = cached_projection(plan_tuple)
        projection_df = build_projection_frame(plan, projection, st.session_state.get("start_month", 4))

        bep_fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=float(summary.get("bep_rate", 0.0) or 0.0) * 100,
                number={"suffix": "%"},
                title={"text": t("bep_gauge", "BEP達成度")},
                gauge={
                    "axis": {"range": [None, 150], "ticksuffix": "%"},
                    "bar": {"color": "#2563EB"},
                    "steps": [
                        {"range": [0, 80], "color": "#FEE2E2"},
                        {"range": [80, 100], "color": "#FDE68A"},
                        {"range": [100, 150], "color": "#BBF7D0"},
                    ],
                },
            )
        )

        sales_vs_bep_fig = go.Figure()
        sales_vs_bep_fig.add_bar(
            x=[t("sales", "売上"), t("bep", "損益分岐点売上高")],
            y=[summary["sales"], summary.get("bep_sales", 0.0)],
            marker_color=["#2563EB", "#F97316"],
        )
        sales_vs_bep_fig.update_layout(
            title=t("sales_vs_bep", "売上とBEPの比較"),
            yaxis_title=currency_symbol,
            showlegend=False,
        )

        cash_fig = px.line(
            projection_df,
            x="期間",
            y="期末現金",
            title=t("cash_projection", "キャッシュフロー予測"),
            markers=True,
        )
        cash_fig.add_hline(y=0, line_dash="dash", line_color="#9CA3AF")

        col_gauge, col_bar = st.columns(2)
        col_gauge.plotly_chart(bep_fig, use_container_width=True)
        col_bar.plotly_chart(sales_vs_bep_fig, use_container_width=True)
        st.plotly_chart(cash_fig, use_container_width=True)

        anomalies = detect_anomalies(summary)
        with st.expander(t("anomaly_alerts", "改善ヒント"), expanded=True):
            for item in anomalies:
                st.markdown(f"**{item['title']}** — {item['message']}")
                hint = item.get("hint", {})
                if hint.get("action") == "reduce_fixed":
                    new_bep = hint.get("new_bep", np.nan)
                    bep_delta = hint.get("bep_delta", np.nan)
                    st.caption(
                        f"固定費を{hint.get('reduction_pct')}%削減するとBEPは"
                        f"{format_currency(new_bep, currency_symbol)}（▲{format_currency(bep_delta, currency_symbol)}）になります。"
                    )
                elif hint.get("action") == "labor_share":
                    st.caption(
                        f"労働分配率は{format_percent(hint.get('labor_share', np.nan))}。"
                        "省力化や価格改定で45%以下を目指しましょう。"
                    )
                elif hint.get("action") == "improve_cm":
                    st.caption(
                        f"粗利率を{format_percent(hint.get('target', 0.0))}まで引き上げると"
                        "営業利益の改善余地が生まれます。"
                    )
                elif hint.get("action") == "price_up":
                    st.caption(
                        f"価格を{format_percent(hint.get('price_increase', 0.0))}引き上げると"
                        f"営業利益が約{format_currency(hint.get('estimated_profit_gain', 0.0), currency_symbol)}改善します。"
                    )

        st.session_state["wizard_complete"] = True
        st.session_state["latest_summary"] = summary
        st.session_state["latest_projection_df"] = projection_df
        st.session_state["latest_cash_fig"] = cash_fig
        st.session_state["latest_bep_fig"] = sales_vs_bep_fig
        st.session_state["latest_gauge_fig"] = bep_fig
        st.session_state["latest_anomalies"] = anomalies

    col_prev, col_next = st.columns([1, 1])
    if step > 1:
        if col_prev.button(t("back", "戻る")):
            st.session_state["wizard_step"] = max(1, step - 1)
            st.experimental_rerun()
    if step < 3:
        if col_next.button(t("next", "次へ")):
            st.session_state["wizard_step"] = min(3, step + 1)
            st.experimental_rerun()


def render_detail_tab(plan: PlanInputs) -> None:
    """Render detailed cost editor and summary."""

    st.subheader(t("detail_costs", "費用カテゴリのカスタマイズ"))
    cost_df: pd.DataFrame = st.session_state.get("cost_table").copy()
    edited = st.data_editor(
        cost_df,
        num_rows="dynamic",
        key="cost_editor",
        column_config={
            "区分": st.column_config.SelectboxColumn(options=["Fixed", "Variable"], help="固定費か変動費かを選択"),
            "入力タイプ": st.column_config.SelectboxColumn(
                options=["率×売上", "単価×数量", "金額"],
                help="金額の算出方法を選択",
            ),
            "労務費?": st.column_config.CheckboxColumn(help="人件費として労働分配率に含めるか")
        },
        hide_index=True,
    )
    st.session_state["cost_table"] = edited

    cost_summary = calculate_costs_from_table(edited, plan.sales)
    col1, col2, col3 = st.columns(3)
    currency_symbol = CURRENCY_OPTIONS.get(st.session_state.get("currency", "JPY"), "¥")
    gross_base = plan.sales - cost_summary["variable"]
    labor_share = cost_summary["labor"] / gross_base if gross_base > 0 else np.nan
    col1.metric("変動費（集計）", format_currency(cost_summary["variable"], currency_symbol))
    col2.metric("固定費（集計）", format_currency(cost_summary["fixed"], currency_symbol))
    col3.metric(t("labor_share", "労働分配率"), format_percent(labor_share))

    if st.button(t("apply_detail", "表の値を計画に反映")):
        plan_data = st.session_state["plan_inputs"]
        plan_data["fixed_cost"] = float(cost_summary["fixed"])
        if plan.sales:
            plan_data["var_cost_rate"] = float(np.clip(cost_summary["var_rate"], 0.0, 0.99))
        st.session_state["labor_cost"] = float(cost_summary["labor"])
        st.success("計画に反映しました。ウィザードを更新してください。")

    with st.expander(t("detail_summary", "集計結果")):
        st.dataframe(edited, use_container_width=True)


def render_scenario_tab(plan: PlanInputs) -> None:
    """Render scenario comparison including presets and custom scenarios."""

    st.subheader(t("scenario_title", "シナリオ比較"))
    custom_scenarios = [Scenario(**s) for s in st.session_state.get("custom_scenarios", [])]
    scenario_df = scenario_dataframe(plan, PRESET_SCENARIOS + custom_scenarios)
    st.dataframe(
        scenario_df.style.format(
            {
                "売上": "{:,.0f}",
                "変動費率": "{:.1%}",
                "BEP": "{:,.0f}",
                "BEP達成率": "{:.1%}",
                "営業利益": "{:,.0f}",
                "営業利益率": "{:.1%}",
            }
        ),
        use_container_width=True,
    )

    with st.expander(t("add_scenario", "カスタムシナリオを追加")):
        with st.form("custom_scenario_form"):
            name = st.text_input("名称", value="新シナリオ")
            sales_pct = st.slider("売上変動(%)", min_value=-50, max_value=50, value=0, step=5)
            var_pp = st.slider("変動費率変化(pp)", min_value=-20, max_value=20, value=0, step=1)
            fixed_pct = st.slider("固定費変化(%)", min_value=-50, max_value=50, value=0, step=5)
            price_pct = st.slider("価格改定(%)", min_value=-20, max_value=20, value=0, step=1)
            submitted = st.form_submit_button("保存")
            if submitted:
                scenario_dict = {
                    "name": name,
                    "sales_multiplier": 1 + sales_pct / 100,
                    "var_cost_rate_pp": var_pp / 100,
                    "fixed_cost_multiplier": 1 + fixed_pct / 100,
                    "price_up_ratio": price_pct / 100,
                }
                st.session_state["custom_scenarios"].append(scenario_dict)
                st.experimental_rerun()

    if st.session_state.get("custom_scenarios"):
        json_data = json.dumps(st.session_state["custom_scenarios"], ensure_ascii=False, indent=2)
        st.download_button(
            t("scenario_json_download", "シナリオJSONを保存"),
            data=json_data.encode("utf-8"),
            file_name="scenarios.json",
            mime="application/json",
        )

    uploaded = st.file_uploader(t("scenario_json_upload", "JSONから読込"), type="json")
    if uploaded is not None:
        try:
            payload = json.load(uploaded)
            if isinstance(payload, list):
                for item in payload:
                    if set(item.keys()).issuperset({"name", "sales_multiplier", "var_cost_rate_pp", "fixed_cost_multiplier", "price_up_ratio"}):
                        st.session_state["custom_scenarios"].append(item)
                st.success("シナリオを読み込みました。")
                st.experimental_rerun()
            else:
                st.error("JSONの形式が不正です。")
        except json.JSONDecodeError:
            st.error("JSONファイルを解析できませんでした。")

    st.session_state["latest_scenario_df"] = scenario_df


def render_analysis_tab(plan: PlanInputs) -> None:
    """Render KPI analysis with charts and anomaly details."""

    st.subheader(t("analysis_title", "経営指標分析"))
    if not st.session_state.get("wizard_complete"):
        st.info("まずは『はじめる』タブで前提を入力してください。")
        return

    summary = st.session_state.get("latest_summary", {})
    currency_symbol = CURRENCY_OPTIONS.get(st.session_state.get("currency", "JPY"), "¥")

    gauge_fig = st.session_state.get("latest_gauge_fig")
    sales_vs_bep_fig = st.session_state.get("latest_bep_fig")
    cash_fig = st.session_state.get("latest_cash_fig")

    col1, col2 = st.columns(2)
    if gauge_fig is not None:
        col1.plotly_chart(gauge_fig, use_container_width=True)
    if sales_vs_bep_fig is not None:
        col2.plotly_chart(sales_vs_bep_fig, use_container_width=True)
    if cash_fig is not None:
        st.plotly_chart(cash_fig, use_container_width=True)

    anomalies = st.session_state.get("latest_anomalies", [])
    for item in anomalies:
        st.markdown(f"### {item['title']}")
        st.write(item["message"])
        hint = item.get("hint", {})
        if hint.get("action") == "reduce_fixed":
            st.info(
                f"固定費を{hint.get('reduction_pct')}%削減すると損益分岐点は"
                f"{format_currency(hint.get('new_bep', np.nan), currency_symbol)}まで改善します。"
            )
        elif hint.get("action") == "labor_share":
            st.info(
                f"現在の労働分配率は{format_percent(hint.get('labor_share', np.nan))}です。"
                "FTEあたり売上向上やコスト最適化を検討してください。"
            )
        elif hint.get("action") == "improve_cm":
            st.info(
                f"粗利率を{format_percent(hint.get('target', 0.0))}まで高めると営業利益が改善します。"
            )
        elif hint.get("action") == "price_up":
            st.info(
                f"価格を{format_percent(hint.get('price_increase', 0.0))}調整すると"
                f"利益が約{format_currency(hint.get('estimated_profit_gain', 0.0), currency_symbol)}増加する見込みです。"
            )

    st.write("---")
    st.write("主要KPI")
    kpi_table = pd.DataFrame(
        [
            {"指標": t("sales", "売上"), "値": format_currency(summary.get("sales", np.nan), currency_symbol)},
            {"指標": t("gross_margin", "粗利率"), "値": format_percent(summary.get("cm_ratio", np.nan))},
            {"指標": t("operating_profit", "営業利益"), "値": format_currency(summary.get("operating_profit", np.nan), currency_symbol)},
            {"指標": t("bep", "損益分岐点売上高"), "値": format_currency(summary.get("bep_sales", np.nan), currency_symbol)},
            {"指標": t("bep_rate", "BEP達成率"), "値": format_percent(summary.get("bep_rate", np.nan))},
        ]
    )
    st.table(kpi_table)


def render_export_tab(plan: PlanInputs) -> None:
    """Provide Excel and HTML export options."""

    st.subheader(t("export_title", "出力"))
    if not st.session_state.get("wizard_complete"):
        st.info("まずは『はじめる』タブで前提を入力してください。")
        return

    summary = st.session_state.get("latest_summary", {})
    projection_df: Optional[pd.DataFrame] = st.session_state.get("latest_projection_df")
    scenario_df: Optional[pd.DataFrame] = st.session_state.get("latest_scenario_df")
    cost_df: pd.DataFrame = st.session_state.get("cost_table")

    if scenario_df is None:
        custom_scenarios = [Scenario(**s) for s in st.session_state.get("custom_scenarios", [])]
        scenario_df = scenario_dataframe(plan, PRESET_SCENARIOS + custom_scenarios)
    if projection_df is None:
        projection = cached_projection(plan_to_tuple(plan))
        projection_df = build_projection_frame(plan, projection, st.session_state.get("start_month", 4))

    currency_symbol = CURRENCY_OPTIONS.get(st.session_state.get("currency", "JPY"), "¥")

    metadata = {
        "business_name": st.session_state.get("business_name", ""),
        "currency": currency_symbol,
        "period_label": f"{PERIOD_CONFIG[plan.period]['label']}×{plan.periods}",
        "created_at": dt.datetime.now().strftime("%Y-%m-%d"),
    }

    excel_bytes = generate_excel_bytes(plan, summary, projection_df, scenario_df, cost_df, metadata)
    st.download_button(
        t("download_excel", "Excelダウンロード"),
        data=excel_bytes,
        file_name="plan_dashboard.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    cash_fig = st.session_state.get("latest_cash_fig")
    gauge_fig = st.session_state.get("latest_gauge_fig")
    anomalies = st.session_state.get("latest_anomalies", [])
    html_report = generate_html_report(
        plan,
        summary,
        scenario_df,
        cash_fig,
        gauge_fig,
        anomalies,
        metadata,
        currency_symbol,
    )
    st.download_button(
        t("download_html", "HTMLレポートダウンロード"),
        data=html_report.encode("utf-8"),
        file_name="plan_dashboard.html",
        mime="text/html",
    )

    st.info(t("pdf_hint", "PDF化するにはブラウザの印刷ダイアログから保存してください。"))


def main() -> None:
    """Entry point of the Streamlit app."""

    ensure_session_defaults()
    inject_css()
    render_language_switch()

    plan = PlanInputs(**st.session_state["plan_inputs"])

    tabs = st.tabs(
        [
            t("tab_start", "はじめる"),
            t("tab_detail", "詳細入力"),
            t("tab_scenario", "シナリオ"),
            t("tab_analysis", "分析"),
            t("tab_export", "レポート/エクスポート"),
        ]
    )

    with tabs[0]:
        render_wizard(plan)

    with tabs[1]:
        if st.session_state.get("wizard_complete"):
            render_detail_tab(plan)
        else:
            st.info("まずは『はじめる』タブで前提を入力してください。")

    with tabs[2]:
        if st.session_state.get("wizard_complete"):
            render_scenario_tab(plan)
        else:
            st.info("まずは『はじめる』タブで前提を入力してください。")

    with tabs[3]:
        render_analysis_tab(plan)

    with tabs[4]:
        render_export_tab(plan)


if __name__ == "__main__":
    main()
