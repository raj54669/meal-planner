# ui_widgets.py
import streamlit as st
import pandas as pd
from html import escape
import random

# compact CSS: reduces top whitespace and styles Days Ago column
def apply_compact_css():
    css = """
    <style>
    /* reduce top spacing around the page title & headers */
    .block-container { padding-top: 1rem; padding-left: 3rem; padding-right: 3rem; }
    /* table tweaks produced by pandas .to_html */
    .prefs_table { border-collapse: collapse; width: 100%; }
    .prefs_table th { background: #f7f7f8; text-align: left; padding: 10px; border: 1px solid #eee; }
    .prefs_table td { padding: 10px; border: 1px solid #eee; vertical-align: middle; }
    /* DaysAgo narrow and center */
    .prefs_table td.daysago, .prefs_table th.daysago { width: 60px; text-align: center; }
    /* make recipe column a bit wider */
    .prefs_table td.recipe { width: 45%; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def _df_to_styled_html(df: pd.DataFrame, days_col: str = "Days Ago"):
    """
    Convert df to styled HTML table string, expects df to be small.
    - Assumes df has columns including recipe/itemtype/last eaten/days ago.
    - Adds classes so CSS can target daysago cell.
    """
    # Prepare display strings (escape to avoid HTML issues)
    html = ['<table class="prefs_table">']
    # header
    html.append("<thead><tr>")
    for col in df.columns:
        cls = ""
        if col == days_col:
            cls = ' class="daysago"'
        html.append(f"<th{cls}>{escape(col)}</th>")
    html.append("</tr></thead>")
    # rows
    html.append("<tbody>")
    for _, row in df.iterrows():
        html.append("<tr>")
        for col in df.columns:
            val = "" if pd.isna(row[col]) else row[col]
            cls = ""
            if col == days_col:
                cls = ' class="daysago"'
            if col.lower().startswith("recipe"):
                cls = (cls + ' recipe').strip()
            html.append(f"<td{cls}>{escape(str(val))}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    return "\n".join(html)

def render_selectable_table(df: pd.DataFrame, select_key: str, show_cols=None, radio_label="Select recipe to save for today"):
    """
    - df: DataFrame containing at minimum a 'Recipe' column.
    - show_cols: list of columns to show in the table order (if None show all).
    Returns the selected Recipe string (or None).
    Renders an HTML table (no index), formats Last Eaten as DD-MM-YYYY, centers Days Ago.
    Also renders radio buttons beneath for selection (radio keys use select_key).
    """
    if df is None or df.empty:
        st.markdown("<div>empty</div>", unsafe_allow_html=True)
        st.radio(radio_label, options=["No options to select."], key=select_key, index=0, disabled=True)
        return None

    display_df = df.copy().reset_index(drop=True)
    # ensure columns exist
    if show_cols:
        for c in show_cols:
            if c not in display_df.columns:
                display_df[c] = pd.NA
        display_df = display_df[show_cols].copy()

    # Format Last Eaten column as DD-MM-YYYY if present
    if "Last Eaten" in display_df.columns:
        display_df["Last Eaten"] = display_df["Last Eaten"].apply(lambda d: pd.to_datetime(d).strftime("%d-%m-%Y") if pd.notna(d) else "")
    # Days Ago: show as integer or blank
    if "Days Ago" in display_df.columns:
        def fmt_days(x):
            try:
                if pd.isna(x):
                    return ""
                else:
                    return str(int(x))
            except Exception:
                return ""
        display_df["Days Ago"] = display_df["Days Ago"].apply(fmt_days)

    # reorder columns: if Item Type exists and recipe first desired, keep as-is
    # produce HTML
    html = _df_to_styled_html(display_df, days_col="Days Ago")
    st.markdown(html, unsafe_allow_html=True)

    # radio options: use Recipe values for selection
    if "Recipe" in df.columns:
        recipes = display_df["Recipe"].astype(str).tolist()
    else:
        recipes = [str(r) for r in display_df.iloc[:,0].tolist()]

    # show radio selection
    selected = st.radio(radio_label, options=recipes, key=select_key)
    return selected
