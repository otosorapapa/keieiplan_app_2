"""Styling utilities for the integrated business planning app."""
from __future__ import annotations

import streamlit as st

THEME_COLORS: dict[str, str] = {
    "background": "#F5F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#EEF3FB",
    "primary": "#274472",
    "primary_light": "#41729F",
    "accent": "#F9A620",
    "positive": "#4AA96C",
    "negative": "#F26A4F",
    "text": "#233142",
    "muted_text": "#667C99",
}


def inject_custom_style() -> None:
    """Inject consistent theming and responsive tweaks."""

    custom_style = f"""
    <style>
    :root {{
        --app-bg: {THEME_COLORS['background']};
        --app-surface: {THEME_COLORS['surface']};
        --app-surface-alt: {THEME_COLORS['surface_alt']};
        --app-primary: {THEME_COLORS['primary']};
        --app-primary-light: {THEME_COLORS['primary_light']};
        --app-accent: {THEME_COLORS['accent']};
        --app-positive: {THEME_COLORS['positive']};
        --app-negative: {THEME_COLORS['negative']};
        --app-text: {THEME_COLORS['text']};
        --app-text-muted: {THEME_COLORS['muted_text']};
    }}

    html, body, [data-testid="stAppViewContainer"] {{
        background: var(--app-bg);
        color: var(--app-text);
        font-family: "Noto Sans JP", "Hiragino Sans", "Yu Gothic", sans-serif;
    }}

    .main .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 3rem;
        max-width: 1180px;
    }}

    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, var(--app-primary) 0%, var(--app-primary-light) 100%);
        color: #F9FBFF !important;
    }}

    [data-testid="stSidebar"] * {{
        color: #F9FBFF !important;
    }}

    .section-card {{
        background: var(--app-surface);
        border-radius: 18px;
        padding: 1.4rem 1.6rem;
        box-shadow: 0 12px 28px rgba(39, 68, 114, 0.08);
        margin-bottom: 1.6rem;
    }}

    .hero-banner {{
        background: radial-gradient(circle at top left, rgba(65, 114, 159, 0.92), rgba(74, 169, 108, 0.88));
        color: white;
        padding: 2.4rem 2.8rem;
        border-radius: 24px;
        box-shadow: 0 24px 48px rgba(35, 49, 66, 0.25);
        margin-bottom: 2rem;
    }}

    .hero-banner h1 {{
        font-size: 2.2rem;
        margin: 0 0 0.6rem 0;
    }}

    .hero-banner p {{
        font-size: 1.05rem;
        opacity: 0.95;
        margin: 0;
    }}

    .form-tooltip {{
        font-size: 0.85rem;
        color: var(--app-text-muted);
    }}

    .control-bar {{
        display: flex;
        gap: 1rem;
        justify-content: space-between;
        flex-wrap: wrap;
        margin-top: 1.1rem;
    }}

    .control-bar button {{
        flex: 1 1 160px;
        border-radius: 999px;
    }}

    .gantt-container {{
        background: var(--app-surface);
        border-radius: 18px;
        padding: 1.2rem;
        box-shadow: 0 10px 24px rgba(35, 49, 66, 0.08);
    }}

    @media (max-width: 768px) {{
        .main .block-container {{
            padding: 1rem 0.8rem 3rem;
        }}
        .hero-banner {{
            padding: 1.8rem;
        }}
        .control-bar {{
            gap: 0.6rem;
        }}
    }}
    </style>
    """
    st.markdown(custom_style, unsafe_allow_html=True)


def section_header(title: str, subtitle: str | None = None) -> None:
    """Render a consistent header block for each section."""

    st.markdown(
        f"""
        <div class="section-card" style="border-left: 5px solid var(--app-accent);">
            <h2 style="margin-bottom:0.3rem;">{title}</h2>
            {f'<p class="form-tooltip">{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )
