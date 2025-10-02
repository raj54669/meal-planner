# app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
from github import Github
from ui_widgets import display_table, recipe_card, apply_global_styles
import data_manager as dm

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO", "raj54669/meal-planner")
GITHUB_BRANCH = "main"

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
        add_recipe_to_master,
        edit_recipe_in_master,
        delete_recipe_from_master,
        delete_today_pick,
        get_file_sha
    )
except Exception:
    load_master_list = None
    load_history = None
    save_today_pick = None
    add_recipe_to_master = None
    edit_recipe_in_master = None
    delete_recipe_from_master = None
    delete_today_pick = None
    get_file_sha = None

try:
    from recommendations import recommend
except Exception:
    recommend = None

# -----------------------
# Config / Secrets
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

apply_global_styles()

# Page config
st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")

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

        # overwrite on GitHub
        repo_df = pd.DataFrame(df)
        repo_df = repo_df[["Recipe", "Item Type"]]  # enforce schema
        add_recipe_to_master("", "", repo=GITHUB_REPO, branch=GITHUB_BRANCH)  # no-op add ensures file exists
        file = GITHUB_REPO.get_contents(MASTER_LIST_FILE, ref=GITHUB_BRANCH)
        GITHUB_REPO.update_file(file.path, "Update master list", repo_df.to_csv(index=False), file.sha, branch=GITHUB_BRANCH)

        st.success("✅ Master list updated on GitHub!")
        st.cache_data.clear()
        safe_rerun()
        return True

    except Exception as e:
        st.error(f"❌ GitHub save failed: {type(e).__name__} - {e}")
        return False

def try_save_history(df: pd.DataFrame):
    try:
        if not GITHUB_REPO or not GITHUB_TOKEN:
            st.error("GitHub repo or token not configured.")
            return df   # return unchanged DataFrame

        repo_df = pd.DataFrame(df)
        repo_df = repo_df[["Date", "Recipe", "Item Type"]]  # enforce schema
        delete_today_pick(today_str="1900-01-01", repo=GITHUB_REPO, branch=GITHUB_BRANCH)  # no-op ensures file exists
        file = GITHUB_REPO.get_contents(HISTORY_FILE, ref=GITHUB_BRANCH)
        GITHUB_REPO.update_file(file.path, "Update history", repo_df.to_csv(index=False), file.sha, branch=GITHUB_BRANCH)

        st.success("✅ History updated on GitHub!")
        st.cache_data.clear()

        # 🔑 Reload and return the new DataFrame
        if callable(load_history):
            updated = load_history(GITHUB_REPO, branch=GITHUB_BRANCH)
            return updated

        return df
    except Exception as e:
        st.error(f"❌ GitHub save failed: {type(e).__name__} - {e}")
        return df


# -----------------------
# Load data
# -----------------------
#master_df, history_df, master_sha, history_sha = load_data()

# -----------------------
# Load data into session state
# -----------------------
if "master_df" not in st.session_state or "history_df" not in st.session_state:
    master_df, history_df, _, _ = load_data()
    st.session_state.master_df = master_df
    st.session_state.history_df = history_df

# -----------------------
# Title
# -----------------------
st.title("🍴 NextBite – Meal Planner App")

# Sidebar nav
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# Always sync session state copies
master_df = st.session_state.master_df
history_df = st.session_state.history_df

# Utility: today's pick
today = date.today()
today_pick = None
history_df = st.session_state.history_df
if not history_df.empty and "Date" in history_df.columns:
    hx = history_df.dropna(subset=["Date"]).copy()
    if not hx.empty:
        hx["Date"] = pd.to_datetime(hx["Date"], errors="coerce")
        hx["DateOnly"] = hx["Date"].dt.date
        sel = hx[hx["DateOnly"] == today]
        if not sel.empty:
            today_pick = sel.sort_values("Date", ascending=False).iloc[0]["Recipe"]
