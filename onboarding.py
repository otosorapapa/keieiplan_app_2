"""Onboarding experience shown to first-time users."""
from __future__ import annotations

import streamlit as st
from streamlit.delta_generator import DeltaGenerator


ONBOARDING_STYLE = """
<style>
.onboarding-wrapper {
    width: 100%;
    display: flex;
    justify-content: center;
    margin-bottom: 1.2rem;
}

.onboarding-card {
    width: min(680px, 92vw);
    background: linear-gradient(135deg, #274472, #41729F);
    color: #ffffff;
    border-radius: 28px;
    padding: 2.4rem;
    box-shadow: 0 32px 64px rgba(0, 0, 0, 0.35);
}

.onboarding-card h2 {
    margin-top: 0;
    font-size: 2rem;
}

.onboarding-card p {
    margin-bottom: 1rem;
    line-height: 1.6;
}

.onboarding-card ul {
    list-style: none;
    padding-left: 0;
    display: grid;
    gap: 0.8rem;
    margin: 1.4rem 0 1.6rem 0;
}

.onboarding-card li {
    background: rgba(255, 255, 255, 0.12);
    border-radius: 14px;
    padding: 0.9rem 1rem;
}

.onboarding-note {
    font-size: 0.9rem;
    opacity: 0.9;
    margin-top: 1.4rem;
}

[data-testid="stModal"] > div:first-child {
    background: transparent;
    box-shadow: none;
}

[data-testid="stModal"] [data-testid="stVerticalBlock"] {
    padding: 0 0 1.5rem 0;
}

[data-testid="stModal"] [data-testid="stHorizontalBlock"] {
    margin: 1.4rem auto 0 auto;
    max-width: 420px;
}

[data-testid="stModal"] [data-testid="column"] > div {
    display: flex;
    flex-direction: column;
}

[data-testid="stModal"] button[kind="primary"] {
    background: #F9A620;
    border-color: #F9A620;
    color: #233142;
    font-weight: 600;
}

[data-testid="stModal"] button {
    border-radius: 999px;
    font-weight: 600;
    height: 3rem;
}
</style>
"""


ONBOARDING_CARD_HTML = """
<div class="onboarding-wrapper">
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
    <p class="onboarding-note">右上の保存ボタンで暗号化保存、エクスポート機能でPDF/Excel/PPTを即時出力できます。</p>
  </div>
</div>
"""


def _render_onboarding_content(target: DeltaGenerator) -> bool:
    """Render the onboarding card and actions inside the provided container."""

    target.markdown(ONBOARDING_STYLE, unsafe_allow_html=True)
    target.markdown(ONBOARDING_CARD_HTML, unsafe_allow_html=True)
    columns = target.columns(2)
    start_clicked = columns[0].button(
        "ツアーを開始",
        type="primary",
        use_container_width=True,
        key="onboarding_start_button",
    )
    dismiss_clicked = columns[1].button(
        "閉じる",
        use_container_width=True,
        key="onboarding_close_button",
    )
    return start_clicked or dismiss_clicked


def show_onboarding_tour() -> None:
    """Display onboarding information on first visit with a dismissible modal."""

    if st.session_state.get("onboarding_shown", False):
        return

    rerun = getattr(st, "rerun", st.experimental_rerun)

    if hasattr(st, "modal"):
        with st.modal("", key="onboarding_modal", closable=False):
            modal_container = st.container()
            dismissed = _render_onboarding_content(modal_container)
        if dismissed:
            st.session_state["onboarding_shown"] = True
            rerun()
    else:
        container = st.container()
        dismissed = _render_onboarding_content(container)
        if dismissed:
            st.session_state["onboarding_shown"] = True
            container.empty()
            rerun()
