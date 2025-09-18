import streamlit as st
import pandas as pd
from datetime import datetime
from data_manager import (
    load_master_list,
    load_history,
    save_today_pick,
    add_recipe_to_master,
    delete_today_pick,
)
from ui_widgets import display_table

# ---------- GitHub Setup ----------
try:
    from github import Github

    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["GITHUB_REPO"]   # ✅ matches secrets.toml
    BRANCH_NAME = st.secrets.get("GITHUB_BRANCH", "main")

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    use_github = True
except Exception:
    st.warning("⚠️ GitHub not configured or secrets missing. Using local CSV files.")
    repo = None
    BRANCH_NAME = "main"
    use_github = False

# ---------- CSS ----------
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1rem; /* tighten top margin */
    }
    .dataframe th {
        text-align: center !important;
    }
    .days-col {
        text-align: center !important;
        width: 60px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Load Data ----------
master_df = load_master_list(repo, BRANCH_NAME, use_github)
history_df = load_history(repo, BRANCH_NAME, use_github)

# ---------- Navigation ----------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# ---------- Pick Today’s Recipe ----------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")

    today = datetime.today().strftime("%d-%m-%Y")
    if not history_df.empty and history_df["Date"].iloc[-1] == today:
        st.success(f"✅ Today's pick is **{history_df['Recipe'].iloc[-1]}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")

    else:
        option = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"])

        if option == "By Item Type":
            item_types = master_df["Item Type"].dropna().unique().tolist()
            choice = st.selectbox("Select Item Type:", ["-- Choose --"] + item_types)

            if choice != "-- Choose --":
                filtered = master_df[master_df["Item Type"] == choice].copy()
                filtered = filtered.merge(
                    history_df.groupby("Recipe")["Date"].max().reset_index(),
                    on="Recipe",
                    how="left"
                )
                filtered.rename(columns={"Date": "Last Eaten"}, inplace=True)
                filtered["Last Eaten"] = pd.to_datetime(filtered["Last Eaten"], errors="coerce").dt.strftime("%d-%m-%Y")
                filtered["Days Ago"] = (
                    pd.to_datetime(datetime.today().strftime("%d-%m-%Y"), format="%d-%m-%Y")
                    - pd.to_datetime(filtered["Last Eaten"], format="%d-%m-%Y", errors="coerce")
                ).dt.days.fillna("-").astype(str)

                display_table(filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])

                pick = st.radio("Select recipe to save for today", filtered["Recipe"].tolist())
                if st.button("Save Today’s Pick"):
                    save_today_pick(pick, repo, BRANCH_NAME, use_github)

        elif option == "Today's Suggestions":
            # Suggestions: sort by oldest eaten
            suggestions = master_df.copy()
            suggestions = suggestions.merge(
                history_df.groupby("Recipe")["Date"].max().reset_index(),
                on="Recipe",
                how="left"
            )
            suggestions.rename(columns={"Date": "Last Eaten"}, inplace=True)
            suggestions["Last Eaten"] = pd.to_datetime(suggestions["Last Eaten"], errors="coerce").dt.strftime("%d-%m-%Y")
            suggestions["Days Ago"] = (
                pd.to_datetime(datetime.today().strftime("%d-%m-%Y"), format="%d-%m-%Y")
                - pd.to_datetime(suggestions["Last Eaten"], format="%d-%m-%Y", errors="coerce")
            ).dt.days.fillna("-").astype(str)

            suggestions = suggestions.sort_values(by="Days Ago", ascending=False)

            display_table(suggestions[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])

            pick = st.radio("Select recipe to save for today", suggestions["Recipe"].tolist())
            if st.button("Save Today’s Pick"):
                save_today_pick(pick, repo, BRANCH_NAME, use_github)

# ---------- Master List ----------
elif page == "Master List":
    st.header("Master Meal List")

    display_table(master_df[["Recipe", "Item Type"]])

    with st.expander("➕ Add a new recipe"):
        recipe = st.text_input("Recipe name")
        item_type = st.text_input("Item type")
        if st.button("Add Recipe"):
            if recipe and item_type:
                add_recipe_to_master(recipe, item_type, repo, BRANCH_NAME, use_github)
                st.success(f"✅ Added {recipe} to Master List")
            else:
                st.error("Please enter both Recipe name and Item type.")

# ---------- History ----------
elif page == "History":
    st.header("Meal History")

    if history_df.empty:
        st.info("No history yet.")
    else:
        display_table(history_df)

        if st.button("❌ Delete Today’s Pick"):
            delete_today_pick(repo, BRANCH_NAME, use_github)
