import streamlit as st
import pandas as pd
from datetime import datetime
from data_manager import load_master_list, load_history, save_today_pick
from ui_widgets import format_table

# -------------------------
# App Title
# -------------------------
st.set_page_config(page_title="NextBite – Meal Planner", layout="wide")
st.markdown(
    "<h1 style='text-align: center;'>🍴 NextBite – Meal Planner App</h1>",
    unsafe_allow_html=True,
)

# -------------------------
# Sidebar Navigation
# -------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# -------------------------
# Load Data
# -------------------------
master_df = load_master_list()
history_df = load_history()

# -------------------------
# Pick Today’s Recipe
# -------------------------
if page == "Pick Today’s Recipe":
    st.subheader("Pick Today’s Recipe")

    # check if today already picked
    today = datetime.today().strftime("%d-%m-%Y")
    if not history_df.empty and today in history_df["Date"].values:
        today_pick = history_df.loc[history_df["Date"] == today, "Recipe"].values[0]
        st.success(f"Today's pick is **{today_pick}** (saved earlier).")
        st.info("If you want to change it, delete today's entry from the History tab then pick again.")
    else:
        option = st.radio("Choose option:", ["By Item Type", "Today’s Suggestions"])

        # -------------------------
        # By Item Type Mode
        # -------------------------
        if option == "By Item Type":
            item_types = master_df["Item Type"].dropna().unique()
            selected_type = st.selectbox("Select Item Type:", ["-- Choose --"] + sorted(item_types))

            if selected_type != "-- Choose --":
                recipes = master_df[master_df["Item Type"] == selected_type]["Recipe"].tolist()
                selected_recipe = st.selectbox("Select Recipe:", ["-- Choose --"] + recipes)

                if selected_recipe != "-- Choose --":
                    if st.button("Save Today's Pick"):
                        save_today_pick(selected_recipe, history_df)
                        st.success(f"Today's pick **{selected_recipe}** saved!")

        # -------------------------
        # Today’s Suggestions Mode
        # -------------------------
        elif option == "Today’s Suggestions":
            # merge master with history to get last eaten
            latest_history = history_df.groupby("Recipe")["Date"].max().reset_index()
            merged = master_df.merge(latest_history, on="Recipe", how="left")
            merged.rename(columns={"Date": "Last Eaten"}, inplace=True)

            # compute Days Ago
            merged["Last Eaten"] = pd.to_datetime(merged["Last Eaten"], errors="coerce")
            merged["Days Ago"] = (datetime.today() - merged["Last Eaten"]).dt.days
            merged["Last Eaten"] = merged["Last Eaten"].dt.strftime("%d-%m-%Y")

            # prepare table
            suggestions_df = merged[["Recipe", "Item Type", "Last Eaten", "Days Ago"]].copy()
            st.table(
                suggestions_df.style.set_properties(
                    subset=["Days Ago"], **{"text-align": "center", "width": "60px"}
                )
            )

            # recipe selection
            selected_recipe = st.radio("Select recipe to save for today", suggestions_df["Recipe"].tolist())

            if selected_recipe:
                if st.button("Save Today's Pick"):
                    save_today_pick(selected_recipe, history_df)
                    st.success(f"Today's pick **{selected_recipe}** saved!")

# -------------------------
# Master List
# -------------------------
elif page == "Master List":
    st.subheader("Master List")
    st.dataframe(master_df)

# -------------------------
# History
# -------------------------
elif page == "History":
    st.subheader("History")
    if history_df.empty:
        st.info("No history yet.")
    else:
        hist_df = history_df.copy()
        hist_df["Date"] = pd.to_datetime(hist_df["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
        st.dataframe(hist_df)
