# app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
import os
from github import Github

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
    MASTER_LIST_FILE = st.secrets.get("MASTER_CSV", MASTER_LIST_FILE)
    HISTORY_FILE = st.secrets.get("HISTORY_CSV", HISTORY_FILE)
except Exception:
    GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO", GITHUB_REPO_NAME)
    GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
    MASTER_LIST_FILE = os.environ.get("MASTER_CSV", MASTER_LIST_FILE)
    HISTORY_FILE = os.environ.get("HISTORY_CSV", HISTORY_FILE)

# Page config
st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")

# CSS (unchanged)
st.markdown(
    """
    <style>
    .app-container > .main > .block-container { padding-top: 1rem !important; }
    .nb-table { border-collapse: collapse; width: 100%; font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
    .nb-table th, .nb-table td { padding: 10px 12px; border: 1px solid #eee; }
    .nb-table thead th { background: #fafafa; text-align: left; font-weight: 600; }
    .nb-table td.center { text-align: center; }
    .nb-table td.right { text-align: right; }
    .nb-table td.daysago { text-align: center; width: 60px; white-space: nowrap; }
    .nb-table-wrap { width:100%; overflow-x:auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Helpers
# -----------------------
def safe_rerun():
    try:
        st.rerun()
    except Exception:
        try:
            st.experimental_rerun()
        except Exception:
            return

def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    df = df.copy()
    if last_col in df.columns:
        df[last_col] = pd.to_datetime(df[last_col], errors="coerce").dt.strftime("%d-%m-%Y").fillna("")
    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)
    cols = list(df.columns)
    thead_cells = "".join(f"<th>{c}</th>" for c in cols)
    tbody_rows = ""
    for _, r in df.iterrows():
        row_cells = ""
        for c in cols:
            v = r[c] if pd.notna(r[c]) else ""
            if c == days_col:
                row_cells += f"<td class='daysago'>{v}</td>"
            else:
                row_cells += f"<td>{v}</td>"
        tbody_rows += f"<tr>{row_cells}</tr>"
    return f"<div class='nb-table-wrap'><table class='nb-table'><thead><tr>{thead_cells}</tr></thead><tbody>{tbody_rows}</tbody></table></div>"

def load_data():
    master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
    history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    master_sha = None
    history_sha = None

    if load_master_list and load_history and GITHUB_REPO and GITHUB_TOKEN:
        try:
            m = load_master_list(GITHUB_REPO, GITHUB_BRANCH)
            master_df = m
        except Exception:
            master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
        try:
            h = load_history(GITHUB_REPO, GITHUB_BRANCH)
            history_df = h
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
        history_df["Date"] = history_df["Date"].fillna(datetime.today().strftime("%d-%m-%Y"))

    return master_df, history_df, master_sha, history_sha

def try_save_master_list(df: pd.DataFrame, sha=None):
    try:
        if not GITHUB_TOKEN:
            st.error("GitHub not configured.")
            return False
        repo = gh.get_repo(GITHUB_REPO_NAME)
        save_master_list(df, repo=repo, branch=GITHUB_BRANCH)   # ✅ FIXED: no use_github
        st.success("✅ Master list updated successfully!")
        st.rerun()
        return True
    except Exception as e:
        st.error(f"❌ GitHub save failed: {type(e).__name__} - {e}")
        return False

def try_save_history(df: pd.DataFrame, sha=None):
    try:
        if not GITHUB_TOKEN:
            st.error("GitHub not configured.")
            return False
        repo = gh.get_repo(GITHUB_REPO_NAME)
        save_history(df, repo=repo, branch=GITHUB_BRANCH)   # ✅ FIXED: no use_github
        st.success("✅ History updated successfully!")
        st.rerun()
        return True
    except Exception as e:
        st.error(f"❌ GitHub save failed: {type(e).__name__} - {e}")
        return False

# -----------------------
# Load data
# -----------------------
master_df, history_df, master_sha, history_sha = load_data()

# -----------------------
# Top-level Title
# -----------------------
st.title("🍴 NextBite – Meal Planner App")

# -----------------------
# Sidebar
# -----------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# -----------------------
# Utility: today's pick
# -----------------------
today = date.today()
today_pick = None
if not history_df.empty and "Date" in history_df.columns:
    hx = history_df.dropna(subset=["Date"]).copy()
    hx["DateOnly"] = pd.to_datetime(hx["Date"]).dt.date
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
        types = sorted([t for t in master_df["Item Type"].dropna().astype(str).unique() if t.strip()])
        if not types:
            st.warning("Master list is empty.")
        else:
            selected_type = st.selectbox("Select Item Type:", ["-- Choose --"] + types, index=0)
            if selected_type and selected_type != "-- Choose --":
                filtered = master_df[master_df["Item Type"] == selected_type].copy()
                last_dates = {}
                if not history_df.empty:
                    tmp = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
                    last_dates = tmp.groupby("Recipe")["Date"].first().to_dict()
                filtered["Last Eaten"] = filtered["Recipe"].map(last_dates)
                filtered["Days Ago"] = filtered["Last Eaten"].apply(
                    lambda d: (today - pd.to_datetime(d).date()).days if pd.notna(d) else pd.NA
                )
                st.markdown(df_to_html_table(filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]]), unsafe_allow_html=True)
                choices = filtered["Recipe"].astype(str).tolist()
                if choices:
                    recipe_choice = st.radio("Select recipe to save for today", choices, key="bytype_choice")
                    if st.button("Save Today's Pick (By Type)"):
                        new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": recipe_choice, "Item Type": selected_type}
                        new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                        try_save_history(new_history, history_sha)

    else:
        rec_df = recommend(master_df, history_df, min_count=5, max_count=7) if recommend else master_df.copy().head(10)
        if rec_df is None or rec_df.empty:
            st.warning("No suggestions available.")
        else:
            if "Last Eaten" in rec_df.columns:
                rec_df["Last Eaten"] = pd.to_datetime(rec_df["Last Eaten"], errors="coerce")
            if "Days Ago" in rec_df.columns:
                rec_df["Days Ago"] = rec_df["Days Ago"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)
            st.markdown(df_to_html_table(rec_df[["Recipe", "Item Type", "Last Eaten", "Days Ago"]]), unsafe_allow_html=True)
            choices = rec_df["Recipe"].astype(str).tolist()
            if choices:
                recipe_choice = st.radio("Select recipe to save for today", choices, key="suggest_choice")
                if st.button("Save Today's Pick (Suggestion)"):
                    chosen_row = rec_df[rec_df["Recipe"] == recipe_choice].iloc[0].to_dict()
                    new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": recipe_choice, "Item Type": chosen_row.get("Item Type", "")}
                    new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                    try_save_history(new_history, history_sha)

# -----------------------
# MASTER LIST
# -----------------------
elif page == "Master List":
    st.header("Master List")
    st.write("Add / Edit / Delete recipes.")

    if callable(load_master_list) and GITHUB_REPO:
        master_df = load_master_list(GITHUB_REPO, branch=GITHUB_BRANCH)
        master_sha = get_file_sha(MASTER_LIST_FILE, repo=GITHUB_REPO, branch=GITHUB_BRANCH)
    else:
        master_df = pd.DataFrame(columns=["Recipe", "Item Type"])

    with st.form("add_recipe", clear_on_submit=True):
        new_name = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        if st.form_submit_button("Add Recipe") and new_name.strip():
            new_master = pd.concat(
                [master_df, pd.DataFrame([{"Recipe": new_name.strip(), "Item Type": new_type.strip()}])],
                ignore_index=True
            )
            try_save_master_list(new_master, master_sha)

    if not master_df.empty:
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
                edit_name = st.text_input(f"Edit name ({i}):", value=row["Recipe"], key=f"edit_name_{i}")
                edit_type = st.text_input(f"Edit type ({i}):", value=row["Item Type"], key=f"edit_type_{i}")
                if st.button("Save Edit", key=f"save_edit_{i}"):
                    master_df.at[i, "Recipe"] = edit_name
                    master_df.at[i, "Item Type"] = edit_type
                    try_save_master_list(master_df, master_sha)
                if st.button("Cancel", key=f"cancel_edit_{i}"):
                    st.session_state["edit_row"] = None
                    safe_rerun()
            if st.session_state.get("delete_row") == i:
                st.warning(f"Confirm delete '{row['Recipe']}'?")
                if st.button("Confirm Delete", key=f"confirm_del_{i}"):
                    new_master = master_df.drop(i).reset_index(drop=True)
                    try_save_master_list(new_master, master_sha)
                if st.button("Cancel Delete", key=f"cancel_del_{i}"):
                    st.session_state["delete_row"] = None
                    safe_rerun()
    else:
        st.info("No recipes found.")

# -----------------------
# HISTORY
# -----------------------
elif page == "History":
    st.header("History")
    st.write("Use the filter buttons below.")

    col1, col2, col3, col4 = st.columns(4)
    btn_prev_month = col1.button("Previous Month")
    btn_curr_month = col2.button("Current Month")
    btn_prev_week = col3.button("Previous Week")
    btn_curr_week = col4.button("Current Week")

    filtered = history_df.copy()

    if not filtered.empty and "Date" in filtered.columns:
        master_map = dict(zip(master_df["Recipe"].astype(str), master_df["Item Type"].astype(str)))
        filtered["Item Type"] = filtered["Item Type"].fillna(filtered["Recipe"].map(master_map))
        today_local = date.today()
        if btn_prev_month:
            first_of_this = today_local.replace(day=1)
            last_of_prev = first_of_this - timedelta(days=1)
            first_of_prev = last_of_prev.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first_of_prev) & (filtered["Date"].dt.date <= last_of_prev)]
        elif btn_curr_month:
            first = today_local.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first) & (filtered["Date"].dt.date <= today_local)]
        elif btn_prev_week:
            start_this_week = today_local - timedelta(days=today_local.weekday())
            prev_start = start_this_week - timedelta(days=7)
            prev_end = start_this_week - timedelta(days=1)
            filtered = filtered[(filtered["Date"].dt.date >= prev_start) & (filtered["Date"].dt.date <= prev_end)]
        elif btn_curr_week:
            start_this_week = today_local - timedelta(days=today_local.weekday())
            filtered = filtered[(filtered["Date"].dt.date >= start_this_week) & (filtered["Date"].dt.date <= today_local)]
        filtered["Days Ago"] = filtered["Date"].apply(lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA)
        filtered["Date"] = pd.to_datetime(filtered["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
        try:
            filtered["__sort_date__"] = pd.to_datetime(filtered["Date"], format="%d-%m-%Y", errors="coerce")
            filtered = filtered.sort_values("__sort_date__", ascending=True).drop(columns="__sort_date__")
        except Exception:
            filtered = filtered.sort_index(ascending=True)
        st.markdown(df_to_html_table(filtered[["Date", "Recipe", "Item Type", "Days Ago"]]), unsafe_allow_html=True)
        if st.button("Remove Today's Entry (if exists)"):
            new_hist = history_df[history_df["Date"].dt.date != date.today()].reset_index(drop=True)
            try_save_history(new_hist, history_sha)
    else:
        st.info("History is empty.")
