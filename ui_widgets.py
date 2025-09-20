# ui_widget.py
import streamlit as st
import pandas as pd


def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    df = df.copy()

    # Format Last Eaten
    if last_col in df.columns:
        df[last_col] = pd.to_datetime(df[last_col], errors="coerce")
        df[last_col] = df[last_col].dt.strftime("%d-%m-%Y")
        df[last_col] = df[last_col].fillna("")

    # Format Days Ago: int, or '-'
    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)

    cols = list(df.columns)
    thead_cells = "".join(f"<th>{c}</th>" for c in cols)
    tbody_rows = ""
    for _, r in df.iterrows():
        row_cells = ""
        for c in cols:
            v = r[c] if pd.notna(r[c]) else ""
            v = "" if v is None else v
            if c == days_col:
                row_cells += f"<td class='daysago'>{v}</td>"
            else:
                row_cells += f"<td>{v}</td>"
        tbody_rows += f"<tr>{row_cells}</tr>"
    full_html = f"<div class='nb-table-wrap'><table class='nb-table'><thead><tr>{thead_cells}</tr></thead><tbody>{tbody_rows}</tbody></table></div>"
    return full_html


def display_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    """Wrapper to show styled HTML tables in Streamlit."""
    html = df_to_html_table(df, days_col=days_col, last_col=last_col)
    st.markdown(html, unsafe_allow_html=True)
