# -----------------------------
# FILE: ui_widgets.py
# -----------------------------
import streamlit as st
import pandas as pd


def apply_compact_css():
    st.markdown(
        """
        <style>
        /* tighten top padding but keep title visible */
        .block-container { padding-top: 1rem; }
        /* style tables generated via to_html */
        .table-container table { border-collapse: collapse; width:100%; }
        .table-container th, .table-container td { border: 1px solid #e6e6e6; padding: 8px; }
        .table-container th { background-color: #fafafa; text-align: left; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Render a table (no index) and provide a radio control underneath
def render_selectable_table(df, select_key, show_cols=None, radio_label="Select"):
    if df is None or df.empty:
        st.write("_empty")
        return None

    display = df.copy()
    if show_cols:
        # keep only requested columns that exist
        cols_to_show = [c for c in show_cols if c in display.columns]
        display = display[cols_to_show]

    # Format Last Eaten column to DD-MM-YYYY if present
    if "Last Eaten" in display.columns:
        display["Last Eaten"] = pd.to_datetime(display["Last Eaten"], errors="coerce").dt.strftime("%d-%m-%Y")
        display["Last Eaten"] = display["Last Eaten"].fillna("")

    # Ensure Days Ago shown as integer or empty
    if "Days Ago" in display.columns:
        display["Days Ago"] = display["Days Ago"].apply(lambda x: (str(int(x)) if pd.notna(x) else ""))

    # Generate HTML table without index
    html = display.to_html(index=False, escape=False)

    # Determine which column is Days Ago to apply center narrow style
    days_idx = None
    if "Days Ago" in display.columns:
        days_idx = list(display.columns).index("Days Ago") + 1

    # inject wrapper with CSS for centering days column (if found)
    style = ""
    if days_idx:
        style = f"<style> .table-container td:nth-child({days_idx}), .table-container th:nth-child({days_idx}) {{ text-align:center; width:60px; }} </style>"

    st.markdown(f"<div class='table-container'>{style}{html}</div>", unsafe_allow_html=True)

    # Provide radio with Recipe names (use first column assumed to be Recipe or explicit 'Recipe')
    recipe_col = None
    for c in ["Recipe", display.columns[0]]:
        if c in display.columns:
            recipe_col = c
            break

    if recipe_col is None:
        st.warning("No recipe column found to select.")
        return None

    options = display[recipe_col].astype(str).tolist()
    if not options:
        st.info("No options to select.")
        return None

    selected = st.radio(radio_label, options, key=select_key)
    return selected


