"""Utility functions shared across the business planning application."""
from __future__ import annotations

import json
import locale
import os
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pandas as pd
import streamlit as st
from cryptography.fernet import Fernet


@dataclass
class FinancialInputs:
    """Input parameters required for financial projections."""

    fiscal_year: int
    sales: float
    cogs_rate: float
    personnel_cost: float
    marketing_cost: float
    general_admin_cost: float
    depreciation: float
    other_income: float
    interest_payment: float
    tax_rate: float
    initial_cash: float = 0.0
    capital_expenditure: float = 0.0


DEFAULT_PLAN: Dict[str, Any] = {
    "overview": {
        "company_name": "株式会社サンプル",
        "vision": "地域に根ざした価値創造を通じて持続的に成長する",
        "mission": "顧客の課題を共創で解決するソリューションを提供する",
        "value_proposition": "DXと人の力を掛け合わせた高付加価値サービス",
        "target_market": "地方中堅企業の経営支援",
    },
    "three_c": {
        "customer": "主要顧客は売上10億円規模の製造業。課題は業務可視化と新規販路開拓。",
        "company": "自社の強みは業務設計ノウハウとワンストップ支援の体制。",
        "competitor": "大手コンサルとの差別化は地域密着とスピード。",
    },
    "swot": {
        "strengths": "属人的ノウハウの体系化、パートナー連携ネットワーク",
        "weaknesses": "リード獲得チャネルが限定的、採用体制が未整備",
        "opportunities": "中小企業のDX需要拡大、補助金活用意欲の高まり",
        "threats": "価格競争の激化、景気後退時の投資抑制",
    },
    "pest": {
        "political": "中小企業支援政策の強化、補助金制度の拡充",
        "economic": "為替変動による仕入コスト変化、金利上昇リスク",
        "social": "働き方改革による業務アウトソース需要",
        "technological": "生成AIの進展と活用余地、セキュリティ要件の高度化",
    },
    "four_p": {
        "product": "業務設計・実行支援を一気通貫で提供する伴走プログラム",
        "price": "月額30万円からの成果連動型フィー設計",
        "place": "オンライン×現地訪問のハイブリッド対応",
        "promotion": "ウェビナーと紹介スキームを軸に、SEO・SNSを補完",
    },
    "financials": {
        "fiscal_year": datetime.now().year,
        "sales": 120_000_000.0,
        "cogs_rate": 0.42,
        "personnel_cost": 28_000_000.0,
        "marketing_cost": 6_000_000.0,
        "general_admin_cost": 18_000_000.0,
        "depreciation": 2_500_000.0,
        "other_income": 1_200_000.0,
        "interest_payment": 600_000.0,
        "tax_rate": 0.30,
        "initial_cash": 10_000_000.0,
        "capital_expenditure": 5_000_000.0,
    },
    "milestones": [],
}


def _ensure_locale() -> None:
    """Set locale for Japanese yen formatting when possible."""

    try:
        locale.setlocale(locale.LC_ALL, "ja_JP.UTF-8")
    except locale.Error:
        # Graceful fallback: keep default but currency formatting will degrade gracefully.
        pass


def initialize_session_state() -> None:
    """Populate Streamlit session state with default values if necessary."""

    if "plan_data" not in st.session_state:
        st.session_state["plan_data"] = json.loads(json.dumps(DEFAULT_PLAN, default=str))
    st.session_state.setdefault("milestones", pd.DataFrame(
        [
            {
                "マイルストーン": "顧客開拓キャンペーン開始",
                "予定日": date(datetime.now().year, 4, 1),
                "実績日": None,
                "担当者": "営業チーム",
                "進捗率": 0,
            }
        ]
    ))
    st.session_state.setdefault("wizard_step", 0)
    st.session_state.setdefault("show_wizard", False)
    st.session_state.setdefault("onboarding_shown", False)


