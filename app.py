# app.py
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
import textwrap

# Try to import your repository helper modules (they must exist in repo)
try:
    from data_manager import load_master_list, load_history, save_master_list, save_history
except Exception:
    load_master_list = None
    load_history = None
    save_master_list = None
    save_history = None

try:
    from recommendations import recommend
except Exception:
    recommend = None

# --------------------------
# Config / Secrets
# --------------------------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH") if "GITHUB_BRANCH" in st.secrets else os.environ.get("GITHUB_BRANCH", "main")
MASTER_CSV = st.secrets.get("MASTER_CSV") if "MASTER_CSV" in st.secrets else os.environ.get("MASTER_CSV", "master_list.csv")
HISTORY_CSV = st.secrets.get("HISTORY_CSV") if "HISTORY_CSV" in st.secrets else os.environ.get("HISTORY_CSV", "history.csv")

# Page config → browser tab title
st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")

# Small CSS to tighten top spacing + style tables
st.markdown(
    """
    <style>
    /* reduce top whitespace but keep title visible */
    .app-container > .main > .block-container { padding-top: 1rem !important; }

    .nb-table { border-collapse: collapse; width: 100%; font-family: Inter, sans-serif; }
    .nb-table th, .nb-table td { padding: 10px 12px; border: 1px solid #eee; }
    .nb-table thead th { background: #fafafa; text-align: left; font-weight: 600; }
    .nb-table td.center { text-align: center; }
    .nb-table td.right { text-align: right; }
    .nb-table td { text-align: left; }
    .nb-table td:last-child, .nb-table th:last-child { text-align: center; width: 7ch; }

    .nb-table-wrap { width:100%; overflow-x:auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# Helpers
# --------------------------
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        return

def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_eaten_col: str = "Last Eaten"):
    df = df.copy()

    if last_eaten_col in df.columns:
        df[last_eaten_col] = pd.to_datetime(df[last_eaten_col], errors="coerce")
        df[last_eaten_col] = df[last_eaten_col].dt.strftime("%d-%m-%Y")
        df[last_eaten_col] = df[last_eaten_col].fillna("")

    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)

    html = df.to_html(index=False, classes="nb-table", escape=False)
    return f"<div class='nb-table-wrap'>{html}</div>"

def load_data():
    master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
    history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    master_sha = None
    history_sha = None

    if load_master_list and load_history and GITHUB_REPO and GITHUB_TOKEN:
        try:
            m = load_master_list(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
            if isinstance(m, tuple):
                master_df, master_sha = m[0], (m[1] if len(m) > 1 else None)
            else:
                master_df = m
        except Exception:
            pass
        try:
            h = load_history(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
            if isinstance(h, tuple):
                history_df, history_sha = h[0], (h[1] if len(h) > 1 else None)
            else:
                history_df = h
        except Exception:
            pass

    if master_df is None or master_df.empty:
        if os.path.exists(MASTER_CSV):
            try:
                master_df = pd.read_csv(MASTER_CSV)
            except Exception:
                master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
        else:
            master_df = pd.DataFrame(columns=["Recipe", "Item Type"])

    if history_df is None or history_df.empty:
        if os.path.exists(HISTORY_CSV):
            try:
                history_df = pd.read_csv(HISTORY_CSV, parse_dates=["Date"])
            except Exception:
                history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
        else:
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

def try_save_history(df: pd.DataFrame, history_sha=None):
    if save_history and GITHUB_REPO and GITHUB_TOKEN:
        try:
            r = save_history(df, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=history_sha)
            if isinstance(r, tuple): return bool(r[0])
            return bool(r)
        except Exception: pass
    try:
        df.to_csv(HISTORY_CSV, index=False)
        return True
    except Exception:
        st.error("Failed to persist history.")
        return False

def try_save_master(df: pd.DataFrame, master_sha=None):
    if save_master_list and GITHUB_REPO and GITHUB_TOKEN:
        try:
            r = save_master_list(df, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=master_sha)
            if isinstance(r, tuple): return bool(r[0])
            return bool(r)
        except Exception: pass
    try:
        df.to_csv(MASTER_CSV, index=False)
        return True
    except Exception:
        st.error("Failed to persist master list.")
        return False

# --------------------------
# Load data
# --------------------------
master_df, history_df, master_sha, history_sha = load_data()

today = date.today()
today_pick = None
if not history_df.empty and "Date" in history_df.columns:
    hx = history_df.dropna(subset=["Date"]).copy()
    if not hx.empty:
        hx["DateOnly"] = pd.to_datetime(hx["Date"]).dt.date
        sel = hx[hx["DateOnly"] == today]
        if not sel.empty:
            today_pick = sel.sort_values("Date", ascending=False).iloc[0]["Recipe"]

# --------------------------
# App Title (top of the page)
# --------------------------
st.title("🍴 NextBite – Meal Planner App")

# --------------------------
# Sidebar Navigation
# --------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

# --------------------------
# PICK TODAY
# --------------------------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")
    if today_pick:
        st.success(f"✅ Today's pick is **{today_pick}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")

    st.write("")
    mode = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"], horizontal=True)

    if mode == "By Item Type":
        item_types = master_df["Item Type"].dropna().astype(str).unique().tolist()
        item_types = sorted([t for t in item_types if str(t).strip() != ""])
        if not item_types:
            st.warning("Master list has no Item Types yet.")
        else:
            selected_type = st.selectbox("Select Item Type:", ["-- Choose --"] + item_types, index=0)
            if selected_type and selected_type != "-- Choose --":
                filtered = master_df[master_df["Item Type"] == selected_type].copy()
                last_dates = {}
                if not history_df.empty and "Date" in history_df.columns:
                    tmp = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
                    last_dates = tmp.groupby("Recipe")["Date"].first().to_dict()

                filtered["Last Eaten"] = filtered["Recipe"].map(lambda r: last_dates.get(r) if r in last_dates else pd.NaT)
                filtered["Days Ago"] = filtered["Last Eaten"].apply(lambda d: (today - pd.to_datetime(d).date()).days if pd.notna(d) else pd.NA)

                html = df_to_html_table(filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])
                st.markdown(html, unsafe_allow_html=True)

                choices = filtered["Recipe"].astype(str).tolist()
                if choices:
                    recipe_choice = st.radio("Select recipe to save for today", choices, key="bytype_choice")
                    if st.button("Save Today's Pick (By Type)"):
                        new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": recipe_choice, "Item Type": selected_type}
                        new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                        if try_save_history(new_history, history_sha):
                            st.success(f"Saved **{recipe_choice}** to history.")
                            safe_rerun()

    else:
        if recommend:
            rec_df = recommend(master_df, history_df, min_count=5, max_count=7)
        else:
            tmp = master_df.copy()
            if "Days Ago" in tmp.columns:
                try:
                    tmp["Days Ago"] = tmp["Days Ago"].astype(float)
                except Exception: pass
                rec_df = tmp.sort_values("Days Ago", ascending=False).head(10)
            else:
                rec_df = master_df.head(10)

        if rec_df is None or rec_df.empty:
            st.warning("No suggestions available.")
        else:
            if "Last Eaten" in rec_df.columns:
                rec_df["Last Eaten"] = pd.to_datetime(rec_df["Last Eaten"], errors="coerce")
            if "Days Ago" in rec_df.columns:
                rec_df["Days Ago"] = rec_df["Days Ago"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)

            html = df_to_html_table(rec_df[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])
            st.markdown(html, unsafe_allow_html=True)

            choices = rec_df["Recipe"].astype(str).tolist()
            if choices:
                recipe_choice = st.radio("Select recipe to save for today", choices, key="suggest_choice")
                if st.button("Save Today's Pick (Suggestion)"):
                    chosen_row = rec_df[rec_df["Recipe"] == recipe_choice].iloc[0].to_dict()
                    item_type = chosen_row.get("Item Type", "")
                    new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": recipe_choice, "Item Type": item_type}
                    new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                    if try_save_history(new_history, history_sha):
                        st.success(f"Saved **{recipe_choice}** to history.")
                        safe_rerun()

# --------------------------
# MASTER LIST
# --------------------------
elif page == "Master List":
    st.header("Master List")
    st.write("Add / Edit / Delete recipes.")

    with st.form("add_recipe", clear_on_submit=True):
        new_name = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        submitted = st.form_submit_button("Add Recipe")
        if submitted:
            if not new_name.strip():
                st.warning("Provide a recipe name.")
            else:
                new_master = pd.concat([master_df, pd.DataFrame([{"Recipe": new_name.strip(), "Item Type": new_type.strip()}])], ignore_index=True)
                if try_save_master(new_master, master_sha):
                    st.success(f"Added **{new_name}** to master list.")
                    safe_rerun()

    if master_df.empty:
        st.info("No recipes found.")
    else:
        html = df_to_html_table(master_df[["Recipe", "Item Type"]])
        st.markdown(html, unsafe_allow_html=True)

# --------------------------
# HISTORY
# --------------------------
elif page == "History":
    st.header("History")
    col1, col2, col3, col4 = st.columns(4)
    btn_prev_month = col1.button("Previous Month")
    btn_curr_month = col2.button("Current Month")
    btn_prev_week = col3.button("Previous Week")
    btn_curr_week = col4.button("Current Week")

    filtered = history_df.copy()
    if not filtered.empty and "Date" in filtered.columns:
        if btn_prev_month:
            today_local = date.today()
            first_of_month = today_local.replace(day=1)
            last_prev = first_of_month - timedelta(days=1)
            first_prev = last_prev.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first_prev) & (filtered["Date"].dt.date <= last_prev)]
        elif btn_curr_month:
            today_local = date.today()
            first = today_local.replace(day=1)
            filtered = filtered[(filtered["Date"].dt.date >= first) & (filtered["Date"].dt.date <= today_local)]
        elif btn_prev_week:
            today_local = date.today()
            start_this_week = today_local - timedelta(days=today_local.weekday())
            prev_start = start_this_week - timedelta(days=7)
            prev_end = start_this_week - timedelta(days=1)
            filtered = filtered[(filtered["Date"].dt.date >= prev_start) & (filtered["Date"].dt.date <= prev_end)]
        elif btn_curr_week:
            today_local = date.today()
            start_this_week = today_local - timedelta(days=today_local.weekday())
            filtered = filtered[(filtered["Date"].dt.date >= start_this_week) & (filtered["Date"].dt.date <= today_local)]

        filtered = filtered.copy()
        filtered["Days Ago"] = filtered["Date"].apply(lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA)
        filtered["Date"] = pd.to_datetime(filtered["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
        html = df_to_html_table(filtered[["Date", "Recipe", "Item Type", "Days Ago"]].sort_values("Date", ascending=False))
        st.markdown(html, unsafe_allow_html=True)

        if st.button("Remove Today's Entry (if exists)"):
            new_hist = history_df[history_df["Date"].dt.date != date.today()].reset_index(drop=True)
            if try_save_history(new_hist, history_sha):
                st.success("Removed today's entry.")
                safe_rerun()
    else:
        st.info("History is empty.")