# -----------------------
# PICK TODAY
# -----------------------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")
    if today_pick:
        st.success(f"✅ Today's pick is **{today_pick}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")

    mode = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"], horizontal=True)

    if mode == "By Item Type":
        master_df = st.session_state.master_df
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

                # ✅ use shared table UI
                display_table(filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])

                choices = filtered["Recipe"].astype(str).tolist()
                if choices:
                    recipe_choice = st.radio("Select recipe to save for today", choices, key="bytype_choice")
                    button_label = "Update Today's Pick (By Type)" if today_pick else "Save Today's Pick (By Type)" if st.button(button_label):
                        try:
                            updated = save_today_pick(recipe_choice, selected_type, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
                            st.session_state.history_df = updated
                            st.cache_data.clear()
                            st.success(f"✅ Saved **{recipe_choice}** and updated live!")
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

            # ✅ use shared table UI
            display_table(rec_df[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])

            choices = rec_df["Recipe"].astype(str).tolist()
            if choices:
                recipe_choice = st.radio("Select recipe to save for today", choices, key="suggest_choice")
                button_label = "Update Today's Pick (Suggestion)" if today_pick else "Save Today's Pick (Suggestion)" if st.button(button_label):
                
                    chosen_row = rec_df[rec_df["Recipe"] == recipe_choice].iloc[0].to_dict()
                    item_type = chosen_row.get("Item Type", "")
                
                    try:
                        updated = save_today_pick(recipe_choice, item_type, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
                        st.session_state.history_df = updated
                        st.cache_data.clear()
                        st.success(f"✅ Saved **{recipe_choice}** and updated live!")
                        safe_rerun()
                    except Exception as e:
                        st.error(f"Failed to save history: {e}")

                    
# -----------------------
# MASTER LIST
# -----------------------
elif page == "Master List":
    st.header("Master List")
    st.write("Add / Edit / Delete recipes. Edit opens inline editor for the selected row.")

    if callable(load_master_list) and GITHUB_REPO:
        master_df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)
        st.session_state.master_df = master_df
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
                # prevent duplicates (case-insensitive)
                exists = master_df["Recipe"].str.lower().str.strip().eq(new_name.strip().lower()).any()
                if exists:
                    st.error(f"⚠️ Recipe **{new_name}** already exists in Master List.")
                else:
                    new_master = pd.concat(
                        [master_df, pd.DataFrame([{"Recipe": new_name.strip(), "Item Type": new_type.strip()}])],
                        ignore_index=True
                    )
                    st.session_state.master_df = try_save_master_list(new_master) or master_df
                    st.success(f"✅ Added **{new_name}** and updated live!")


    st.markdown("")

    # -----------------------
    # Accordion style Master List (mobile friendly)
    # -----------------------
    if master_df.empty:
        st.info("No recipes found. Add some above.")
    else:
        # Sort first by Item Type, then by Recipe
        master_df = master_df.sort_values(by=["Item Type", "Recipe"], ascending=[True, True]).reset_index(drop=True)
    
        for i, row in master_df.iterrows():
            with st.expander(f"{row['Recipe']} – {row['Item Type']}"):
                # Edit + Delete side by side
                col1, col2 = st.columns(2, gap="small")
                with col1:
                    if st.button("✏️ Edit", key=f"edit_btn_{i}"):
                        st.session_state["edit_row"] = i
                        st.session_state["delete_row"] = None
                        safe_rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"del_btn_{i}"):
                        st.session_state["delete_row"] = i
                        st.session_state["edit_row"] = None
                        safe_rerun()
    
                # Edit mode
                if st.session_state.get("edit_row") == i:
                    edit_name = st.text_input("Edit Recipe Name", value=row["Recipe"], key=f"edit_name_{i}")
                    edit_type = st.text_input("Edit Item Type", value=row["Item Type"], key=f"edit_type_{i}")
    
                    col1, col2, col3 = st.columns(3, gap="small")
                    with col1:
                        if st.button("💾 Save Edit", key=f"save_edit_{i}"):
                            master_df.at[i, "Recipe"] = edit_name
                            master_df.at[i, "Item Type"] = edit_type
                            st.session_state.master_df = try_save_master_list(master_df) or master_df
                            st.success("✏️ Recipe updated live!")
                            st.session_state["edit_row"] = None
                            safe_rerun()
                    with col2:
                        if st.button("❌ Cancel", key=f"cancel_edit_{i}"):
                            st.session_state["edit_row"] = None
                            safe_rerun()
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_btn_edit_{i}"):
                            st.session_state["delete_row"] = i
                            st.session_state["edit_row"] = None
                            safe_rerun()
    
                # Confirm delete mode
                if st.session_state.get("delete_row") == i:
                    st.warning(f"Confirm delete '{row['Recipe']}'?")
                    if st.button("🗑️ Confirm Delete", key=f"confirm_del_{i}"):
                        new_master = master_df.drop(i).reset_index(drop=True)
                        st.session_state.master_df = try_save_master_list(new_master) or master_df
                        st.success("🗑️ Recipe deleted live!")
                        st.session_state["delete_row"] = None
                        safe_rerun()
                    if st.button("❌ Cancel Delete", key=f"cancel_del_{i}"):
                        st.session_state["delete_row"] = None
                        safe_rerun()


