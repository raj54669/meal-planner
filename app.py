# app.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
import os
import textwrap

# Try to import repository helpers (if present)
try:
    from data_manager import (
        load_master_list,
        load_history,
        save_master_list,
        save_history,
        get_file_sha   # ✅ add this
    )
except Exception:
    load_master_list = None
    load_history = None
    save_master_list = None
    save_history = None
    get_file_sha = None   # ✅ add fallback

try:
    from recommendations import recommend
except Exception:
    recommend = None

# -----------------------
# Config / Secrets (defensive)
# -----------------------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if isinstance(st.secrets, dict) or hasattr(st, "secrets") else None
if GITHUB_TOKEN is None:
    # st.secrets supports get, but some environments may not provide it as dict; use get with fallback
    try:
        GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN")
    except Exception:
        GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

GITHUB_REPO = None
GITHUB_BRANCH = None
MASTER_CSV = "master_list.csv"
HISTORY_CSV = "history.csv"
try:
    # preferred keys (defensive)
    GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")
    GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH") if "GITHUB_BRANCH" in st.secrets else os.environ.get("GITHUB_BRANCH", "main")
    MASTER_CSV = st.secrets.get("MASTER_CSV") if "MASTER_CSV" in st.secrets else os.environ.get("MASTER_CSV", MASTER_CSV)
    HISTORY_CSV = st.secrets.get("HISTORY_CSV") if "HISTORY_CSV" in st.secrets else os.environ.get("HISTORY_CSV", HISTORY_CSV)
except Exception:
    # fallback to env
    GITHUB_REPO = os.environ.get("GITHUB_REPO")
    GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
    MASTER_CSV = os.environ.get("MASTER_CSV", MASTER_CSV)
    HISTORY_CSV = os.environ.get("HISTORY_CSV", HISTORY_CSV)

# Page config (title appears in browser tab)
st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")

