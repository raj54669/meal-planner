# ui_widgets.py
import streamlit as st
import pandas as pd


def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    """Convert a dataframe into custom HTML table (no direct Streamlit dataframe)."""
    df = df.copy()

    # Format Last Eaten column
    if last_col in df.columns:
        df[last_col] = pd.to_datetime(df[last_col], errors="coerce")
        df[last_col] = df[last_col].dt.strftime("%d-%m-%Y")
        df[last_col] = df[last_col].fillna("")

    # Format Days Ago: integer, or '-'
    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)

    # Build HTML table manually
    cols = list(df.columns)
    thead_cells = "".join(f"<th>{c}</th>" for c in cols)
    tbody_rows = ""
    for _, r in df.iterrows():
        row_cells = ""
        for c in cols:
            v = r[c] if pd.notna(r[c]) else ""
            v = "" if v is None else v
            if c == days_col:
                row_cells += f"<td class='days-col'>{v}</td>"
            else:
                row_cells += f"<td class='normal-col'>{v}</td>"
        tbody_rows += f"<tr>{row_cells}</tr>"

    full_html = f"""
    <div class='custom-table-wrap'>
        <table class='custom-table'>
            <thead><tr>{thead_cells}</tr></thead>
            <tbody>{tbody_rows}</tbody>
        </table>
    </div>
    """
    return full_html


def display_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    """Wrapper to show styled HTML tables in Streamlit with custom CSS."""
    if df.empty:
        st.info("No data available.")
        return

    html = df_to_html_table(df, days_col=days_col, last_col=last_col)

    css = """
    <style>
        .custom-table {
            border-collapse: collapse;
            width: 100%;
        }
        .custom-table th, .custom-table td {
            border: 1px solid #eee;
            padding: 6px 8px;
            text-align: center;
        }
        .custom-table th {
            background: #fafafa;
            text-align: left;
        }
        .custom-table td.normal-col {
            text-align: left;
            white-space: nowrap;
        }
        .custom-table td.days-col, 
        .custom-table th.days-col {
            min-width: 80px;
            text-align: center;
            font-weight: bold;
        }
    </style>
    """

    st.markdown(css + html, unsafe_allow_html=True)
