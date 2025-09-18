import streamlit as st
import pandas as pd
from datetime import datetime
from data_manager import load_master_list, load_history, save_today_pick, save_master_list
from recommendations import get_suggestions
from ui_widgets import render_table

# ---------- GitHub Setup ----------
try:
    from github import Github

    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["GITHUB_REPO"]
    BRANCH_NAME = st.secrets.get("GITHUB_BRANCH", "main")

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    use_github = True
except Exception as e:
    st.warning("⚠️ GitHub not configured or secrets missing. Using local CSV files.")
    repo = None
    BRANCH_NAME = "main"
    use_github = False

MASTER_CSV = st.secrets.get("MASTER_CSV", "master_list.csv")
HISTORY_CSV = st.secrets.get("HISTORY_CSV", "history.csv")

# ---------- App Title ----------
st.markdown("<h1 style='margin-top: -30px;'>🍴 NextBite – Meal Planner App</h1>", unsafe_allow_html=True)

# ---------- Sidebar Navigation ----------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# ---------- Pick Today’s Recipe ----------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")

    history = load_history(repo, HISTORY_CSV)
    master = load_master_list(repo, MASTER_CSV)

    today = datetime.today().strftime("%Y-%m-%d")
    if not history.empty and today in history["Date"].values:
        today_pick = history.loc[history["Date"] == today, "Recipe"].values[0]
        st.success(f"✅ Today's pick is **{today_pick}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")
    else:
        option = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"])

        if option == "By Item Type":
            item_types = master["Item Type"].dropna().unique().tolist()
            item_type = st.selectbox("Select Item Type:", ["-- Choose --"] + item_types)

            if item_type != "-- Choose --":
                filtered = master[master["Item Type"] == item_type].copy()
                filtered = filtered.sort_values("Last Eaten", na_position="first")
                render_table(filtered)

                recipe = st.selectbox("Select Recipe:", ["-- Choose --"] + filtered["Recipe"].tolist())
                if recipe != "-- Choose --":
                    if st.button("Save Today's Pick"):
                        save_today_pick(recipe, repo, HISTORY_CSV)
                        st.success(f"✅ Saved today's pick: **{recipe}**")

        else:  # Today's Suggestions
            suggestions = get_suggestions(master, history)
            render_table(suggestions)

            recipe = st.selectbox("Select Recipe:", ["-- Choose --"] + suggestions["Recipe"].tolist())
            if recipe != "-- Choose --":
                if st.button("Save Today's Pick"):
                    save_today_pick(recipe, repo, HISTORY_CSV)
                    st.success(f"✅ Saved today's pick: **{recipe}**")

# ---------- Master List ----------
elif page == "Master List":
    st.header("Master List")
    master = load_master_list(repo, MASTER_CSV)
    render_table(master)

    with st.expander("➕ Add New Recipe"):
        new_recipe = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        if st.button("Add Recipe"):
            if new_recipe and new_type:
                new_row = {"Recipe": new_recipe, "Item Type": new_type, "Last Eaten": ""}
                master = pd.concat([master, pd.DataFrame([new_row])], ignore_index=True)
                save_master_list(master, repo, MASTER_CSV)
                st.success(f"✅ Added {new_recipe} to Master List")
            else:
                st.error("Please enter both Recipe Name and Item Type.")

# ---------- History ----------
elif page == "History":
    st.header("History")
    history = load_history(repo, HISTORY_CSV)
    render_table(history)

    if not history.empty:
        if st.button("Delete Last Entry"):
            history = history.iloc[:-1]
            save_master_list(history, repo, HISTORY_CSV)  # reusing save_master_list for history
            st.success("✅ Deleted last entry")
