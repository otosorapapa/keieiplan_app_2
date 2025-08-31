import streamlit as st
import pandas as pd
import numpy as np
import math
from typing import Dict, Tuple

st.set_page_config(
    page_title="経営計画策定（単年）｜Streamlit",
    page_icon="📈",
    layout="wide",
)

DEFAULTS = {
    "sales": 1_000_000_000.0,
    "fte": 20.0,
    "cogs_mat_rate": 0.25,
    "cogs_lbr_rate": 0.06,
    "cogs_out_src_rate": 0.10,
    "cogs_out_con_rate": 0.04,
    "cogs_oth_rate": 0.0,
    "opex_h_rate": 0.17,
    "opex_k_rate": 0.468,
    "opex_dep_rate": 0.006,
    "noi_misc_rate": 0.0001,
    "noi_grant_rate": 0.0,
    "noi_oth_rate": 0.0,
    "noe_int_rate": 0.0074,
    "noe_oth_rate": 0.0,
    "unit": "円",
}

ITEMS = [
    ("REV", "売上高", "売上"),
    ("COGS_MAT", "外部仕入｜材料費", "外部仕入"),
    ("COGS_LBR", "外部仕入｜労務費(外部)", "外部仕入"),
    ("COGS_OUT_SRC", "外部仕入｜外注費(専属)", "外部仕入"),
    ("COGS_OUT_CON", "外部仕入｜外注費(委託)", "外部仕入"),
    ("COGS_OTH", "外部仕入｜その他諸経費", "外部仕入"),
    ("COGS_TTL", "外部仕入｜計", "外部仕入"),
    ("GROSS", "粗利(加工高)", "粗利"),
    ("OPEX_H", "内部費用｜人件費", "内部費用"),
    ("OPEX_K", "内部費用｜経費", "内部費用"),
    ("OPEX_DEP", "内部費用｜減価償却費", "内部費用"),
    ("OPEX_TTL", "内部費用｜計", "内部費用"),
    ("OP", "営業利益", "損益"),
    ("NOI_MISC", "営業外収益｜雑収入", "営業外"),
    ("NOI_GRANT", "営業外収益｜補助金/給付金", "営業外"),
    ("NOI_OTH", "営業外収益｜その他", "営業外"),
    ("NOE_INT", "営業外費用｜支払利息", "営業外"),
    ("NOE_OTH", "営業外費用｜雑損", "営業外"),
    ("ORD", "経常利益", "損益"),
    ("BE_SALES", "損益分岐点売上高", "KPI"),
    ("PC_SALES", "一人当たり売上", "KPI"),
    ("PC_GROSS", "一人当たり粗利", "KPI"),
    ("PC_ORD", "一人当たり経常利益", "KPI"),
    ("LDR", "労働分配率", "KPI"),
]

ITEM_LABELS = {code: label for code, label, _ in ITEMS}


def format_money(x: float) -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return "—"
    return f"¥{x:,.0f}"


class PlanConfig:
    def __init__(self, base_sales: float, fte: float, unit: str) -> None:
        self.base_sales = base_sales
        self.fte = max(0.0001, fte)
        self.unit = unit
        self.items: Dict[str, Dict[str, float]] = {}

    def set_rate(self, code: str, rate: float, rate_base: str = "sales") -> None:
        self.items[code] = {"method": "rate", "value": float(rate), "rate_base": rate_base}

    def set_amount(self, code: str, amount: float) -> None:
        self.items[code] = {"method": "amount", "value": float(amount), "rate_base": "fixed"}

    def clone(self) -> "PlanConfig":
        c = PlanConfig(self.base_sales, self.fte, self.unit)
        c.items = {k: v.copy() for k, v in self.items.items()}
        return c


