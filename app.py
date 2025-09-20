import streamlit as st
import pandas as pd
import random
import os
from datetime import datetime, timedelta
from github import Github
from data_manager import (
    load_master_list,
    load_history,
    save_today_pick,
    add_recipe_to_master,
    delete_today_pick,
    save_master_list,
    save_history,
    get_file_sha,
)

# ---------- GitHub Setup ----------
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["GITHUB_REPO"]
    BRANCH_NAME = st.secrets["GITHUB_BRANCH"]
except Exception:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
    REPO_NAME = os.environ.get("GITHUB_REPO")
    BRANCH_NAME = os.environ.get("GITHUB_BRANCH")

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)

MASTER_LIST_FILE = "master_list.csv"
HISTORY_FILE = "history.csv"

# ---------- Helpers ----------
def safe_rerun():
    """Force rerun without Streamlit recursion errors."""
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

def df_to_html_table(df: pd.DataFrame) -> str:
    """Render pandas DataFrame as styled HTML table for cleaner UI."""
    if df.empty:
        return "<p><em>No data available</em></p>"
    return df.to_html(index=False, escape=False)

def load_data():
    """Load master + history consistently from GitHub."""
    master = load_master_list(repo=repo, branch=BRANCH_NAME, use_github=True)
    history = load_history(repo=repo, branch=BRANCH_NAME, use_github=True)

    # Ensure schema consistency
    if "Item Type" not in history.columns:
        history["Item Type"] = None

    return master, history

def try_save_master_list(df, *args, **kwargs):
    """Wrapper to safely save master list and rerun."""
    try:
        save_master_list(df, repo=repo, branch=BRANCH_NAME)
        safe_rerun()
    except Exception as e:
        st.error(f"Failed to save master list: {e}")

def try_save_history(df, *args, **kwargs):
    """Wrapper to safely save history and rerun."""
    try:
        save_history(df, repo=repo, branch=BRANCH_NAME)
        safe_rerun()
    except Exception as e:
        st.error(f"Failed to save history: {e}")

# ---------- UI ----------
st.set_page_config(page_title="Meal Planner", layout="wide")
st.title("🍴 Meal Planner")

tab1, tab2, tab3 = st.tabs(["Pick Today’s Recipe", "Master List", "History"])

# ---------- Tab 1: Pick Today ----------
with tab1:
    st.header("Pick Today’s Recipe")
    master, history = load_data()

    # Ensure Date parsed
    if not history.empty and not pd.api.types.is_datetime64_any_dtype(history["Date"]):
        try:
            history["Date"] = pd.to_datetime(history["Date"], format="%d-%m-%Y")
        except Exception:
            history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
    if not history.empty:
        history["Date"] = history["Date"].dt.date

    today = datetime.today().date()
    today_entry = history.loc[history["Date"] == today]

    if not today_entry.empty:
        st.success(f"✅ Today's Pick: {today_entry.iloc[0]['Recipe']}")
        if st.button("❌ Remove Today’s Pick"):
            delete_today_pick(repo=repo, branch=BRANCH_NAME, use_github=True)
            safe_rerun()
    else:
        mode = st.radio("Choose mode:", ["By Item Type", "Suggestions"])

        if mode == "By Item Type":
            item_types = master["Item Type"].dropna().unique().tolist()
            item_type = st.selectbox("Select Item Type:", [""] + item_types)

            if item_type:
                options = master[master["Item Type"] == item_type]["Recipe"].tolist()
                choice = st.selectbox("Pick Recipe:", [""] + options)

                if choice and st.button("Save Today’s Pick"):
                    save_today_pick(choice, repo=repo, branch=BRANCH_NAME, use_github=True)
                    safe_rerun()

        else:  # Suggestions mode
            # Exclude recipes picked in last 30 days
            cutoff = today - timedelta(days=30)
            recent = history[history["Date"] >= cutoff]["Recipe"].tolist()
            candidates = master[~master["Recipe"].isin(recent)]

            if candidates.empty:
                st.warning("⚠️ No available suggestions (all used in last 30 days).")
            else:
                suggestions = random.sample(
                    candidates["Recipe"].tolist(),
                    min(5, len(candidates))
                )
                st.write("### Suggestions:")
                for recipe in suggestions:
                    if st.button(f"Pick {recipe}"):
                        save_today_pick(recipe, repo=repo, branch=BRANCH_NAME, use_github=True)
                        safe_rerun()

# ---------- Tab 2: Master List ----------
with tab2:
    st.header("📖 Master List")
    master, _ = load_data()
    master_sha = get_file_sha(MASTER_LIST_FILE)

    st.subheader("Add New Recipe")
    new_recipe = st.text_input("Recipe Name")
    new_type = st.selectbox("Item Type", ["", "Breakfast", "Lunch", "Dinner", "Snack", "Other"])

    if st.button("Add Recipe"):
        if not new_recipe or not new_type:
            st.warning("⚠️ Please fill all fields.")
        else:
            add_recipe_to_master(new_recipe, new_type, repo=repo, branch=BRANCH_NAME, use_github=True)
            safe_rerun()

    st.subheader("Edit/Delete Recipes")
    edited = st.data_editor(master, num_rows="dynamic", key="master_editor")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Changes"):
            try_save_master_list(edited, master_sha)
    with col2:
        if st.button("🔄 Reset Changes"):
            safe_rerun()

# ---------- Tab 3: History ----------
with tab3:
    st.header("📜 History")
    _, history = load_data()
    history_sha = get_file_sha(HISTORY_FILE)

    if not history.empty:
        history["Date"] = pd.to_datetime(history["Date"], format="%d-%m-%Y", errors="coerce")
        history["__sort_date__"] = history["Date"]
        history["Days Ago"] = (datetime.today().date() - history["Date"].dt.date).dt.days

        # Fill missing item type from master
        master, _ = load_data()
        type_map = dict(zip(master["Recipe"], master["Item Type"]))
        history["Item Type"] = history.apply(
            lambda r: r["Item Type"] if pd.notna(r["Item Type"]) else type_map.get(r["Recipe"], None),
            axis=1
        )

        st.subheader("Filter")
        option = st.radio("Show:", ["All", "Last Week", "Last Month"], horizontal=True)

        if option == "Last Week":
            cutoff = datetime.today().date() - timedelta(days=7)
            filtered = history[history["Date"].dt.date >= cutoff]
        elif option == "Last Month":
            cutoff = datetime.today().date() - timedelta(days=30)
            filtered = history[history["Date"].dt.date >= cutoff]
        else:
            filtered = history

        filtered = filtered.sort_values("__sort_date__", ascending=False)
        st.dataframe(filtered[["Date", "Recipe", "Item Type", "Days Ago"]], use_container_width=True)

        if st.button("❌ Remove Today’s Entry"):
            delete_today_pick(repo=repo, branch=BRANCH_NAME, use_github=True)
            safe_rerun()
    else:
        st.info("No history yet.")
