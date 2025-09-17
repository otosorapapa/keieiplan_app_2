"""Onboarding experience shown to first-time users."""
from __future__ import annotations

import streamlit as st


ONBOARDING_HTML = """
<style>
.onboarding-overlay {
    position: fixed;
    inset: 0;
    background: rgba(35, 49, 66, 0.82);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
}
.onboarding-card {
    width: min(680px, 90vw);
    background: linear-gradient(135deg, #274472, #41729F);
    color: #ffffff;
    border-radius: 28px;
    padding: 2.4rem;
    box-shadow: 0 32px 64px rgba(0, 0, 0, 0.35);
    animation: fadeIn 0.6s ease-out;
}
.onboarding-card h2 {
    margin-top: 0;
    font-size: 2rem;
}
.onboarding-card ul {
    list-style: none;
    padding-left: 0;
    display: grid;
    gap: 0.8rem;
}
.onboarding-card li {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    animation: slideUp 0.8s ease-out;
}
@keyframes fadeIn {
    from {opacity: 0; transform: translateY(10px);}
    to {opacity: 1; transform: translateY(0);}
}
@keyframes slideUp {
    from {opacity: 0; transform: translateY(24px);}
    to {opacity: 1; transform: translateY(0);}
}
</style>
<div class="onboarding-overlay">
  <div class="onboarding-card">
    <h2>ようこそ！統合経営ダッシュボードへ</h2>
    <p>このツアーでは、事業計画の入力〜シナリオ分析〜資料出力までの流れをご案内します。</p>
    <ul>
      <li>① 「概要」タブでビジョンと価値提案を整理</li>
      <li>② 「分析タブ」で3C・SWOT・PEST・4Pのフレームに沿って入力</li>
      <li>③ 「財務計画」で数値シミュレーション、シナリオ別にグラフ化</li>
      <li>④ 「マイルストーン」で実行ロードマップを可視化</li>
      <li>⑤ 「進捗ダッシュボード」からKPIとキャッシュをトラッキング</li>
    </ul>
    <p>右上の保存ボタンで暗号化保存、エクスポート機能でPDF/Excel/PPTを即時出力できます。</p>
  </div>
</div>
"""


def show_onboarding_tour() -> None:
    """Display onboarding overlay on first visit."""

    if st.session_state.get("onboarding_shown", False):
        return

    placeholder = st.empty()
    placeholder.markdown(ONBOARDING_HTML, unsafe_allow_html=True)
    if st.button("ツアーを開始", type="primary"):
        st.session_state["onboarding_shown"] = True
        placeholder.empty()
        st.experimental_rerun()