# Small CSS to tighten top spacing but keep title visible and make Days Ago centered/narrow
st.markdown(
    """
    <style>
    /* keep the app title visible; slightly reduce top padding but not hide */
    .app-container > .main > .block-container { padding-top: 1rem !important; }

    /* table style used for our HTML-rendered tables */
    .nb-table { border-collapse: collapse; width: 100%; font-family: Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial; }
    .nb-table th, .nb-table td { padding: 10px 12px; border: 1px solid #eee; }
    .nb-table thead th { background: #fafafa; text-align: left; font-weight: 600; }
    .nb-table td.center { text-align: center; }
    .nb-table td.right { text-align: right; }

    /* narrow Days Ago column by applying a max-width to that cell */
    .nb-table td.daysago { text-align: center; width: 60px; white-space: nowrap; }

    /* wrap container for overflow */
    .nb-table-wrap { width:100%; overflow-x:auto; }

    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------
# Helpers
# -----------------------
def safe_rerun():
    """Call experimental_rerun if available, else do nothing."""
    try:
        st.experimental_rerun()
    except Exception:
        return


def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_col: str = "Last Eaten"):
    """
    Convert DataFrame to HTML table with:
      - no index
      - Last Eaten formatted as DD-MM-YYYY
      - Days Ago shown as integer (no decimals), '-' when missing
      - Days Ago cell gets class 'daysago' for narrow/centered styling
    """
    df = df.copy()

    # Format Last Eaten
    if last_col in df.columns:
        df[last_col] = pd.to_datetime(df[last_col], errors="coerce")
        df[last_col] = df[last_col].dt.strftime("%d-%m-%Y")
        df[last_col] = df[last_col].fillna("")

    # Format Days Ago: int, or '-'
    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)

    # Convert to HTML and inject classes for Days Ago column cells
    html = df.to_html(index=False, classes="nb-table", escape=False)
    # post-process: add class daysago to the last column td entries (simple hack)
    # split table into head/body and replace <td> in last column
    # We'll do a robust approach: convert with pandas, then rebuild minimal HTML manually
    cols = list(df.columns)
    thead_cells = "".join(f"<th>{c}</th>" for c in cols)
    tbody_rows = ""
    for _, r in df.iterrows():
        row_cells = ""
        for i, c in enumerate(cols):
            v = r[c] if pd.notna(r[c]) else ""
            v = "" if v is None else v
            # if this is Days Ago column, add special class
            if c == days_col:
                row_cells += f"<td class='daysago'>{v}</td>"
            else:
                row_cells += f"<td>{v}</td>"
        tbody_rows += f"<tr>{row_cells}</tr>"
    full_html = f"<div class='nb-table-wrap'><table class='nb-table'><thead><tr>{thead_cells}</tr></thead><tbody>{tbody_rows}</tbody></table></div>"
    return full_html


def load_data():
    """
    Load master and history either via data_manager helpers (if present and GitHub configured)
    or fallback to local CSV files.
    Returns: master_df, history_df, master_sha, history_sha
    """
    master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
    history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    master_sha = None
    history_sha = None

    # Try data_manager -> GitHub path
    if load_master_list and load_history and GITHUB_REPO and GITHUB_TOKEN:
        try:
            m = load_master_list(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
            if isinstance(m, tuple):
                master_df = m[0]
                master_sha = m[1] if len(m) > 1 else None
            else:
                master_df = m
        except Exception:
            master_df = pd.DataFrame(columns=["Recipe", "Item Type"])

        try:
            h = load_history(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
            if isinstance(h, tuple):
                history_df = h[0]
                history_sha = h[1] if len(h) > 1 else None
            else:
                history_df = h
        except Exception:
            history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

    # Fallback to local CSVs if needed
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

    # Normalize columns
    master_df.columns = [c.strip() for c in master_df.columns]
    history_df.columns = [c.strip() for c in history_df.columns]

    # Ensure required columns
    for c in ["Recipe", "Item Type"]:
        if c not in master_df.columns:
            master_df[c] = ""
    for c in ["Date", "Recipe", "Item Type"]:
        if c not in history_df.columns:
            history_df[c] = pd.NA

    if "Date" in history_df.columns:
        history_df["Date"] = pd.to_datetime(history_df["Date"], errors="coerce")

    return master_df, history_df, master_sha, history_sha


def try_save_master(df: pd.DataFrame, master_sha=None):
    """
    Attempt to save master list via save_master_list helper (if available.)
    If not, fallback to local CSV. Return True on success.
    """
    if save_master_list and GITHUB_REPO and GITHUB_TOKEN:
        try:
            r = save_master_list(df, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=master_sha)
            if isinstance(r, tuple):
                return bool(r[0])
            return bool(r)
        except TypeError:
            # try simpler signature
            try:
                return bool(save_master_list(df, GITHUB_REPO, GITHUB_TOKEN))
            except Exception:
                pass
        except Exception:
            pass

    # fallback to local
    try:
        df.to_csv(MASTER_CSV, index=False)
        return True
    except Exception:
        st.error("Failed to persist master list (GitHub + local both failed).")
        return False


def try_save_history(df: pd.DataFrame, history_sha=None):
    """
    Attempt to save history via save_history helper; fallback to CSV.
    """
    if save_history and GITHUB_REPO and GITHUB_TOKEN:
        try:
            r = save_history(df, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=history_sha)
            if isinstance(r, tuple):
                return bool(r[0])
            return bool(r)
        except TypeError:
            try:
                return bool(save_history(df, GITHUB_REPO, GITHUB_TOKEN))
            except Exception:
                pass
        except Exception:
            pass

    try:
        df.to_csv(HISTORY_CSV, index=False)
        return True
    except Exception:
        st.error("Failed to persist history (GitHub + local both failed).")
        return False


# -----------------------
# Load data
# -----------------------
master_df, history_df, master_sha, history_sha = load_data()

# -----------------------
# Top-level Title (visible on every page)
# -----------------------
st.title("🍴 NextBite – Meal Planner App")  # keep visible at top of page

# -----------------------
# Sidebar navigation (keep core workflow)
# -----------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"])

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
# PICK TODAY (unchanged primary flow)
# -----------------------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")
    if today_pick:
        st.success(f"✅ Today's pick is **{today_pick}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")

    st.write("")  # spacer
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

                # compute last eaten & days ago using history
                last_dates = {}
                if not history_df.empty and "Date" in history_df.columns:
                    tmp = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
                    last_dates = tmp.groupby("Recipe")["Date"].first().to_dict()

                filtered["Last Eaten"] = filtered["Recipe"].map(lambda r: last_dates.get(r) if r in last_dates else pd.NaT)
                filtered["Days Ago"] = filtered["Last Eaten"].apply(lambda d: (today - pd.to_datetime(d).date()).days if pd.notna(d) else pd.NA)

                html = df_to_html_table(filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])
                st.markdown(html, unsafe_allow_html=True)

                # selection radio below the table
                choices = filtered["Recipe"].astype(str).tolist()
                if choices:
                    recipe_choice = st.radio("Select recipe to save for today", choices, key="bytype_choice")
                    if st.button("Save Today's Pick (By Type)"):
                        new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": recipe_choice, "Item Type": selected_type}
                        new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                        ok = try_save_history(new_history, history_sha)
                        if ok:
                            st.success(f"Saved **{recipe_choice}** to history.")
                            safe_rerun()
                        else:
                            st.error("Failed to save history. Check logs.")

    else:
        # Today's Suggestions
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
                    ok = try_save_history(new_history, history_sha)
                    if ok:
                        st.success(f"Saved **{recipe_choice}** to history.")
                        safe_rerun()
                    else:
                        st.error("Failed to save history. Check logs.")

# -----------------------
# MASTER LIST (restore Edit & Delete buttons)

# -----------------------

# -----------------------
elif page == "Master List":
    st.header("Master List")
    st.write("Add / Edit / Delete recipes. Edit opens inline editor for the selected row.")

    # Always reload latest master list to reflect changes
    if callable(load_master_list):
        master_df = load_master_list()
        master_sha = get_file_sha(MASTER_LIST_FILE)
    else:
        st.error("⚠️ load_master_list not available. Check data_manager.py import.")
        master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
        master_sha = None

    # Add recipe form
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
                ok = try_save_master(new_master, master_sha)
                if ok:
                    st.success(f"Added **{new_name}** to master list.")
                    # 🔥 Reload both DataFrame and SHA
                    if callable(load_master_list):
                        master_df = load_master_list()
                    if callable(get_file_sha):
                        master_sha = get_file_sha(MASTER_LIST_FILE)
                    safe_rerun()
                else:
                    st.error("Failed to save master list. Check logs.")

    st.markdown("")  # spacing

    if master_df.empty:
        st.info("No recipes found. Add some above.")
    else:
        # Initialize session keys for editing/deleting
        if "edit_row" not in st.session_state:
            st.session_state["edit_row"] = None
        if "delete_row" not in st.session_state:
            st.session_state["delete_row"] = None

        # Header row
        cols = st.columns([4, 2, 1, 1])
        cols[0].markdown("**Recipe**")
        cols[1].markdown("**Item Type**")
        cols[2].markdown("**Edit**")
        cols[3].markdown("**Delete**")

        # Row controls: Edit / Delete (inline)
        for i, row in master_df.reset_index(drop=True).iterrows():
            cols = st.columns([4, 2, 1, 1])
            cols[0].write(row["Recipe"])
            cols[1].write(row["Item Type"])

            # Edit button
            if cols[2].button("✏️", key=f"edit_btn_{i}"):
                st.session_state["edit_row"] = i
                st.session_state["delete_row"] = None
                safe_rerun()

            # Delete button
            if cols[3].button("🗑️", key=f"del_btn_{i}"):
                st.session_state["delete_row"] = i
                st.session_state["edit_row"] = None
                safe_rerun()

            # If this row is selected for edit, show inline editor
            if st.session_state.get("edit_row") == i:
                st.markdown("---")
                edit_name = st.text_input(f"Edit name ({i}):", value=row["Recipe"], key=f"edit_name_{i}")
                edit_type = st.text_input(f"Edit type ({i}):", value=row["Item Type"], key=f"edit_type_{i}")
                if st.button("Save Edit", key=f"save_edit_{i}"):
                    master_df.at[i, "Recipe"] = edit_name
                    master_df.at[i, "Item Type"] = edit_type
                    ok = try_save_master(master_df, master_sha)
                    if ok:
                        st.success("Updated master list.")
                        st.session_state["edit_row"] = None
                        if callable(load_master_list):
                            master_df = load_master_list()
                        if callable(get_file_sha):
                            master_sha = get_file_sha(MASTER_LIST_FILE)
                        safe_rerun()
                    else:
                        st.error("Failed to save master list. See logs.")
                if st.button("Cancel", key=f"cancel_edit_{i}"):
                    st.session_state["edit_row"] = None
                    safe_rerun()

            # If deletion was requested for this row, ask confirm
            if st.session_state.get("delete_row") == i:
                st.warning(f"Confirm delete '{row['Recipe']}'?")
                if st.button("Confirm Delete", key=f"confirm_del_{i}"):
                    new_master = master_df.drop(i).reset_index(drop=True)
                    ok = try_save_master(new_master, master_sha)
                    if ok:
                        st.success("Deleted entry.")
                        st.session_state["delete_row"] = None
                        if callable(load_master_list):
                            master_df = load_master_list()
                        if callable(get_file_sha):
                            master_sha = get_file_sha(MASTER_LIST_FILE)
                        safe_rerun()
                    else:
                        st.error("Failed to delete entry. See logs.")
                if st.button("Cancel Delete", key=f"cancel_del_{i}"):
                    st.session_state["delete_row"] = None
                    safe_rerun()
# -----------------------


# HISTORY (Item Type shown; sorted oldest → newest)
# -----------------------
elif page == "History":
    st.header("History")
    st.write("Use the static filter buttons below to view historical picks.")

    col1, col2, col3, col4 = st.columns(4)
    btn_prev_month = col1.button("Previous Month")
    btn_curr_month = col2.button("Current Month")
    btn_prev_week = col3.button("Previous Week")
    btn_curr_week = col4.button("Current Week")

    filtered = history_df.copy()

    if not filtered.empty and "Date" in filtered.columns:
        # fill Item Type in history from master where missing
        master_map = dict(zip(master_df["Recipe"].astype(str), master_df["Item Type"].astype(str)))
        filtered["Item Type"] = filtered["Item Type"].fillna(filtered["Recipe"].map(master_map))

        # apply filters
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

        # compute Days Ago and format Date
        filtered = filtered.copy()
        filtered["Days Ago"] = filtered["Date"].apply(lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA)
        filtered["Date"] = pd.to_datetime(filtered["Date"], errors="coerce").dt.strftime("%d-%m-%Y")

        # Sort oldest -> newest (ascending)
        try:
            # attempt to sort by original parsed Date column if available
            if "Date" in filtered.columns:
                # We can't sort by formatted string reliably; re-parse
                filtered["__sort_date__"] = pd.to_datetime(filtered["Date"], format="%d-%m-%Y", errors="coerce")
                filtered = filtered.sort_values("__sort_date__", ascending=True).drop(columns="__sort_date__")
            else:
                filtered = filtered.sort_index(ascending=True)
        except Exception:
            filtered = filtered.sort_index(ascending=True)

        html = df_to_html_table(filtered[["Date", "Recipe", "Item Type", "Days Ago"]])
        st.markdown(html, unsafe_allow_html=True)

        if st.button("Remove Today's Entry (if exists)"):
            try:
                new_hist = history_df[history_df["Date"].dt.date != date.today()].reset_index(drop=True)
                ok = try_save_history(new_hist, history_sha)
                if ok:
                    st.success("Removed today's entry.")
                    safe_rerun()
                else:
                    st.error("Failed to update history. Check logs.")
            except Exception:
                st.error("Unable to remove today's entry. Check history data format.")
    else:
        st.info("History is empty.")
