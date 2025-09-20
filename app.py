# app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import os
from github import Github
from ui_widgets import display_table

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO", "raj54669/meal-planner")
GITHUB_BRANCH = "main"

gh = None
GITHUB_REPO = None
if GITHUB_TOKEN:
    try:
        gh = Github(GITHUB_TOKEN)
        GITHUB_REPO = gh.get_repo(GITHUB_REPO_NAME)
    except Exception as e:
        st.warning(f"GitHub repo init failed: {e}")

# ---------- File constants ----------
MASTER_LIST_FILE = "master_list.csv"
HISTORY_FILE = "history.csv"

# Try to import repository helpers
try:
    from data_manager import (
        load_master_list,
        load_history,
        save_today_pick,
        save_master_list,
        save_history,
        delete_today_pick,
        get_file_sha
    )
except Exception:
    load_master_list = None
    load_history = None
    save_today_pick = None
    save_master_list = None
    save_history = None
    delete_today_pick = None
    get_file_sha = None

try:
    from recommendations import recommend
except Exception:
    recommend = None

# -----------------------
# Config / Secrets (defensive)
# -----------------------
try:
    GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", GITHUB_TOKEN)
except Exception:
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

try:
    GITHUB_REPO_NAME = st.secrets.get("GITHUB_REPO", GITHUB_REPO_NAME)
    GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH", "main")
    MASTER_CSV = st.secrets.get("MASTER_CSV", MASTER_LIST_FILE)
    HISTORY_CSV = st.secrets.get("HISTORY_CSV", HISTORY_FILE)
except Exception:
    GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO", GITHUB_REPO_NAME)
    GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
    MASTER_CSV = os.environ.get("MASTER_CSV", MASTER_LIST_FILE)
    HISTORY_CSV = os.environ.get("HISTORY_CSV", HISTORY_FILE)

# Page config
st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")