def compute(plan: PlanConfig, sales_override: float | None = None, amount_overrides: Dict[str, float] | None = None) -> Dict[str, float]:
    S = float(plan.base_sales if sales_override is None else sales_override)
    amt = {code: 0.0 for code, *_ in ITEMS}
    amt["REV"] = S

    def line_amount(code, gross_guess):
        cfg = plan.items.get(code, None)
        if amount_overrides and code in amount_overrides:
            return float(amount_overrides[code])
        if cfg is None:
            return 0.0
        if cfg["method"] == "amount":
            return float(cfg["value"])
        r = float(cfg["value"])
        base = cfg.get("rate_base", "sales")
        if base == "sales":
            return S * r
        elif base == "gross":
            return max(0.0, gross_guess) * r
        elif base == "fixed":
            return r
        return S * r

    cogs_codes = ["COGS_MAT", "COGS_LBR", "COGS_OUT_SRC", "COGS_OUT_CON", "COGS_OTH"]
    sales_based_cogs = 0.0
    for code in cogs_codes:
        cfg = plan.items.get(code)
        if cfg and cfg["method"] == "rate" and cfg.get("rate_base", "sales") == "sales":
            sales_based_cogs += S * float(cfg["value"])
        elif cfg and cfg["method"] == "amount":
            sales_based_cogs += float(cfg["value"])

    gross = S - sales_based_cogs
    for _ in range(5):
        cogs = 0.0
        for code in cogs_codes:
            cogs += max(0.0, line_amount(code, gross))
        gross_new = S - cogs
        if abs(gross_new - gross) < 1e-6:
            gross = gross_new
            break
        gross = gross_new

    cogs_total = 0.0
    for code in cogs_codes:
        val = max(0.0, line_amount(code, gross))
        amt[code] = val
        cogs_total += val
    amt["COGS_TTL"] = cogs_total
    amt["GROSS"] = S - cogs_total

    opex_codes = ["OPEX_H", "OPEX_K", "OPEX_DEP"]
    opex_total = 0.0
    for code in opex_codes:
        val = max(0.0, line_amount(code, amt["GROSS"]))
        amt[code] = val
        opex_total += val
    amt["OPEX_TTL"] = opex_total

    amt["OP"] = amt["GROSS"] - amt["OPEX_TTL"]

    noi_codes = ["NOI_MISC", "NOI_GRANT", "NOI_OTH"]
    noe_codes = ["NOE_INT", "NOE_OTH"]
    for code in noi_codes + noe_codes:
        val = max(0.0, line_amount(code, amt["GROSS"]))
        amt[code] = val

    amt["ORD"] = amt["OP"] + (amt["NOI_MISC"] + amt["NOI_GRANT"] + amt["NOI_OTH"]) - (amt["NOE_INT"] + amt["NOE_OTH"])

    var_cost = 0.0
    for code in cogs_codes + opex_codes + noi_codes + noe_codes:
        cfg = plan.items.get(code)
        if cfg and cfg["method"] == "rate" and cfg.get("rate_base", "sales") in ("sales", "gross"):
            if cfg.get("rate_base") == "gross":
                g_ratio = amt["GROSS"] / S if S > 0 else 0.0
                var_cost += S * (cfg["value"] * g_ratio)
            else:
                var_cost += S * cfg["value"]

    fixed_cost = 0.0
    for code in cogs_codes + opex_codes + noi_codes + noe_codes:
        cfg = plan.items.get(code)
        if cfg and cfg["method"] == "amount":
            fixed_cost += cfg["value"]
        elif cfg and cfg.get("rate_base") == "fixed":
            if cfg["method"] == "rate":
                fixed_cost += cfg["value"]
    cm_ratio = 1.0 - (var_cost / S if S > 0 else 0.0)
    if cm_ratio <= 0:
        be_sales = float("inf")
    else:
        be_sales = fixed_cost / cm_ratio
    amt["BE_SALES"] = be_sales

    fte = max(0.0001, plan.fte)
    amt["PC_SALES"] = amt["REV"] / fte
    amt["PC_GROSS"] = amt["GROSS"] / fte
    amt["PC_ORD"] = amt["ORD"] / fte
    amt["LDR"] = (amt["OPEX_H"] / amt["GROSS"]) if amt["GROSS"] > 0 else np.nan

    return amt


