# ui_widgets.py
import streamlit as st
import pandas as pd

# CSS to keep tables compact and centered (prevents extreme widening)
_COMPACT_CSS = """
<style>
/* limit main container width for tables and center them */
.block-container { max-width: 960px; padding-left: 1rem; padding-right: 1rem; }

/* smaller font for dataframes to reduce spacing on mobile */
[data-testid="stDataFrameContainer"] table { font-size: 13px; }

/* buttons small */
.stButton>button { padding: .35rem .6rem; font-size: 13px; }

/* reduce expander padding */
section[data-testid="stExpander"] { margin-bottom: 0.5rem; }
</style>
"""

def apply_compact_css():
    st.markdown(_COMPACT_CSS, unsafe_allow_html=True)

def popup_edit(title, recipe_name, item_type, on_save):
    """
    popup editor - open modal if available, else expander fallback.
    on_save is function(new_name, new_type) -> None
    """
    try:
        # Streamlit modal (newer versions)
        with st.modal(title):
            new_name = st.text_input("Recipe Name", value=recipe_name, key=f"modal_name_{title}")
            new_type = st.text_input("Item Type", value=item_type, key=f"modal_type_{title}")
            col1, col2 = st.columns([1,1])
            if col1.button("Save"):
                on_save(new_name.strip(), new_type.strip())
            if col2.button("Cancel"):
                pass
    except Exception:
        # fallback
        with st.expander(title, expanded=True):
            new_name = st.text_input("Recipe Name", value=recipe_name, key=f"exp_name_{title}")
            new_type = st.text_input("Item Type", value=item_type, key=f"exp_type_{title}")
            col1, col2 = st.columns([1,1])
            if col1.button("Save"):
                on_save(new_name.strip(), new_type.strip())
            if col2.button("Cancel"):
                pass

def render_selectable_table(df, select_key="select", show_cols=None, radio_label="Select"):
    """
    Render table rows compactly with a radio selection per row.
    Returns selected_recipe (string) or None.
    show_cols: columns to display in order, default: all
    """
    if df is None or df.empty:
        st.info("No items to show.")
        return None
    df_display = df.copy()
    if show_cols:
        df_display = df_display[show_cols]
    # display header table (without index)
    st.dataframe(df_display.reset_index(drop=True), use_container_width=True)
    # radio below to choose one (to simulate selection dot in row)
    options = df["Recipe"].tolist()
    if not options:
        return None
    selected = st.radio(radio_label, options, key=select_key, index=0)
    return selected
