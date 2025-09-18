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
    # If data_manager isn't present or has different signatures, we'll fallback to local CSV I/O below.
    load_master_list = None
    load_history = None
    save_master_list = None
    save_history = None

try:
    from recommendations import recommend
except Exception:
    recommend = None

# --------------------------
# Config / Secrets (no REPO_NAME)
# --------------------------
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH") if "GITHUB_BRANCH" in st.secrets else os.environ.get("GITHUB_BRANCH", "main")
MASTER_CSV = st.secrets.get("MASTER_CSV") if "MASTER_CSV" in st.secrets else os.environ.get("MASTER_CSV", "master_list.csv")
HISTORY_CSV = st.secrets.get("HISTORY_CSV") if "HISTORY_CSV" in st.secrets else os.environ.get("HISTORY_CSV", "history.csv")

# Page config
st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")

# Small CSS to tighten top spacing + style our generated HTML tables
st.markdown(
    """
    <style>
    /* reduce top whitespace but keep title visible */
    .app-container > .main > .block-container { padding-top: 1rem !important; }

    /* simple table look */
    .nb-table { border-collapse: collapse; width: 100%; font-family: Inter, sans-serif; }
    .nb-table th, .nb-table td { padding: 10px 12px; border: 1px solid #eee; }
    .nb-table thead th { background: #fafafa; text-align: left; font-weight: 600; }
    .nb-table td.center { text-align: center; }
    .nb-table td.right { text-align: right; }

    /* small responsive fix */
    .nb-table-wrap { width:100%; overflow-x:auto; }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------
# Helpers
# --------------------------
def safe_rerun():
    """Call experimental_rerun if available."""
    try:
        st.experimental_rerun()
    except Exception:
        # older/newer streamlit builds may not support it; ignore
        return


def df_to_html_table(df: pd.DataFrame, days_col: str = "Days Ago", last_eaten_col: str = "Last Eaten"):
    """
    Render a DataFrame to an HTML table string with:
      - no index (index=False)
      - Last Eaten formatted as DD-MM-YYYY (if present)
      - Days Ago integer (no decimals), blank or '-' for missing
      - CSS class nb-table so our CSS applies
    """
    df = df.copy()

    # Format Last Eaten
    if last_eaten_col in df.columns:
        df[last_eaten_col] = pd.to_datetime(df[last_eaten_col], errors="coerce")
        df[last_eaten_col] = df[last_eaten_col].dt.strftime("%d-%m-%Y")
        df[last_eaten_col] = df[last_eaten_col].fillna("")

    # Format Days Ago (no decimals)
    if days_col in df.columns:
        def fmt_days(x):
            if pd.isna(x) or x == "" or x is None:
                return "-"
            try:
                return str(int(float(x)))
            except Exception:
                return str(x)
        df[days_col] = df[days_col].apply(fmt_days)

    # Convert to HTML; add classes so CSS picks it up
    html = df.to_html(index=False, classes="nb-table", escape=False)
    # Wrap with a container so overflow can be handled
    return f"<div class='nb-table-wrap'>{html}</div>"


def load_data():
    """
    Load master and history. We support:
     - data_manager.load_master_list/load_history that may return (df, sha) or df
     - fallback to reading local CSV files (MASTER_CSV, HISTORY_CSV)
    Returns: (master_df, history_df, master_sha, history_sha)
    """
    master_df = pd.DataFrame(columns=["Recipe", "Item Type"])
    history_df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    master_sha = None
    history_sha = None

    # Try GitHub-backed loader first if available and credentials provided
    if load_master_list and load_history and GITHUB_REPO and GITHUB_TOKEN:
        try:
            m = load_master_list(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
            if isinstance(m, tuple) and len(m) >= 1:
                master_df = m[0]
                if len(m) > 1:
                    master_sha = m[1]
            else:
                master_df = m
        except Exception:
            # fall through to local
            pass

        try:
            h = load_history(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
            if isinstance(h, tuple) and len(h) >= 1:
                history_df = h[0]
                if len(h) > 1:
                    history_sha = h[1]
            else:
                history_df = h
        except Exception:
            pass

    # If still empty / not loaded, try local CSVs
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

    # Normalize column names
    master_df.columns = [c.strip() for c in master_df.columns]
    history_df.columns = [c.strip() for c in history_df.columns]

    # Ensure required columns exist
    for c in ["Recipe", "Item Type"]:
        if c not in master_df.columns:
            master_df[c] = ""

    for c in ["Date", "Recipe", "Item Type"]:
        if c not in history_df.columns:
            history_df[c] = pd.NA

    # Ensure Date parsed
    if "Date" in history_df.columns:
        history_df["Date"] = pd.to_datetime(history_df["Date"], errors="coerce")

    return master_df, history_df, master_sha, history_sha


def try_save_history(df: pd.DataFrame, history_sha=None):
    """
    Try to save history with your data_manager.save_history signature.
    If that fails, fallback to CSV write.
    Return True on success else False.
    """
    # Try to use provided save_history function (if available)
    if save_history and GITHUB_REPO and GITHUB_TOKEN:
        try:
            # try a signature that returns (ok, new_sha)
            r = save_history(df, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=history_sha)
            # Accept both boolean or tuple responses
            if isinstance(r, tuple):
                ok = r[0]
            else:
                ok = bool(r)
            if ok:
                return True
        except TypeError:
            # try a simpler signature
            try:
                r = save_history(df, GITHUB_REPO, GITHUB_TOKEN)
                return bool(r)
            except Exception:
                pass
        except Exception:
            pass

    # Fallback to local CSV
    try:
        df.to_csv(HISTORY_CSV, index=False)
        return True
    except Exception:
        st.error("Failed to persist history (both GitHub and local CSV failed). Check logs.")
        return False


def try_save_master(df: pd.DataFrame, master_sha=None):
    """Same defensive save for master list."""
    if save_master_list and GITHUB_REPO and GITHUB_TOKEN:
        try:
            r = save_master_list(df, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=master_sha)
            if isinstance(r, tuple):
                return bool(r[0])
            return bool(r)
        except Exception:
            pass
    try:
        df.to_csv(MASTER_CSV, index=False)
        return True
    except Exception:
        st.error("Failed to persist master list (both GitHub and local CSV failed). Check logs.")
        return False


# --------------------------
# Load data
# --------------------------
master_df, history_df, master_sha, history_sha = load_data()

# Utility: compute today's pick if any
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
# Sidebar Navigation (unchanged)
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

    st.write("")  # spacer
    mode = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"], horizontal=True)

    if mode == "By Item Type":
        # get item types
        item_types = master_df["Item Type"].dropna().astype(str).unique().tolist()
        item_types = sorted([t for t in item_types if str(t).strip() != ""])
        if not item_types:
            st.warning("Master list has no Item Types yet. Please add entries in Master List.")
        else:
            selected_type = st.selectbox("Select Item Type:", ["-- Choose --"] + item_types, index=0)
            if selected_type and selected_type != "-- Choose --":
                filtered = master_df[master_df["Item Type"] == selected_type].copy()

                # compute Last Eaten and Days Ago
                last_dates = {}
                if not history_df.empty and "Date" in history_df.columns:
                    tmp = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
                    last_dates = tmp.groupby("Recipe")["Date"].first().to_dict()

                filtered["Last Eaten"] = filtered["Recipe"].map(lambda r: last_dates.get(r) if r in last_dates else pd.NaT)
                filtered["Days Ago"] = filtered["Last Eaten"].apply(lambda d: (today - pd.to_datetime(d).date()).days if pd.notna(d) else pd.NA)

                # Render HTML table (no index) and center+narrow Days Ago via CSS
                html = df_to_html_table(filtered[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])
                st.markdown(html, unsafe_allow_html=True)

                # selection radio below the table (keeps core workflow)
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
                            st.error("Failed to save history. See logs.")

    else:
        # Today's Suggestions
        if recommend:
            rec_df = recommend(master_df, history_df, min_count=5, max_count=7)
        else:
            # fallback: use top by Days Ago if column exists (descending)
            tmp = master_df.copy()
            if "Days Ago" in tmp.columns:
                try:
                    tmp["Days Ago"] = tmp["Days Ago"].astype(float)
                except Exception:
                    pass
                rec_df = tmp.sort_values("Days Ago", ascending=False).head(10)
            else:
                rec_df = master_df.head(10)

        if rec_df is None or rec_df.empty:
            st.warning("No suggestions available.")
        else:
            # Ensure Last Eaten & Days Ago formatting
            if "Last Eaten" in rec_df.columns:
                rec_df["Last Eaten"] = pd.to_datetime(rec_df["Last Eaten"], errors="coerce")
            if "Days Ago" in rec_df.columns:
                rec_df["Days Ago"] = rec_df["Days Ago"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)

            html = df_to_html_table(rec_df[["Recipe", "Item Type", "Last Eaten", "Days Ago"]])
            st.markdown(html, unsafe_allow_html=True)

            # selection radio
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
                        st.error("Failed to save history. See logs.")

# --------------------------
# MASTER LIST
# --------------------------
elif page == "Master List":
    st.header("Master List")
    st.write("Add / Edit / Delete recipes. Edit opens inline editor below each row.")

    # Add recipe form
    with st.form("add_recipe", clear_on_submit=True):
        new_name = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        submitted = st.form_submit_button("Add Recipe")
        if submitted:
            if not new_name.strip():
                st.warning("Provide a recipe name.")
            else:
                new_master = pd.concat([master_df, pd.DataFrame([{"Recipe": new_name.strip(), "Item Type": new_type.strip()}])], ignore_index=True)
                ok = try_save_master(new_master, master_sha)
                if ok:
                    st.success(f"Added **{new_name}** to master list.")
                    safe_rerun()
                else:
                    st.error("Failed to save master list. See logs.")

    st.markdown("")  # spacing
    if master_df.empty:
        st.info("No recipes found. Add some above.")
    else:
        # Show table (no index)
        html = df_to_html_table(master_df[["Recipe", "Item Type"]])
        st.markdown(html, unsafe_allow_html=True)

        # Provide inline edit/delete per row (simple)
        for i, row in master_df.reset_index(drop=True).iterrows():
            cols = st.columns([4, 2, 1])
            cols[0].write(row["Recipe"])
            cols[1].write(row["Item Type"])
            if cols[2].button("✏️ Edit", key=f"edit_{i}"):
                # show inline editor
                new_name = st.text_input("Edit name:", value=row["Recipe"], key=f"edit_name_{i}")
                new_type = st.text_input("Edit type:", value=row["Item Type"], key=f"edit_type_{i}")
                if st.button("Save Edit", key=f"save_edit_{i}"):
                    master_df.at[i, "Recipe"] = new_name
                    master_df.at[i, "Item Type"] = new_type
                    ok = try_save_master(master_df, master_sha)
                    if ok:
                        st.success("Updated master list.")
                        safe_rerun()
                    else:
                        st.error("Failed to save master list.")
            if cols[2].button("🗑️ Delete", key=f"del_{i}"):
                if st.confirm(f"Delete '{row['Recipe']}'? This action cannot be undone."):
                    new_master = master_df.drop(i).reset_index(drop=True)
                    ok = try_save_master(new_master, master_sha)
                    if ok:
                        st.success("Deleted entry.")
                        safe_rerun()
                    else:
                        st.error("Failed to delete entry.")

# --------------------------
# HISTORY
# --------------------------
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

        # Days Ago column
        filtered = filtered.copy()
        filtered["Days Ago"] = filtered["Date"].apply(lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA)

        # format Date to DD-MM-YYYY
        filtered["Date"] = pd.to_datetime(filtered["Date"], errors="coerce").dt.strftime("%d-%m-%Y")
        html = df_to_html_table(filtered[["Date", "Recipe", "Item Type", "Days Ago"]].sort_values("Date", ascending=False))
        st.markdown(html, unsafe_allow_html=True)

        if st.button("Remove Today's Entry (if exists)"):
            new_hist = history_df[history_df["Date"].dt.date != date.today()].reset_index(drop=True)
            ok = try_save_history(new_hist, history_sha)
            if ok:
                st.success("Removed today's entry.")
                safe_rerun()
            else:
                st.error("Failed to update history.")
    else:
        st.info("History is empty.")