def dual_input(label: str, base_value, mode: str, pct_key: str, abs_key: str, *, kind: str = "amount", pct_range: Tuple[float, float] = (-0.5, 0.5), abs_min: float = 0.0):
    state = st.session_state
    flag_key = f"_{pct_key}_lock"
    state.setdefault(flag_key, False)
    if kind == "amount":
        base_amt = float(base_value)
        state.setdefault(pct_key, 0.0)
        state.setdefault(abs_key, base_amt)
    else:
        base_rate, base_sales = base_value
        base_amt = base_sales * base_rate
        state.setdefault(pct_key, 0.0)
        state.setdefault(abs_key, base_rate)

    if mode == "％":
        state.setdefault(f"{pct_key}_slider", state[pct_key])
        state.setdefault(f"{pct_key}_num", state[pct_key])
        state.setdefault(f"{abs_key}_slider", state[abs_key])
        state.setdefault(f"{abs_key}_num", state[abs_key])

        def slider_cb():
            if state[flag_key]:
                return
            state[flag_key] = True
            p = state[f"{pct_key}_slider"]
            state[pct_key] = p
            state[f"{pct_key}_num"] = p
            if kind == "amount":
                state[abs_key] = base_amt * (1 + p)
            else:
                state[abs_key] = base_rate + p
            state[f"{abs_key}_slider"] = state[abs_key]
            state[f"{abs_key}_num"] = state[abs_key]
            state[f"qc_{pct_key}"] = state[pct_key]
            state[f"qc_{abs_key}"] = state[abs_key]
            state[flag_key] = False

        def num_cb():
            if state[flag_key]:
                return
            state[flag_key] = True
            p = state[f"{pct_key}_num"]
            state[pct_key] = p
            state[f"{pct_key}_slider"] = p
            if kind == "amount":
                state[abs_key] = base_amt * (1 + p)
            else:
                state[abs_key] = base_rate + p
            state[f"{abs_key}_slider"] = state[abs_key]
            state[f"{abs_key}_num"] = state[abs_key]
            state[f"qc_{pct_key}"] = state[pct_key]
            state[f"qc_{abs_key}"] = state[abs_key]
            state[flag_key] = False

        st.slider(
            label,
            min_value=pct_range[0],
            max_value=pct_range[1],
            step=0.01,
            key=f"{pct_key}_slider",
            on_change=slider_cb,
        )
        st.number_input(
            f"{label}（%)" if kind == "amount" else f"{label}(pt)",
            min_value=pct_range[0],
            max_value=pct_range[1],
            step=0.01,
            key=f"{pct_key}_num",
            on_change=num_cb,
        )
        slider_cb()
        if kind == "amount":
            st.caption(f"実額: {format_money(state[abs_key])}")
            return {"target": state[abs_key], "pct": state[pct_key]}
        else:
            st.caption(f"粗利額: {format_money((base_rate + state[pct_key]) * base_sales)}")
            return {"target_gp": state[abs_key], "pt": state[pct_key]}
    else:
        state.setdefault(f"{pct_key}_slider", state[pct_key])
        state.setdefault(f"{pct_key}_num", state[pct_key])
        state.setdefault(f"{abs_key}_slider", state[abs_key])
        state.setdefault(f"{abs_key}_num", state[abs_key])
        max_abs = base_amt * (1 + pct_range[1]) if kind == "amount" else base_sales

        def slider_cb():
            if state[flag_key]:
                return
            state[flag_key] = True
            a = state[f"{abs_key}_slider"]
            state[abs_key] = a
            state[f"{abs_key}_num"] = a
            if kind == "amount":
                state[pct_key] = a / base_amt - 1 if base_amt else 0.0
            else:
                state[pct_key] = a - base_rate
            state[f"{pct_key}_slider"] = state[pct_key]
            state[f"{pct_key}_num"] = state[pct_key]
            state[f"qc_{pct_key}"] = state[pct_key]
            state[f"qc_{abs_key}"] = state[abs_key]
            state[flag_key] = False

        def num_cb():
            if state[flag_key]:
                return
            state[flag_key] = True
            a = state[f"{abs_key}_num"]
            state[abs_key] = a
            state[f"{abs_key}_slider"] = a
            if kind == "amount":
                state[pct_key] = a / base_amt - 1 if base_amt else 0.0
            else:
                state[pct_key] = a - base_rate
            state[f"{pct_key}_slider"] = state[pct_key]
            state[f"{pct_key}_num"] = state[pct_key]
            state[f"qc_{pct_key}"] = state[pct_key]
            state[f"qc_{abs_key}"] = state[abs_key]
            state[flag_key] = False

        st.slider(
            label,
            min_value=abs_min,
            max_value=max_abs,
            step=max(1_000_000.0, max_abs / 1000),
            key=f"{abs_key}_slider",
            on_change=slider_cb,
        )
        st.number_input(
            f"{label}（円）",
            min_value=abs_min,
            step=1_000_000.0,
            key=f"{abs_key}_num",
            on_change=num_cb,
        )
        slider_cb()
        if kind == "amount":
            st.caption(f"増減: {state[pct_key]*100:.1f}%")
            return {"target": state[abs_key], "pct": state[pct_key]}
        else:
            st.caption(f"pt: {state[pct_key]*100:.1f}pt")
            return {"target_gp": state[abs_key], "pt": state[pct_key]}