st.markdown(
    """
    <style>
    .app-container > .main > .block-container { padding-top: 0rem; }
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Helpers
# -----------------------
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        try:
            st.rerun()
        except Exception:
            return

def load_data():
    master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
    history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    master_sha = None
    history_sha = None

    if callable(load_master_list) and callable(load_history) and GITHUB_REPO and GITHUB_TOKEN:
        try:
            master_df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)
        except Exception:
            master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
        try:
            history_df = load_history(GITHUB_REPO, branch=GITHUB_BRANCH)
        except Exception:
            history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

    master_df.columns = [c.strip() for c in master_df.columns]
    history_df.columns = [c.strip() for c in history_df.columns]

    for c in ["Recipe", "Item Type"]:
        if c not in master_df.columns:
            master_df[c] = ""
    for c in ["Date", "Recipe", "Item Type"]:
        if c not in history_df.columns:
            history_df[c] = pd.NA

    if "Date" in history_df.columns:
        history_df["Date"] = pd.to_datetime(history_df["Date"], errors="coerce")

    return master_df, history_df, master_sha, history_sha


def try_save_master_list(df: pd.DataFrame):
    try:
        if not GITHUB_REPO or not GITHUB_TOKEN:
            st.error("GitHub repo or token not configured.")
            return False

        sha = None
        if callable(get_file_sha):
            sha = get_file_sha(MASTER_LIST_FILE, repo=GITHUB_REPO, branch=GITHUB_BRANCH)

        save_master_list(df, repo=GITHUB_REPO, branch=GITHUB_BRANCH, sha=sha)

        st.success("✅ Master list updated on GitHub!")

        st.cache_data.clear()
        if callable(load_master_list):
            df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)

        safe_rerun()
        return True
    except Exception as e:
        st.error(f"❌ GitHub save failed: {type(e).__name__} - {e}")
        return False


def try_save_history(df: pd.DataFrame):
    try:
        if not GITHUB_REPO or not GITHUB_TOKEN:
            st.error("GitHub repo or token not configured.")
            return False

        sha = None
        if callable(get_file_sha):
            sha = get_file_sha(HISTORY_FILE, repo=GITHUB_REPO, branch=GITHUB_BRANCH)

        save_history(df, repo=GITHUB_REPO, branch=GITHUB_BRANCH, sha=sha)

        st.success("✅ History updated on GitHub!")

        st.cache_data.clear()
        if callable(load_history):
            df = load_history(GITHUB_REPO, branch=GITHUB_BRANCH)

        safe_rerun()
        return True
    except Exception as e:
        st.error(f"❌ GitHub save failed: {type(e).__name__} - {e}")
        return False


# -----------------------
# Load data
# -----------------------
master_df, history_df, master_sha, history_sha = load_data()

# -----------------------
# Title
# -----------------------
st.title("🍴 NextBite – Meal Planner App")

# Replace sidebar with tabs
tab1, tab2, tab3 = st.tabs(["Pick Today’s Recipe", "Master List", "History"])

# Utility: today's pick
today = date.today()
today_pick = None
if not history_df.empty and "Date" in history_df.columns:
    hx = history_df.dropna(subset=["Date"]).copy()
    if not hx.empty:
        hx["DateOnly"] = pd.to_datetime(hx["Date"]).dt.date
        sel = hx[hx["DateOnly"] == today]
        if not sel.empty:
            today_pick = sel.sort_values("Date", ascending=False).iloc[0]["Recipe"]

# -----------------------
# PICK TODAY
# -----------------------
with tab1:
    st.header("Pick Today’s Recipe")
    if today_pick:
        st.success(f"✅ Today's pick is **{today_pick}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")

    mode = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"], horizontal=True)

    if mode == "By Item Type":
        types = master_df["Item Type"].dropna().astype(str).unique().tolist()
        types = [t for t in types if str(t).strip() != ""]
        types = sorted(types)
        if not types:
            st.warning("Master list is empty. Please add recipes in Master List.")
        else:
            selected_type = st.selectbox("Select Item Type:", ["-- Choose --"] + types, index=0)
            if selected_type and selected_type != "-- Choose --":
                filtered = master_df[master_df["Item Type"] == selected_type].copy()

                last_dates = {}
                if not history_df.empty and "Date" in history_df.columns:
                    tmp = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
                    last_dates = tmp.groupby("Recipe")["Date"].first().to_dict()

                filtered["Last Eaten"] = filtered["Recipe"].map(lambda r: last_dates.get(r) if r in last_dates else pd.NaT)
                filtered["Days Ago"] = filtered["Last Eaten"].apply(lambda d: (today - pd.to_datetime(d).date()).days if pd.notna(d) else pd.NA)
                filtered = filtered.sort_values(by="Days Ago", ascending=False)

                display_table(filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])

                choices = filtered["Recipe"].astype(str).tolist()
                if choices:
                    recipe_choice = st.radio("Select recipe to save for today", choices, key="bytype_choice")
                    if st.button("Save Today's Pick (By Type)"):
                        try:
                            history_df = save_today_pick(recipe_choice, selected_type, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
                            st.cache_data.clear()
                            st.success(f"Saved **{recipe_choice}** to history (GitHub updated).")
                            safe_rerun()
                        except Exception as e:
                            st.error(f"Failed to save history: {e}")

    else:
        if recommend:
            rec_df = recommend(master_df, history_df, min_count=5, max_count=7)
        else:
            rec_df = master_df.copy().head(10)

        if rec_df is None or rec_df.empty:
            st.warning("No suggestions available.")
        else:
            if "Last Eaten" in rec_df.columns:
                rec_df["Last Eaten"] = pd.to_datetime(rec_df["Last Eaten"], errors="coerce")
            if "Days Ago" in rec_df.columns:
                rec_df["Days Ago"] = rec_df["Days Ago"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)

            display_table(rec_df[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])

            choices = rec_df["Recipe"].astype(str).tolist()
            if choices:
                recipe_choice = st.radio("Select recipe to save for today", choices, key="suggest_choice")
                if st.button("Save Today's Pick (Suggestion)"):
                    chosen_row = rec_df[rec_df["Recipe"] == recipe_choice].iloc[0].to_dict()
                    item_type = chosen_row.get("Item Type", "")
                    new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": recipe_choice, "Item Type": item_type}
                    new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                    try:
                        history_df = save_history(new_history, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
                        st.cache_data.clear()
                        st.success(f"Saved **{recipe_choice}** to history (GitHub updated).")
                        safe_rerun()
                    except Exception as e:
                        st.error(f"Failed to save history: {e}")

# -----------------------
# MASTER LIST
# -----------------------
with tab2:
    st.header("Master List")
    st.write("Add / Edit / Delete recipes. Edit opens inline editor for the selected row.")

    if callable(load_master_list) and GITHUB_REPO:
        master_df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)
        try:
            master_sha = get_file_sha(MASTER_LIST_FILE, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
        except Exception:
            master_sha = None
    else:
        st.error("⚠️ load_master_list not available. Check data_manager.py import.")
        master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
        master_sha = None

    with st.form("add_recipe", clear_on_submit=True):
        new_name = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        submitted = st.form_submit_button("Add Recipe")
        if submitted:
            if not new_name.strip():
                st.warning("Provide a recipe name.")
            else:
                new_master = pd.concat(
                    [master_df, pd.DataFrame([{"Recipe": new_name.strip(), "Item Type": new_type.strip()}])],
                    ignore_index=True
                )
                ok = try_save_master_list(new_master)
                if ok:
                    st.cache_data.clear()
                    master_df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)
                    st.success(f"Added **{new_name}** to master list.")
                    safe_rerun()
                else:
                    st.error("Failed to save master list. Check logs.")

    st.markdown("")

    if master_df.empty:
        st.info("No recipes found. Add some above.")
    else:
        if "edit_row" not in st.session_state:
            st.session_state["edit_row"] = None
        if "delete_row" not in st.session_state:
            st.session_state["delete_row"] = None

        cols = st.columns([4, 2, 1, 1])
        cols[0].markdown("**Recipe**")
        cols[1].markdown("**Item Type**")
        cols[2].markdown("**Edit**")
        cols[3].markdown("**Delete**")

        for i, row in master_df.reset_index(drop=True).iterrows():
            cols = st.columns([4, 2, 1, 1])
            cols[0].write(row["Recipe"])
            cols[1].write(row["Item Type"])

            if cols[2].button("✏️", key=f"edit_btn_{i}"):
                st.session_state["edit_row"] = i
                st.session_state["delete_row"] = None
                safe_rerun()

            if cols[3].button("🗑️", key=f"del_btn_{i}"):
                st.session_state["delete_row"] = i
                st.session_state["edit_row"] = None
                safe_rerun()

            if st.session_state.get("edit_row") == i:
                st.markdown("---")
                edit_name = st.text_input(f"Edit name ({i}):", value=row["Recipe"], key=f"edit_name_{i}")
                edit_type = st.text_input(f"Edit type ({i}):", value=row["Item Type"], key=f"edit_type_{i}")
                if st.button("Save Edit", key=f"save_edit_{i}"):
                    master_df.at[i, "Recipe"] = edit_name
                    master_df.at[i, "Item Type"] = edit_type
                    ok = try_save_master_list(master_df)
                    if ok:
                        st.cache_data.clear()
                        master_df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)
                        st.success("Updated master list.")
                        st.session_state["edit_row"] = None
                        safe_rerun()
                    else:
                        st.error("Failed to save master list. See logs.")
                if st.button("Cancel", key=f"cancel_edit_{i}"):
                    st.session_state["edit_row"] = None
                    safe_rerun()

            if st.session_state.get("delete_row") == i:
                st.warning(f"Confirm delete '{row['Recipe']}'?")
                if st.button("Confirm Delete", key=f"confirm_del_{i}"):
                    new_master = master_df.drop(i).reset_index(drop=True)
                    ok = try_save_master_list(new_master)
                    if ok:
                        st.cache_data.clear()
                        master_df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)
                        st.success("Deleted entry.")
                        st.session_state["delete_row"] = None
                        safe_rerun()
                    else:
                        st.error("Failed to delete entry. See logs.")
                if st.button("Cancel Delete", key=f"cancel_del_{i}"):
                    st.session_state["delete_row"] = None
                    safe_rerun()

# -----------------------
# HISTORY
# -----------------------
with tab3:
    st.header("History")
    st.write("Use the static filter buttons below to view historical picks.")

    st.markdown(
        "<style>div.stButton > button { white-space: nowrap; }</style>",
        unsafe_allow_html=True,
    )

    if callable(load_history) and GITHUB_REPO:
        try:
            history_df = load_history(GITHUB_REPO, branch=GITHUB_BRANCH)
            history_sha = get_file_sha(HISTORY_FILE, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
        except Exception:
            history_df = pd.DataFrame()
            history_sha = None

    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        b1, b2 = st.columns([1, 1])
        btn_curr_month = b1.button("Current Month", key="history_curr_month")
        btn_prev_month = b2.button("Previous Month", key="history_prev_month")

    filtered = history_df.copy()

    if not filtered.empty and "Date" in filtered.columns:
        filtered["Date"] = pd.to_datetime(filtered["Date"], errors="coerce")

        master_map = dict(zip(master_df["Recipe"].astype(str), master_df["Item Type"].astype(str)))
        filtered["Item Type"] = filtered["Item Type"].fillna(filtered["Recipe"].map(master_map))

        today_local = date.today()
        if btn_prev_month:
            first_of_this = today_local.replace(day=1)
            last_of_prev = first_of_this - timedelta(days=1)
            first_of_prev = last_of_prev.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first_of_prev) & (filtered["Date"].dt.date <= last_of_prev)]
        else:
            first = today_local.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first) & (filtered["Date"].dt.date <= today_local)]

        filtered = filtered.copy()
        filtered["Days Ago"] = filtered["Date"].apply(
            lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA
        )
        filtered["Date"] = pd.to_datetime(filtered["Date"], errors="coerce").dt.strftime("%d-%m-%Y")

        try:
            filtered["__sort_date__"] = pd.to_datetime(filtered["Date"], format="%d-%m-%Y", errors="coerce")
            filtered = filtered.sort_values("__sort_date__", ascending=True).drop(columns="__sort_date__")
        except Exception:
            filtered = filtered.sort_index(ascending=True)

        display_table(filtered[["Date", "Recipe", "Item Type", "Days Ago"]])

        if st.button("Remove Today's Entry (if exists)"):
            try:
                today_str = date.today().strftime("%Y-%m-%d")
                history_df = delete_today_pick(today_str, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
                st.cache_data.clear()
                st.success("Removed today's entry from GitHub.")
                safe_rerun()
            except Exception as e:
                st.error(f"Unable to remove today's entry: {e}")
    else:
        st.info("History is empty.")
