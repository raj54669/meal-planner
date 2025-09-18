import streamlit as st
import pandas as pd
from data_manager import load_master_list, load_history, save_today_pick, save_master_list
from ui_widgets import render_table

# ----------------- App Title -----------------
st.set_page_config(page_title="NextBite – Meal Planner", layout="wide")
st.title("🍴 NextBite – Meal Planner App")

# ----------------- GitHub Setup -----------------
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
    GITHUB_BRANCH = st.secrets["GITHUB_BRANCH"]
    MASTER_CSV = st.secrets["MASTER_CSV"]
    HISTORY_CSV = st.secrets["HISTORY_CSV"]
except Exception:
    st.warning("⚠️ GitHub secrets not found. Using local CSVs instead.")
    GITHUB_TOKEN = None
    GITHUB_REPO = None
    GITHUB_BRANCH = None
    MASTER_CSV = "master_list.csv"
    HISTORY_CSV = "history.csv"

# ----------------- Load Data -----------------
master_df = load_master_list(MASTER_CSV)
history_df = load_history(HISTORY_CSV)

# Ensure Days Ago is integer (no decimals)
if "Days Ago" in master_df.columns:
    master_df["Days Ago"] = master_df["Days Ago"].apply(
        lambda x: int(x) if pd.notnull(x) else "-"
    )

# ----------------- Navigation -----------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# ----------------- Pick Today’s Recipe -----------------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")

    option = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"])

    if option == "By Item Type":
        item_types = master_df["Item Type"].dropna().unique().tolist()
        item_type = st.selectbox("Select Item Type:", ["-- Choose --"] + item_types)

        if item_type != "-- Choose --":
            filtered = master_df[master_df["Item Type"] == item_type]

            # Format Days Ago properly
            filtered["Days Ago"] = filtered["Days Ago"].apply(
                lambda x: int(x) if isinstance(x, (int, float)) else x
            )

            # Render table with custom column widths
            render_table(
                filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]],
                col_widths={"Recipe": "200px", "Item Type": "120px", "Last Eaten": "120px", "Days Ago": "120px"},
                center_cols=["Days Ago"]
            )

            choice = st.radio("Select recipe to save for today", filtered["Recipe"])
            if st.button("Save Today’s Pick"):
                save_today_pick(choice, HISTORY_CSV)
                st.success(f"✅ Today's pick saved: **{choice}**")

    elif option == "Today's Suggestions":
        suggestions = master_df.sort_values("Days Ago", ascending=False).head(10)

        suggestions["Days Ago"] = suggestions["Days Ago"].apply(
            lambda x: int(x) if isinstance(x, (int, float)) else x
        )

        render_table(
            suggestions[["Recipe", "Item Type", "Last Eaten", "Days Ago"]],
            col_widths={"Recipe": "200px", "Item Type": "120px", "Last Eaten": "120px", "Days Ago": "120px"},
            center_cols=["Days Ago"]
        )

# ----------------- Master List -----------------
elif page == "Master List":
    st.header("Master List of Recipes")
    render_table(master_df, col_widths={"Recipe": "200px", "Item Type": "150px", "Last Eaten": "120px", "Days Ago": "120px"}, center_cols=["Days Ago"])

# ----------------- History -----------------
elif page == "History":
    st.header("History of Picks")
    render_table(history_df, col_widths={"Recipe": "200px", "Item Type": "150px", "Last Eaten": "120px"}, center_cols=[])