def quick_slider(label: str, base_value, mode: str, pct_key: str, abs_key: str, *, kind: str = "amount", pct_range: Tuple[float, float] = (-0.5, 0.5), abs_min: float = 0.0):
    state = st.session_state
    if kind == "amount":
        base_amt = float(base_value)
    else:
        base_rate, base_sales = base_value
        base_amt = base_sales * base_rate
    if mode == "％":
        state.setdefault(f"qc_{pct_key}", state.get(pct_key, 0.0))
        def qc_cb():
            p = state[f"qc_{pct_key}"]
            state[pct_key] = p
            if kind == "amount":
                state[abs_key] = base_amt * (1 + p)
            else:
                state[abs_key] = base_rate + p
            state[f"{pct_key}_slider"] = state[pct_key]
            state[f"{pct_key}_num"] = state[pct_key]
            state[f"{abs_key}_slider"] = state[abs_key]
            state[f"{abs_key}_num"] = state[abs_key]
        st.slider(
            label,
            min_value=pct_range[0],
            max_value=pct_range[1],
            step=0.01,
            key=f"qc_{pct_key}",
            on_change=qc_cb,
        )
    else:
        default_abs = state.get(abs_key, base_amt if kind == "amount" else base_rate)
        state.setdefault(f"qc_{abs_key}", default_abs)
        max_abs = base_amt * (1 + pct_range[1]) if kind == "amount" else base_sales
        def qc_cb():
            a = state[f"qc_{abs_key}"]
            state[abs_key] = a
            if kind == "amount":
                state[pct_key] = a / base_amt - 1 if base_amt else 0.0
            else:
                state[pct_key] = a - base_rate
            state[f"{pct_key}_slider"] = state[pct_key]
            state[f"{pct_key}_num"] = state[pct_key]
            state[f"{abs_key}_slider"] = a
            state[f"{abs_key}_num"] = a
        st.slider(
            label,
            min_value=abs_min,
            max_value=max_abs,
            step=max(1_000_000.0, max_abs / 1000),
            key=f"qc_{abs_key}",
            on_change=qc_cb,
        )


base_plan = PlanConfig(DEFAULTS["sales"], DEFAULTS["fte"], DEFAULTS["unit"])
base_plan.set_rate("COGS_MAT", DEFAULTS["cogs_mat_rate"])
base_plan.set_rate("COGS_LBR", DEFAULTS["cogs_lbr_rate"])
base_plan.set_rate("COGS_OUT_SRC", DEFAULTS["cogs_out_src_rate"])
base_plan.set_rate("COGS_OUT_CON", DEFAULTS["cogs_out_con_rate"])
base_plan.set_rate("COGS_OTH", DEFAULTS["cogs_oth_rate"])
base_plan.set_rate("OPEX_H", DEFAULTS["opex_h_rate"])
base_plan.set_rate("OPEX_K", DEFAULTS["opex_k_rate"])
base_plan.set_rate("OPEX_DEP", DEFAULTS["opex_dep_rate"])
base_plan.set_rate("NOI_MISC", DEFAULTS["noi_misc_rate"])
base_plan.set_rate("NOI_GRANT", DEFAULTS["noi_grant_rate"])
base_plan.set_rate("NOI_OTH", DEFAULTS["noi_oth_rate"])
base_plan.set_rate("NOE_INT", DEFAULTS["noe_int_rate"])
base_plan.set_rate("NOE_OTH", DEFAULTS["noe_oth_rate"])

