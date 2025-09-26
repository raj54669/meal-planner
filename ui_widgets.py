# ui_widgets.py
import streamlit as st
import pandas as pd

# -----------------------
# Original table functions (fixed to always render HTML)
# -----------------------
def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    df = df.copy()

    # Format Last Eaten column (DD-MM-YYYY)
    if last_col in df.columns:
        df[last_col] = pd.to_datetime(df[last_col], errors="coerce")
        df[last_col] = df[last_col].dt.strftime("%d-%m-%Y")
        df[last_col] = df[last_col].fillna("")

    # Format Days Ago column
    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)

    # Build HTML table
    cols = list(df.columns)
    thead_cells = "".join(f"<th>{c}</th>" for c in cols)
    tbody_rows = ""
    for _, r in df.iterrows():
        row_cells = "".join(f"<td>{'' if pd.isna(r[c]) else r[c]}</td>" for c in cols)
        tbody_rows += f"<tr>{row_cells}</tr>"

    # Full HTML + CSS styling (Vehicle Pricing Style + auto light/dark)
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
        font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
        font-size: 13px;
        font-weight: bold;
    }}
    .nb-table th {{
        background-color: #004080;  /* Dark Blue */
        color: white;
        padding: 6px 8px;
        text-align: center;
        font-size: 13px;
    }}
    .nb-table td {{
        background-color: #f0f4f8;  /* Light Gray-Blue */
        color: black;
        padding: 6px 8px;
        text-align: center;
        font-size: 13px;
    }}
    .nb-table, .nb-table th, .nb-table td {{
        border: 1px solid #000;
    }}
    /* Dark mode override */
    @media (prefers-color-scheme: dark) {{
        .nb-table th {{
            background-color: #222;
            color: #eee;
        }}
        .nb-table td {{
            background-color: #1e1e1e;
            color: #eee;
        }}
        .nb-table, .nb-table th, .nb-table td {{
            border: 1px solid #444;
        }}
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
