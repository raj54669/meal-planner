import streamlit as st
import pandas as pd
from data_manager import load_master_list, save_master_list, load_history, save_history
from ui_widgets import display_filtered_table, display_today_suggestions
from datetime import datetime

# CSS to reduce top margin and style tables
st.markdown("""
    <style>
    .block-container {
        padding-top: 1rem;
    }
    table.dataframe th:first-child, table.dataframe td:first-child {
        display: none;
    }
    td, th {
        text-align: center !important;
        vertical-align: middle !important;
    }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(page_title="Meal Planner", layout="wide")

st.title("🥗 Meal Planner with GitHub Storage")

# Load data
master_df = load_master_list()
history_df = load_history()

# Section 1: Add Recipe to Master List
st.subheader("📘 Add Recipe to Master List")
with st.form("add_recipe_form"):
    name = st.text_input("Recipe Name")
    item_type = st.selectbox("Item Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
    calories = st.number_input("Calories", min_value=0, step=10)
    submitted = st.form_submit_button("Add Recipe")
    if submitted and name:
        new_row = {"Recipe": name, "Item Type": item_type, "Calories": calories}
        master_df = pd.concat([master_df, pd.DataFrame([new_row])], ignore_index=True)  # ✅ Fix append
        save_master_list(master_df)
        st.success(f"✅ {name} added to Master List")

# Section 2: Filter Recipes by Item Type
st.subheader("🔎 Filter Recipes by Item Type")
item_filter = st.selectbox("Select Item Type", ["All"] + master_df["Item Type"].unique().tolist())
filtered_df = master_df if item_filter == "All" else master_df[master_df["Item Type"] == item_filter]
display_filtered_table(filtered_df, history_df)

# Section 3: Today’s Suggestions
st.subheader("✨ Today’s Suggestions")
suggestions = master_df.sample(min(5, len(master_df))) if not master_df.empty else pd.DataFrame()
display_today_suggestions(suggestions, history_df)

# Section 4: Save Today’s Pick
st.subheader("📝 Log Today’s Meal")
with st.form("log_meal_form"):
    recipe_choice = st.selectbox("Pick Recipe", master_df["Recipe"].tolist() if not master_df.empty else [])
    log_btn = st.form_submit_button("Save Today’s Pick")
    if log_btn and recipe_choice:
        new_row = {"Recipe": recipe_choice, "Date": datetime.today().strftime("%d-%m-%Y")}
        history_df = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)  # ✅ Fix append
        save_history(history_df)
        st.success(f"✅ Logged {recipe_choice} for today")
