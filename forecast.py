"""Forecasting utilities for multi-scenario sales and cash projections."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from utils import FinancialInputs, format_currency


@dataclass
class ForecastScenario:
    """Definition of a forecast scenario."""

    name: str
    sales_growth: float
    cogs_rate_delta: float
    opex_growth: float
    cash_adjustment: float = 0.0


def generate_forecast_dataframe(
    inputs: FinancialInputs,
    scenarios: Iterable[ForecastScenario],
    months: int = 12,
) -> pd.DataFrame:
    """Create a dataframe of monthly sales and cash balances for each scenario."""

    base_sales = inputs.sales / months
    base_opex = (
        inputs.personnel_cost + inputs.marketing_cost + inputs.general_admin_cost
    ) / months
    other_income_monthly = inputs.other_income / months
    interest_monthly = inputs.interest_payment / months
    depreciation_monthly = inputs.depreciation / months

    records: List[dict] = []
    for scenario in scenarios:
        monthly_growth = (1 + scenario.sales_growth) ** (1 / months) - 1
        monthly_opex_growth = (1 + scenario.opex_growth) ** (1 / months) - 1
        cogs_rate = min(max(inputs.cogs_rate + scenario.cogs_rate_delta, 0.0), 0.95)
        cash_balance = inputs.initial_cash + scenario.cash_adjustment

        for month in range(1, months + 1):
            sales = base_sales * ((1 + monthly_growth) ** (month - 1))
            cogs = sales * cogs_rate
            opex = base_opex * ((1 + monthly_opex_growth) ** (month - 1))
            operating_cf = sales - cogs - opex
            net_cash = (
                operating_cf
                + other_income_monthly
                - interest_monthly
                + depreciation_monthly
            )
            if month == 1:
                net_cash -= inputs.capital_expenditure
            cash_balance += net_cash
            records.append(
                {
                    "シナリオ": scenario.name,
                    "月": month,
                    "売上": sales,
                    "キャッシュ残高": cash_balance,
                }
            )
    return pd.DataFrame(records)


def build_forecast_chart(df: pd.DataFrame) -> go.Figure:
    """Create a combined chart displaying sales and cash transitions."""

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for scenario in df["シナリオ"].unique():
        subset = df[df["シナリオ"] == scenario]
        fig.add_trace(
            go.Scatter(
                x=subset["月"],
                y=subset["売上"],
                name=f"{scenario}｜売上",
                mode="lines+markers",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=subset["月"],
                y=subset["キャッシュ残高"],
                name=f"{scenario}｜キャッシュ",
                mode="lines",
                line=dict(dash="dash"),
            ),
            secondary_y=True,
        )
    fig.update_layout(
        height=480,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2),
        margin=dict(l=60, r=60, t=30, b=60),
        template="plotly_white",
    )
    fig.update_xaxes(title_text="月")
    fig.update_yaxes(title_text="売上高", secondary_y=False)
    fig.update_yaxes(title_text="キャッシュ残高", secondary_y=True)
    return fig


def render_forecast_section(inputs: FinancialInputs) -> pd.DataFrame:
    """Render the forecasting controls and chart, returning the dataframe."""

    st.subheader("シナリオ比較｜売上・キャッシュフロー予測")
    with st.expander("シナリオパラメータ", expanded=True):
        months = st.slider(
            "分析期間（月数）",
            min_value=6,
            max_value=36,
            value=12,
            help="短期から中期までの月次視点で売上とキャッシュを俯瞰します。",
            key="forecast_months",
        )
        scenario_configs: List[ForecastScenario] = []
        labels = [
            ("ベース", 0.08, 0.0, 0.02, 0.0),
            ("ストレッチ", 0.15, -0.02, 0.04, 2_000_000.0),
            ("ディフェンシブ", -0.05, 0.03, 0.0, -1_000_000.0),
        ]
        for name, growth, cogs_delta, opex_growth, cash_adj in labels:
            cols = st.columns(4)
            with cols[0]:
                growth_val = st.number_input(
                    f"{name}｜売上成長率",
                    value=growth,
                    min_value=-0.5,
                    max_value=0.8,
                    step=0.01,
                    help="年率ベースでの売上成長前提。月次へ自動的に補間します。",
                    key=f"growth_{name}",
                )
            with cols[1]:
                cogs_delta_val = st.number_input(
                    f"{name}｜原価率変化",
                    value=cogs_delta,
                    min_value=-0.3,
                    max_value=0.3,
                    step=0.005,
                    help="プロセス改善や仕入条件による原価率の変動を想定します。",
                    key=f"cogs_{name}",
                )
            with cols[2]:
                opex_growth_val = st.number_input(
                    f"{name}｜販管費成長",
                    value=opex_growth,
                    min_value=-0.3,
                    max_value=0.6,
                    step=0.01,
                    help="固定費・半固定費の増減を年率ベースで設定します。",
                    key=f"opex_{name}",
                )
            with cols[3]:
                cash_adj_val = st.number_input(
                    f"{name}｜初期キャッシュ調整",
                    value=cash_adj,
                    step=500000.0,
                    help="追加調達や特別配当など初期のキャッシュ増減を設定します。",
                    key=f"cash_{name}",
                )
            scenario_configs.append(
                ForecastScenario(
                    name=name,
                    sales_growth=growth_val,
                    cogs_rate_delta=cogs_delta_val,
                    opex_growth=opex_growth_val,
                    cash_adjustment=cash_adj_val,
                )
            )

    forecast_df = generate_forecast_dataframe(inputs, scenario_configs, months=months)
    fig = build_forecast_chart(forecast_df)
    st.plotly_chart(fig, use_container_width=True)

    latest = (
        forecast_df.sort_values(["シナリオ", "月"]).groupby("シナリオ").tail(1)
    )
    for _, row in latest.iterrows():
        st.metric(
            label=f"{row['シナリオ']}シナリオ 最終月キャッシュ",
            value=format_currency(row["キャッシュ残高"]),
        )
    return forecast_df
