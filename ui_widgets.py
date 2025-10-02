# ui_widgets.py
import streamlit as st
import pandas as pd


def apply_global_styles():
    """Inject global CSS for dropdowns, labels, buttons, titles, headers and other UI elements."""
    st.markdown("""
    <style>
    /* ===== Remove top white space ===== */
    .block-container {
        padding-top: 1rem !important;
    }

    /* ===== Main Page Title (st.title) ===== */
    h1 {
        text-align: center;
        font-family: 'Trebuchet MS', sans-serif;
        font-size: 2.6rem !important;
        font-weight: 800 !important;
        margin-bottom: 1rem;
    }

    /* ===== Section Headers (st.header) ===== */
    h2 {
        text-align: left;
        font-family: 'Trebuchet MS', sans-serif;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin-top: 1.5rem;
        margin-bottom: 0.75rem;
    }

    /* ===== Light Mode Colors ===== */
    body[data-theme="light"] h1 {
        color: #2E86C1;   /* Deep blue */
    }
    body[data-theme="light"] h2 {
        color: #117A65;   /* Dark teal */
    }

    /* ===== Dark Mode Colors ===== */
    body[data-theme="dark"] h1 {
        color: #5DADE2;   /* Lighter blue */
    }
    body[data-theme="dark"] h2 {
        color: #48C9B0;   /* Bright teal */
    }

    /* ===== Your existing dropdown & button styles (kept as is) ===== */
    .stSelectbox label {
        font-size: 14px !important;
        font-weight: 600 !important;
        margin-bottom: 4px !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        font-size: 13px !important;
        font-weight: bold !important;
        padding: 2px 8px !important;
        line-height: 1.2 !important;
        min-height: 28px !important;
    }
    .stSelectbox {
        margin-bottom: 16px !important;
    }
    .stSelectbox div[data-baseweb="select"] {
        align-items: center !important;
        height: auto !important;
    }
    .stSelectbox [data-baseweb="option"]:hover {
        background-color: #e0e0e0 !important;
        font-weight: 600 !important;
    }
    [data-theme="light"] .stSelectbox div[data-baseweb="select"] > div {
        color: black !important;
        background-color: #f3f4f6 !important;
    }
    [data-theme="dark"] .stSelectbox div[data-baseweb="select"] > div {
        color: white !important;
        background-color: #333 !important;
    }

    .stButton > button,
    .stForm button,
    div[data-testid="stButton"] button {
        font-weight: 700 !important;
        background-color: #004080 !important;
        color: #ffffff !important;
        border-radius: 6px !important;
        border: 1px solid #003060 !important;
        padding: 6px 14px !important;
        font-size: 14px !important;
        transition: background-color 0.15s ease, transform 0.08s ease, box-shadow 0.12s ease;
        box-shadow: none !important;
    }
    .stButton > button:hover,
    .stForm button:hover,
    div[data-testid="stButton"] button:hover {
        background-color: #0059b3 !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:focus,
    .stForm button:focus,
    div[data-testid="stButton"] button:focus {
        outline: none !important;
        box-shadow: 0 0 0 4px rgba(0,80,128,0.12) !important;
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
