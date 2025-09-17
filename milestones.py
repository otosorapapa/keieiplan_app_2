"""Milestone management and visualisation utilities."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from utils import ensure_serialisable_dataframe, save_encrypted_payload


COLUMNS = ["マイルストーン", "予定日", "実績日", "担当者", "進捗率"]


def _prepare_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for column in ["予定日", "実績日"]:
        df[column] = pd.to_datetime(df[column], errors="coerce").dt.date
    df["進捗率"] = df["進捗率"].fillna(0).clip(lower=0, upper=100).astype(int)
    return df


def render_milestone_manager() -> pd.DataFrame:
    """Render the milestone table editor and Gantt-style timeline."""

    st.subheader("マイルストーン管理")
    st.caption("OKRと紐づく主要タスクを時系列で管理し、担当者のアサインを明確化します。")

    current_df = st.session_state.get("milestones")
    if current_df is None or current_df.empty:
        current_df = pd.DataFrame(columns=COLUMNS)
    current_df = _prepare_dataframe(current_df)

    edited_df = st.data_editor(
        current_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "予定日": st.column_config.DateColumn("予定日", help="ガントチャートの開始日に反映されます。"),
            "実績日": st.column_config.DateColumn("実績日", help="完了日が未定の場合は空白のままで構いません。"),
            "担当者": st.column_config.TextColumn("担当者", help="責任者またはチーム名。"),
            "進捗率": st.column_config.NumberColumn(
                "進捗率",
                min_value=0,
                max_value=100,
                step=5,
                help="0〜100で入力。50以上はハーフ達成としてダッシュボードに反映されます。",
            ),
        },
        hide_index=True,
        key="milestone_editor",
    )

    edited_df = _prepare_dataframe(edited_df)
    st.session_state["milestones"] = edited_df
    serialised = ensure_serialisable_dataframe(edited_df)
    st.session_state["plan_data"]["milestones"] = serialised.to_dict("records")
    save_encrypted_payload(st.session_state["plan_data"])

    late_items = edited_df[(edited_df["進捗率"] < 100) & (edited_df["予定日"].notna())]
    today = date.today()
    for _, row in late_items.iterrows():
        if row["予定日"] and row["予定日"] < today:
            st.error(f"{row['マイルストーン']}：予定日を過ぎています。リカバリー策を検討しましょう。")

    if not edited_df.empty:
        gantt_df = edited_df.copy()
        gantt_df["開始"] = gantt_df["予定日"].fillna(today)
        gantt_df["終了"] = gantt_df.apply(
            lambda r: r["実績日"]
            if pd.notnull(r["実績日"])
            else (r["予定日"] + timedelta(days=7) if pd.notnull(r["予定日"]) else today + timedelta(days=7)),
            axis=1,
        )
        fig = px.timeline(
            gantt_df,
            x_start="開始",
            x_end="終了",
            y="担当者",
            color="進捗率",
            hover_name="マイルストーン",
            color_continuous_scale="Blues",
        )
        fig.update_layout(
            height=420,
            margin=dict(l=40, r=40, t=40, b=40),
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("マイルストーンを入力するとガントチャートが表示されます。")

    return edited_df
