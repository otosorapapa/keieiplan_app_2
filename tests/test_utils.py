from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from export import export_plan_to_excel, export_plan_to_pdf, export_plan_to_ppt
from forecast import ForecastScenario, generate_forecast_dataframe
from utils import FinancialInputs, calc_cashflow_projection, calc_income_statement


@pytest.fixture
def sample_financial_inputs() -> FinancialInputs:
    return FinancialInputs(
        fiscal_year=2025,
        sales=120_000_000,
        cogs_rate=0.4,
        personnel_cost=28_000_000,
        marketing_cost=6_000_000,
        general_admin_cost=18_000_000,
        depreciation=2_500_000,
        other_income=1_000_000,
        interest_payment=600_000,
        tax_rate=0.30,
        initial_cash=10_000_000,
        capital_expenditure=5_000_000,
    )


def test_calc_income_statement(sample_financial_inputs: FinancialInputs) -> None:
    income_statement, summary = calc_income_statement(sample_financial_inputs)
    assert pytest.approx(summary["operating_profit"], rel=1e-3) == 120_000_000 * 0.6 - (
        28_000_000 + 6_000_000 + 18_000_000 + 2_500_000
    )
    assert "経常利益" in income_statement["区分"].values
    assert summary["net_income"] > 0


def test_cashflow_projection_monotonic(sample_financial_inputs: FinancialInputs) -> None:
    df = calc_cashflow_projection(sample_financial_inputs, months=12)
    assert len(df) == 12
    assert df["累計現金残高"].iloc[-1] >= df["累計現金残高"].iloc[0]


def test_generate_forecast_dataframe(sample_financial_inputs: FinancialInputs) -> None:
    scenarios = [
        ForecastScenario(name="ベース", sales_growth=0.1, cogs_rate_delta=0.0, opex_growth=0.02),
        ForecastScenario(name="ディフェンシブ", sales_growth=-0.05, cogs_rate_delta=0.03, opex_growth=0.0),
    ]
    df = generate_forecast_dataframe(sample_financial_inputs, scenarios, months=12)
    assert set(df["シナリオ"].unique()) == {"ベース", "ディフェンシブ"}
    counts = df.groupby("シナリオ")["月"].count()
    assert all(counts == 12)


def test_export_generates_files(sample_financial_inputs: FinancialInputs) -> None:
    income_statement, summary = calc_income_statement(sample_financial_inputs)
    narrative = (
        f"売上高は{sample_financial_inputs.sales:,}円、営業利益率は{summary['operating_margin']:.2%}です。"
    )
    forecast_df = generate_forecast_dataframe(
        sample_financial_inputs,
        [ForecastScenario("テスト", 0.05, 0.0, 0.01)],
        months=6,
    )
    milestones_df = pd.DataFrame(
        [
            {
                "マイルストーン": "テスト開始",
                "予定日": pd.Timestamp("2025-01-01"),
                "実績日": pd.Timestamp("2025-01-15"),
                "担当者": "PM",
                "進捗率": 80,
            }
        ]
    )
    excel_bytes = export_plan_to_excel(
        {
            "overview": {"company_name": "テスト株式会社"},
            "financials": sample_financial_inputs.__dict__,
            "milestones": milestones_df.to_dict("records"),
        },
        income_statement,
        forecast_df,
        milestones_df,
    )
    assert len(excel_bytes) > 2000

    pdf_bytes = export_plan_to_pdf(
        {
            "overview": {"company_name": "テスト株式会社"},
        },
        narrative,
        income_statement,
    )
    assert len(pdf_bytes) > 1000

    ppt_bytes = export_plan_to_ppt(
        {
            "overview": {
                "company_name": "テスト株式会社",
                "vision": "未来志向",
                "mission": "顧客価値創造",
                "value_proposition": "高付加価値",
                "target_market": "中小企業",
            }
        },
        narrative,
        income_statement,
    )
    assert len(ppt_bytes) > 1000