# -----------------------
# HISTORY
# -----------------------
elif page == "History":
    st.header("History")
    st.write("Use the static filter buttons below to view historical picks.")

    master_df = st.session_state.master_df
    history_df = st.session_state.history_df

    col1, col2 = st.columns(2, gap="small")
    with col1:
        btn_curr_month = st.button("Current Month", key="history_curr_month")
    with col2:
        btn_prev_month = st.button("Previous Month", key="history_prev_month")


    # 👇 Start filtering outside of `with col_mid:`
    filtered = history_df.copy()

    if not filtered.empty and "Date" in filtered.columns:
        master_map = dict(zip(master_df["Recipe"].astype(str), master_df["Item Type"].astype(str)))
        filtered["Item Type"] = filtered["Item Type"].fillna(filtered["Recipe"].map(master_map))

        # Ensure proper datetime conversion BEFORE filtering
        filtered["Date"] = pd.to_datetime(filtered["Date"], errors="coerce")

        today_local = date.today()

        # Decide which month filter to apply
        if btn_prev_month:
            # Previous month
            first_of_this = today_local.replace(day=1)
            last_of_prev = first_of_this - timedelta(days=1)
            first_of_prev = last_of_prev.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first_of_prev) & (filtered["Date"].dt.date <= last_of_prev)]
        else:
            # Current month
            first = today_local.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first) & (filtered["Date"].dt.date <= today_local)]


        filtered = filtered.copy()
        
        filtered["Days Ago"] = filtered["Date"].apply(
            lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA
        )
        filtered["Date"] = filtered["Date"].dt.strftime("%d-%m-%Y")

        try:
            filtered["__sort_date__"] = pd.to_datetime(filtered["Date"], format="%d-%m-%Y", errors="coerce")
            filtered = filtered.sort_values("__sort_date__", ascending=True).drop(columns="__sort_date__")
        except Exception:
            filtered = filtered.sort_index(ascending=True)

        # Show the history table
        if filtered.empty:
            st.info("📭 No records found for this period.")
        else:
            display_table(filtered[["Date", "Recipe", "Item Type", "Days Ago"]])


        if st.button("🗑️ Remove Today's Entry (if exists)"):
            try:
                updated = delete_today_pick(repo=GITHUB_REPO, branch=GITHUB_BRANCH)
                st.session_state.history_df = updated
                st.cache_data.clear()
                st.success("🗑️ Removed today’s entry live!")
                safe_rerun()
            except Exception as e:
                st.error(f"Failed to remove today's entry: {e}")

    else:
        st.info("History is empty.")
