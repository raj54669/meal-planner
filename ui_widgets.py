# ui_widgets.py
import streamlit as st
import pandas as pd


def apply_global_styles():
    """Inject global CSS for dropdowns, labels, buttons, and other UI elements."""
    st.markdown("""
    <style>
    /* Label styling */
    .stSelectbox label {
        font-size: 14px !important;
        font-weight: 600 !important;
        margin-bottom: 4px !important;
    }

    /* Dropdown box styling */
    .stSelectbox div[data-baseweb="select"] > div {
        font-size: 13px !important;       /* match font size */
        font-weight: bold !important;
        padding: 2px 8px !important;      /* tighter padding */
        line-height: 1.2 !important;
        min-height: 28px !important;      /* smaller height */
    }

    /* Dropdown container (extra space below) */
    .stSelectbox {
        margin-bottom: 16px !important;   /* space below dropdown */
    }

    /* Align items properly */
    .stSelectbox div[data-baseweb="select"] {
        align-items: center !important;
        height: auto !important;
    }

    /* Hover option styling */
    .stSelectbox [data-baseweb="option"]:hover {
        background-color: #e0e0e0 !important;
        font-weight: 600 !important;
    }

    /* Light mode dropdown */
    [data-theme="light"] .stSelectbox div[data-baseweb="select"] > div {
        color: black !important;
        background-color: #f3f4f6 !important;
    }

    /* Dark mode dropdown */
    [data-theme="dark"] .stSelectbox div[data-baseweb="select"] > div {
        color: white !important;
        background-color: #333 !important;
    }   /* ← this closing brace was missing */

    /* 🔵 Base Style (keep your working blue buttons) */
    .stButton > button, .stForm button {
        font-weight: 700 !important;
        background-color: #004080 !important;  /* Dark Blue */
        color: white !important;
        border-radius: 6px !important;
        border: 1px solid #003060 !important;
        padding: 6px 16px !important;
        font-size: 14px !important;
        transition: background-color 0.2s ease, transform 0.1s ease;
    }
    .stButton > button:hover, .stForm button:hover {
        background-color: #0059b3 !important;
        border-color: #004080 !important;
        transform: scale(1.03);
    }
    
    /* ✅ Save Edit (green) */
    div[data-testid="stButton"][data-testid-button-key="save_edit"] button {
        background-color: #2e7d32 !important;
        border-color: #1b5e20 !important;
    }
    div[data-testid="stButton"][data-testid-button-key="save_edit"] button:hover {
        background-color: #1b5e20 !important;
    }
    
    /* ⚠️ Cancel (yellow-orange, safe) */
    div[data-testid="stButton"][data-testid-button-key*="cancel"] button {
        background-color: #ffb300 !important;  /* amber */
        border-color: #fb8c00 !important;
        color: black !important;
    }
    div[data-testid="stButton"][data-testid-button-key*="cancel"] button:hover {
        background-color: #fb8c00 !important;
    }
    
    /* 🗑️ Delete + Confirm Delete (red, dangerous) */
    div[data-testid="stButton"][data-testid-button-key^="delete_"] button,
    div[data-testid="stButton"][data-testid-button-key="confirm_delete"] button {
        background-color: #c62828 !important;
        border-color: #8e0000 !important;
    }
    div[data-testid="stButton"][data-testid-button-key^="delete_"] button:hover,
    div[data-testid="stButton"][data-testid-button-key="confirm_delete"] button:hover {
        background-color: #b71c1c !important;
    }

    
    </style>
    """, unsafe_allow_html=True)

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
        font-size: 12px;
        font-weight: bold;
    }}
    .nb-table th {{
        background-color: #004080;  /* Dark Blue */
        color: white;
        padding: 6px 8px;
        text-align: center;
        font-size: 12px;
    }}
    .nb-table td {{
        background-color: #f0f4f8;  /* Light Gray-Blue */
        color: black;
        padding: 6px 8px;
        text-align: center;
        font-size: 12px;
    }}
    .nb-table, .nb-table th, .nb-table td {{
        border: 1px solid #000;
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
