"""Accounting integration stubs for future API connectivity."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Optional

import pandas as pd
import streamlit as st


@dataclass
class AccountingConfig:
    """Configuration placeholder for connecting to accounting SaaS."""

    provider: str
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None


class AccountingConnector:
    """Future-proof design for integrating with freee or Money Forward APIs."""

    def __init__(self, config: AccountingConfig):
        self.config = config
        self.token: Optional[str] = None

    def authenticate(self) -> None:
        """Placeholder authentication flow."""

        env_token = os.getenv("ACCOUNTING_ACCESS_TOKEN")
        if env_token:
            self.token = env_token
        else:
            self.token = "dummy-token"

    def fetch_trial_balance(self) -> pd.DataFrame:
        """Return dummy trial balance data until API integration is implemented."""

        if self.token is None:
            self.authenticate()
        data = [
            {"勘定科目": "売上高", "金額": 12_500_000},
            {"勘定科目": "売上原価", "金額": -5_300_000},
            {"勘定科目": "販管費", "金額": -4_800_000},
            {"勘定科目": "営業外収益", "金額": 300_000},
            {"勘定科目": "当期純利益", "金額": 2_700_000},
        ]
        return pd.DataFrame(data)

    def fetch_cash_balance(self) -> pd.DataFrame:
        """Simulate cash balance transitions for dashboard visuals."""

        months = pd.date_range(date.today().replace(day=1), periods=6, freq="M")
        balance = 8_000_000
        rows = []
        for month in months:
            balance += 500_000
            rows.append({"月": month.date(), "現金預金残高": balance})
        return pd.DataFrame(rows)


def render_accounting_preview(connector: AccountingConnector) -> None:
    """Render accounting snapshots based on dummy data."""

    st.subheader("会計連携（ダミーデータ）")
    st.caption("API認証情報を設定するとリアルタイムに財務データを同期できます。")

    trial_balance = connector.fetch_trial_balance()
    st.dataframe(trial_balance, use_container_width=True)

    cash_df = connector.fetch_cash_balance()
    st.line_chart(cash_df.set_index("月"))

    st.info(
        "OAuthクライアントIDやシークレットは環境変数で管理できます。"
        "本番環境では、stateパラメータやトークン暗号化を組み合わせて安全性を確保してください。"
    )