base_amt = compute(base_plan)

with st.sidebar:
    mode = st.radio("入力モード", ["％", "実額(円)"], horizontal=True)
    st.markdown("### 計画入力")
    dual_input("売上高", base_amt["REV"], mode, "rev_pct", "rev_target")
    dual_input("粗利率", (base_amt["GROSS"] / base_amt["REV"], base_amt["REV"]), mode, "gp_pt", "gp_target", kind="margin_pt", pct_range=(-0.1, 0.1))
    dual_input("販管費", base_amt["OPEX_K"], mode, "sgna_pct", "sgna_target")
    dual_input("人件費", base_amt["OPEX_H"], mode, "labor_pct", "labor_target")
    dual_input("減価償却費", base_amt["OPEX_DEP"], mode, "dep_pct", "dep_target")
    dual_input("その他", base_amt["NOE_OTH"], mode, "other_pct", "other_target")

left, right = st.columns(2)
with left:
    st.subheader("クイック・コントロール")
    quick_slider("売上高", base_amt["REV"], mode, "rev_pct", "rev_target")
    quick_slider("粗利率", (base_amt["GROSS"] / base_amt["REV"], base_amt["REV"]), mode, "gp_pt", "gp_target", kind="margin_pt", pct_range=(-0.1, 0.1))
    quick_slider("人件費", base_amt["OPEX_H"], mode, "labor_pct", "labor_target")
    quick_slider("販管費", base_amt["OPEX_K"], mode, "sgna_pct", "sgna_target")

with right:
    st.subheader("結果要約")
    sales = st.session_state.get("rev_target", base_amt["REV"])
    gp_rate = st.session_state.get("gp_target", base_amt["GROSS"] / base_amt["REV"])
    overrides = {
        "OPEX_K": st.session_state.get("sgna_target", base_amt["OPEX_K"]),
        "OPEX_H": st.session_state.get("labor_target", base_amt["OPEX_H"]),
        "OPEX_DEP": st.session_state.get("dep_target", base_amt["OPEX_DEP"]),
        "NOE_OTH": st.session_state.get("other_target", base_amt["NOE_OTH"]),
    }
    temp = compute(base_plan, sales_override=sales)
    cogs_other = temp["COGS_MAT"] + temp["COGS_LBR"] + temp["COGS_OUT_SRC"] + temp["COGS_OUT_CON"]
    target_cogs_total = sales * (1 - gp_rate)
    overrides["COGS_OTH"] = max(0.0, target_cogs_total - cogs_other)
    result = compute(base_plan, sales_override=sales, amount_overrides=overrides)
    c1, c2, c3 = st.columns(3)
    c1.metric("売上高", format_money(result["REV"]))
    c2.metric("粗利率", f"{(result['GROSS']/result['REV'])*100:.1f}%")
    c3.metric("営業利益", format_money(result["OP"]))
    c4, c5 = st.columns(2)
    c4.metric("経常利益", format_money(result["ORD"]))
    be_label = "∞" if not math.isfinite(result["BE_SALES"]) else format_money(result["BE_SALES"])
    c5.metric("損益分岐点売上高", be_label)

st.subheader("計画サマリー")
rows = []
for code, label, group in ITEMS:
    if code in ("BE_SALES", "PC_SALES", "PC_GROSS", "PC_ORD", "LDR"):
        continue
    val = result.get(code, 0.0)
    rows.append({"項目": label, "金額": format_money(val)})

st.dataframe(pd.DataFrame(rows), use_container_width=True)
