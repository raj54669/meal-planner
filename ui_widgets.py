import streamlit as st
import pandas as pd

def df_to_html_table(df: pd.DataFrame):
    df = df.copy()

    # ✅ Fix date formatting (DD-MM-YYYY)
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%d-%m-%Y")

    css = """
    <style>
        .blue-table {
            border-collapse: collapse;
            width: 100%;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 14px;
        }
        .blue-table th, .blue-table td {
            border: 1px solid #000;
            padding: 8px;
            text-align: center; /* Center alignment */
        }
        .blue-table th {
            background-color: #004080; /* Dark blue */
            color: white !important;
            font-weight: 900 !important; /* Force bold */
        }
        .blue-table td {
            font-weight: normal !important;
        }
    </style>
    """

    cols = list(df.columns)
    thead_cells = "".join(f"<th>{c}</th>" for c in cols)

    tbody_rows = ""
    for _, r in df.iterrows():
        row_cells = "".join(f"<td>{'' if pd.isna(v) else v}</td>" for v in r)
        tbody_rows += f"<tr>{row_cells}</tr>"

    full_html = f"{css}<table class='blue-table'><thead><tr>{thead_cells}</tr></thead><tbody>{tbody_rows}</tbody></table>"
    return full_html


def display_table(df: pd.DataFrame):
    """Render styled table in Streamlit."""
    html = df_to_html_table(df)
    st.markdown(html, unsafe_allow_html=True)
