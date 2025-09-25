# ui_widgets.py
import streamlit as st
import pandas as pd

# -----------------------
# Original table functions (fixed to always render HTML)
# -----------------------
def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    df = df.copy()

    # --- Format Last Eaten column (DD-MM-YYYY) ---
    if last_col in df.columns:
        df[last_col] = pd.to_datetime(df[last_col], errors="coerce")
        df[last_col] = df[last_col].dt.strftime("%d-%m-%Y")
        df[last_col] = df[last_col].fillna("")

    # --- Format Days Ago column ---
    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)

    # --- Build HTML table ---
    cols = list(df.columns)
    thead_cells = "".join(f"<th>{c}</th>" for c in cols)
    tbody_rows = ""
    for _, r in df.iterrows():
        row_cells = ""
        for c in cols:
            v = r[c] if pd.notna(r[c]) else ""
            v = "" if v is None else v
            row_cells += f"<td>{v}</td>"
        tbody_rows += f"<tr>{row_cells}</tr>"

    # --- Full HTML + CSS styling with Light/Dark adaptation ---
    full_html = f"""
    <div class='nb-table-wrap'>
        <table class='nb-table'>
            <thead>
                <tr>{thead_cells}</tr>
            </thead>
            <tbody>
                {tbody_rows}
            </tbody>
        </table>
    </div>
    <style>
    .nb-table {{
        border-collapse: collapse;
        width: 100%;
        font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }}
    .nb-table th, .nb-table td {{
        padding: 6px 8px;
        border: 1px solid #000;
        text-align: center;
        font-weight: 600;
        font-size: 13px;
    }}
    .nb-table thead th {{
        font-size: 14px;
    }}

    /* Light Mode */
    [data-theme="light"] .nb-table thead th {{
        background: #004a99;
        color: white;
    }}
    [data-theme="light"] .nb-table td {{
        background: #f9f9f9;
        color: black;
    }}

    /* Dark Mode */
    [data-theme="dark"] .nb-table thead th {{
        background: #333;
        color: white;
    }}
    [data-theme="dark"] .nb-table td {{
        background: #1e1e1e;
        color: white;
    }}
    </style>
    """
    return full_html


def display_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    """Wrapper to show styled HTML tables in Streamlit with light/dark adaptation."""
    html = df_to_html_table(df, days_col=days_col, last_col=last_col)
    st.markdown(html, unsafe_allow_html=True)


def recipe_card(i, row):
    with st.expander(f"{row['Recipe']} – {row['Item Type']}"):
        col1, col2 = st.columns(2)
        if col1.button("✏️ Edit", key=f"edit_{i}"):
            st.session_state["edit_row"] = i
        if col2.button("🗑️ Delete", key=f"delete_{i}"):
            st.session_state["delete_row"] = i