def format_currency(value: float, unit: str = "円") -> str:
    """Format currency values with Japanese locale."""

    _ensure_locale()
    try:
        formatted = locale.currency(value, grouping=True)
    except Exception:  # pragma: no cover - fallback path when locale not available
        formatted = f"¥{value:,.0f}"
    return f"{formatted} ({unit})"


def format_percentage(value: float) -> str:
    """Format ratio as percentage string."""

    return f"{value * 100:.1f}%"


def calc_income_statement(inputs: FinancialInputs) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Compute simple income statement and KPI metrics."""

    sales = inputs.sales
    if sales < 0:
        raise ValueError("売上高は0以上で入力してください。")

    cogs = sales * inputs.cogs_rate
    if cogs < 0:
        raise ValueError("売上原価率は0〜1の範囲で入力してください。")
    if inputs.cogs_rate > 0.95:
        raise ValueError("売上原価率が高すぎます。構造を見直してください。")

    gross_profit = sales - cogs

    opex_items = {
        "人件費": inputs.personnel_cost,
        "マーケティング費": inputs.marketing_cost,
        "一般管理費": inputs.general_admin_cost,
        "減価償却費": inputs.depreciation,
    }
    for label, value in opex_items.items():
        if value < 0:
            raise ValueError(f"{label}はマイナスにできません。")
    operating_expenses = sum(opex_items.values())
    operating_profit = gross_profit - operating_expenses

    other_income = inputs.other_income
    interest = inputs.interest_payment
    if interest < 0:
        raise ValueError("支払利息は0以上で入力してください。")

    ordinary_profit = operating_profit + other_income - interest
    taxes = max(0.0, ordinary_profit * inputs.tax_rate)
    net_income = ordinary_profit - taxes

    break_even_sales = (
        operating_expenses / (1 - inputs.cogs_rate)
        if (1 - inputs.cogs_rate) > 0
        else np.nan
    )
    labor_distribution_ratio = (
        inputs.personnel_cost / gross_profit if gross_profit > 0 else np.nan
    )

    income_statement = pd.DataFrame(
        [
            {"区分": "売上高", "金額": sales},
            {"区分": "売上原価", "金額": -cogs},
            {"区分": "粗利", "金額": gross_profit},
            {"区分": "営業費用", "金額": -operating_expenses},
            {"区分": "営業利益", "金額": operating_profit},
            {"区分": "営業外収益", "金額": other_income},
            {"区分": "営業外費用", "金額": -interest},
            {"区分": "経常利益", "金額": ordinary_profit},
            {"区分": "法人税等", "金額": -taxes},
            {"区分": "当期純利益", "金額": net_income},
        ]
    )

    summary = {
        "gross_margin_rate": gross_profit / sales if sales else 0,
        "operating_margin": operating_profit / sales if sales else 0,
        "ordinary_margin": ordinary_profit / sales if sales else 0,
        "net_margin": net_income / sales if sales else 0,
        "break_even_sales": break_even_sales,
        "labor_distribution_ratio": labor_distribution_ratio,
        "net_income": net_income,
        "operating_profit": operating_profit,
    }
    return income_statement, summary


def calc_cashflow_projection(inputs: FinancialInputs, months: int = 12) -> pd.DataFrame:
    """Generate a simple monthly cash-flow projection."""

    monthly_sales = inputs.sales / months
    monthly_cogs = monthly_sales * inputs.cogs_rate
    monthly_personnel = inputs.personnel_cost / months
    monthly_marketing = inputs.marketing_cost / months
    monthly_admin = inputs.general_admin_cost / months
    monthly_interest = inputs.interest_payment / months

    records = []
    cumulative_cash = inputs.initial_cash
    for month in range(1, months + 1):
        cash_in = monthly_sales + (inputs.other_income / months)
        cash_out = (
            monthly_cogs
            + monthly_personnel
            + monthly_marketing
            + monthly_admin
            + monthly_interest
        )
        investment_cf = -inputs.capital_expenditure if month == 1 else 0.0
        operating_cf = cash_in - cash_out
        net = operating_cf + investment_cf
        cumulative_cash += net + (inputs.depreciation / months)
        records.append(
            {
                "月": month,
                "営業キャッシュフロー": operating_cf,
                "投資キャッシュフロー": investment_cf,
                "フリーキャッシュフロー": net,
                "累計現金残高": cumulative_cash,
            }
        )
    return pd.DataFrame(records)


def generate_financial_narrative(inputs: FinancialInputs, summary: Dict[str, float]) -> str:
    """Create an automatically generated narrative for the business plan."""

    return (
        f"{inputs.fiscal_year}年度は売上高{format_currency(inputs.sales)}を計画。"
        f"粗利率は{format_percentage(summary['gross_margin_rate'])}で推移し、"
        f"営業利益は{format_currency(summary['operating_profit'])}となる見込みです。"
        f"経常利益は売上高の{format_percentage(summary['ordinary_margin'])}を確保し、"
        f"当期純利益は{format_currency(summary['net_income'])}。"
        f"労働分配率は{format_percentage(summary['labor_distribution_ratio'] or 0)}に収まり、"
        "収益性と人的投資のバランスを維持します。"
    )


def validate_required_fields(data: Dict[str, Any], required_fields: Iterable[Tuple[str, str]]) -> Dict[str, str]:
    """Validate required fields returning error messages keyed by field."""

    errors: Dict[str, str] = {}
    for field, label in required_fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors[field] = f"{label}は必須項目です。"
    return errors


def _normalise_datetime(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _get_crypto_key() -> bytes:
    env_key = os.getenv("APP_CRYPTO_KEY")
    if env_key:
        return env_key.encode("utf-8")
    if "_crypto_key" not in st.session_state:
        st.session_state["_crypto_key"] = Fernet.generate_key()
    return st.session_state["_crypto_key"]


def save_encrypted_payload(data: Dict[str, Any], filename: str = "plan_secure.bin") -> Path:
    """Encrypt and persist plan data locally for future retrieval."""

    storage_dir = Path(os.getenv("PLAN_STORAGE_DIR", ".secure"))
    storage_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, default=_normalise_datetime).encode("utf-8")
    cipher = Fernet(_get_crypto_key())
    encrypted = cipher.encrypt(payload)
    path = storage_dir / filename
    path.write_bytes(encrypted)
    return path


def load_encrypted_payload(filename: str = "plan_secure.bin") -> Dict[str, Any] | None:
    """Load encrypted plan data if available."""

    storage_dir = Path(os.getenv("PLAN_STORAGE_DIR", ".secure"))
    path = storage_dir / filename
    if not path.exists():
        return None
    cipher = Fernet(_get_crypto_key())
    decrypted = cipher.decrypt(path.read_bytes())
    return json.loads(decrypted.decode("utf-8"))


def flatten_plan(plan_data: Dict[str, Any]) -> pd.DataFrame:
    """Flatten nested plan data into a tabular representation for export."""

    records = []
    for section, contents in plan_data.items():
        if isinstance(contents, dict):
            for key, value in contents.items():
                records.append({"セクション": section, "項目": key, "内容": value})
        else:
            records.append({"セクション": section, "項目": "value", "内容": contents})
    return pd.DataFrame(records)


def plan_to_financial_inputs(plan_data: Dict[str, Any]) -> FinancialInputs:
    """Convert session-state plan data to :class:`FinancialInputs`."""

    financials = plan_data.get("financials", {})
    return FinancialInputs(**financials)


def ensure_serialisable_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare a dataframe for JSON export by casting dates to isoformat."""

    converted = df.copy()
    for col in converted.columns:
        if np.issubdtype(converted[col].dtype, np.datetime64):
            converted[col] = converted[col].dt.date.apply(lambda x: x.isoformat() if x else "")
    return converted
