# app.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import os

from data_manager import load_master_list, save_master_list, load_history, save_history
from recommendations import recommend
from ui_widgets import apply_compact_css, popup_edit, render_selectable_table

# --- Config from Streamlit secrets ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")
BRANCH = "main"

if not GITHUB_REPO or not GITHUB_TOKEN:
    st.warning("GITHUB_REPO and GITHUB_TOKEN not found in secrets/env. App will run in local-file mode (CSV files read/written in repo).")

# Apply compact CSS to reduce wide tables
apply_compact_css()

st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")
st.title("🍴 NextBite – Meal Planner App")

# Load data (from GitHub if configured)
try:
    master_df, master_sha = load_master_list(GITHUB_REPO, GITHUB_TOKEN)
    history_df, history_sha = load_history(GITHUB_REPO, GITHUB_TOKEN)
except Exception as e:
    st.error(f"Failed to load from GitHub: {e}")
    st.info("Falling back to local CSV files if present.")
    # fallback local
    master_df = pd.read_csv("master_list.csv") if os.path.exists("master_list.csv") else pd.DataFrame(columns=["Recipe", "Item Type"])
    history_df = pd.read_csv("history.csv", parse_dates=["Date"]) if os.path.exists("history.csv") else pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    master_sha = None
    history_sha = None

# normalize columns
master_df.columns = [c.strip() for c in master_df.columns]
history_df.columns = [c.strip() for c in history_df.columns]

ensure_master_cols = ["Recipe", "Item Type"]
for c in ensure_master_cols:
    if c not in master_df.columns:
        master_df[c] = ""

ensure_history_cols = ["Date", "Recipe", "Item Type"]
for c in ensure_history_cols:
    if c not in history_df.columns:
        history_df[c] = pd.NA
if "Date" in history_df.columns:
    history_df["Date"] = pd.to_datetime(history_df["Date"], errors="coerce")

# Sidebar navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("", ["Pick Today’s Recipe", "Master List", "History"])

# Utility: show today's saved pick if exists
today = date.today()
today_entries = history_df.dropna(subset=["Date"]).copy()
today_entries["DateOnly"] = pd.to_datetime(today_entries["Date"]).dt.date if not today_entries.empty else pd.Series(dtype="object")
today_pick = None
if not today_entries.empty:
    sel_today = today_entries[today_entries["DateOnly"] == today]
    if not sel_today.empty:
        # show latest saved today
        today_pick = sel_today.sort_values("Date", ascending=False).iloc[0]["Recipe"]

# ----------------- PICK TODAY -----------------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")
    if today_pick:
        st.success(f"✅ Today's pick is **{today_pick}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")
    st.write("")  # spacer

    # side-by-side options (we show them horizontally)
    mode = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"], horizontal=True)

    if mode == "By Item Type":
        types = master_df["Item Type"].dropna().astype(str).unique().tolist()
        if not types:
            st.warning("Master list is empty. Please add recipes in Master List.")
        else:
            selected_type = st.selectbox("Select Item Type:", ["-- Choose --"] + types)
            if selected_type and selected_type != "-- Choose --":
                filtered = master_df[master_df["Item Type"] == selected_type].copy()
                # compute last eaten and days ago
                if history_df is not None and not history_df.empty:
                    last_dates = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False).groupby("Recipe")["Date"].first().to_dict()
                else:
                    last_dates = {}
                filtered["Last Eaten"] = filtered["Recipe"].map(lambda r: last_dates.get(r))
                filtered["Days Ago"] = filtered["Last Eaten"].apply(lambda d: (today - pd.to_datetime(d).date()).days if pd.notna(d) else None)
                # show selectable table
                selected = render_selectable_table(filtered, select_key="by_type_select", show_cols=["Recipe", "Last Eaten", "Days Ago"], radio_label="Select recipe to save for today")
                if selected and st.button("Save Today's Pick (By Type)"):
                    # append to history and push
                    new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": selected, "Item Type": selected_type}
                    new_history = history_df.copy()
                    new_history = new_history.append(new_row, ignore_index=True)
                    try:
                        ok = save_history(new_history, GITHUB_REPO, GITHUB_TOKEN, sha=history_sha) if GITHUB_REPO and GITHUB_TOKEN else False
                        if ok:
                            st.success(f"Saved **{selected}** to history (GitHub).")
                            st.experimental_rerun()
                        else:
                            # fallback local save
                            new_history.to_csv("history.csv", index=False)
                            st.success(f"Saved **{selected}** to local history.csv (no GitHub configured).")
                            st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to save history: {e}")

    else:
        # Today's Suggestions
        rec_df = recommend(master_df, history_df, min_count=5, max_count=7)
        if rec_df is None or rec_df.empty:
            st.warning("No suggestions available. Add more recipes or relax rules.")
        else:
            # ensure Last Eaten as date, Days Ago integer
            if "Last Eaten" in rec_df.columns:
                rec_df["Last Eaten"] = pd.to_datetime(rec_df["Last Eaten"], errors="coerce")
            rec_df["Days Ago"] = rec_df["Days Ago"].apply(lambda x: int(x) if pd.notna(x) else None)
            selected = render_selectable_table(rec_df, select_key="suggest_select", show_cols=["Recipe", "Last Eaten", "Days Ago"], radio_label="Select recipe to save for today")
            if selected and st.button("Save Today's Pick (Suggestion)"):
                chosen = rec_df[rec_df["Recipe"] == selected].iloc[0]
                new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": selected, "Item Type": chosen["Item Type"]}
                new_history = history_df.copy()
                new_history = new_history.append(new_row, ignore_index=True)
                try:
                    ok = save_history(new_history, GITHUB_REPO, GITHUB_TOKEN, sha=history_sha) if GITHUB_REPO and GITHUB_TOKEN else False
                    if ok:
                        st.success(f"Saved **{selected}** to history (GitHub).")
                        st.experimental_rerun()
                    else:
                        new_history.to_csv("history.csv", index=False)
                        st.success(f"Saved **{selected}** to local history.csv (no GitHub configured).")
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to save history: {e}")


# ----------------- MASTER LIST -----------------
elif page == "Master List":
    st.header("Master List")
    st.write("Add / Edit / Delete recipes. Edit opens a popup modal.")

    # Add new recipe form
    with st.form("add_recipe", clear_on_submit=True):
        new_name = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        submitted = st.form_submit_button("Add Recipe")
        if submitted:
            if not new_name.strip():
                st.warning("Provide a recipe name.")
            else:
                new_master = master_df.copy()
                new_master = new_master.append({"Recipe": new_name.strip(), "Item Type": new_type.strip()}, ignore_index=True)
                try:
                    ok = save_master_list(new_master, GITHUB_REPO, GITHUB_TOKEN, sha=master_sha) if GITHUB_REPO and GITHUB_TOKEN else False
                    if ok:
                        st.success(f"Added {new_name} to GitHub master list.")
                        st.experimental_rerun()
                    else:
                        new_master.to_csv("master_list.csv", index=False)
                        st.success(f"Added {new_name} to local master_list.csv.")
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to save master list: {e}")

    st.markdown("### Current Recipes")
    if master_df.empty:
        st.info("No recipes found. Add some above.")
    else:
        # render rows with Edit/Delete buttons; edit opens popup
        for idx, row in master_df.iterrows():
            cols = st.columns([3, 2, 1, 1])
            cols[0].write(row["Recipe"])
            cols[1].write(row["Item Type"])
            if cols[2].button("✏️ Edit", key=f"edit_{idx}"):
                # open popup editor
                def _save_edit(new_name, new_type):
                    master_df.at[idx, "Recipe"] = new_name
                    master_df.at[idx, "Item Type"] = new_type
                    try:
                        ok = save_master_list(master_df, GITHUB_REPO, GITHUB_TOKEN, sha=master_sha) if GITHUB_REPO and GITHUB_TOKEN else False
                        if ok:
                            st.success("Updated master list on GitHub.")
                        else:
                            master_df.to_csv("master_list.csv", index=False)
                            st.success("Updated local master_list.csv.")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to save master list: {e}")
                popup_title = f"Edit: {row['Recipe']}"
                popup_edit(popup_title, row["Recipe"], row["Item Type"], _save_edit)
            if cols[3].button("🗑️ Delete", key=f"del_{idx}"):
                # confirm delete with simple confirm
                if st.confirm(f"Delete '{row['Recipe']}'? This action cannot be undone."):
                    new_master = master_df.drop(idx).reset_index(drop=True)
                    try:
                        ok = save_master_list(new_master, GITHUB_REPO, GITHUB_TOKEN, sha=master_sha) if GITHUB_REPO and GITHUB_TOKEN else False
                        if ok:
                            st.success("Deleted from GitHub master list.")
                            st.experimental_rerun()
                        else:
                            new_master.to_csv("master_list.csv", index=False)
                            st.success("Deleted from local master_list.csv.")
                            st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")


# ----------------- HISTORY -----------------
elif page == "History":
    st.header("History")
    st.write("Use the static filter buttons below to view historical picks.")
    # static 4 buttons row
    col1, col2, col3, col4 = st.columns(4)
    btn_prev_month = col1.button("Previous Month")
    btn_curr_month = col2.button("Current Month")
    btn_prev_week = col3.button("Previous Week")
    btn_curr_week = col4.button("Current Week")

    # default filtered_df
    filtered_df = history_df.copy()
    if history_df.empty:
        st.info("History is empty.")
    else:
        # apply filters
        if btn_prev_month:
            today = date.today()
            first_of_this = today.replace(day=1)
            last_of_prev = first_of_this - timedelta(days=1)
            first_of_prev = last_of_prev.replace(day=1)
            filtered_df = history_df[(history_df["Date"].dt.date >= first_of_prev) & (history_df["Date"].dt.date <= last_of_prev)]
        elif btn_curr_month:
            today = date.today()
            first = today.replace(day=1)
            filtered_df = history_df[(history_df["Date"].dt.date >= first) & (history_df["Date"].dt.date <= today)]
        elif btn_prev_week:
            today = date.today()
            start_this_week = today - timedelta(days=today.weekday())
            prev_start = start_this_week - timedelta(days=7)
            prev_end = start_this_week - timedelta(days=1)
            filtered_df = history_df[(history_df["Date"].dt.date >= prev_start) & (history_df["Date"].dt.date <= prev_end)]
        elif btn_curr_week:
            today = date.today()
            start_this_week = today - timedelta(days=today.weekday())
            filtered_df = history_df[(history_df["Date"].dt.date >= start_this_week) & (history_df["Date"].dt.date <= today)]
        else:
            filtered_df = history_df.copy()

        # compute Days Ago for display
        if not filtered_df.empty:
            filtered_df = filtered_df.copy()
            filtered_df["Days Ago"] = filtered_df["Date"].apply(lambda d: (date.today() - d.date()).days if pd.notna(d) else None)
            # show compact table
            display_cols = ["Date", "Recipe", "Item Type", "Days Ago"]
            st.dataframe(filtered_df[display_cols].sort_values("Date", ascending=False).reset_index(drop=True), use_container_width=True)

            # quick action: remove today's entry
            if st.button("Remove Today's Entry (if exists)"):
                new_hist = history_df[history_df["Date"].dt.date != date.today()].reset_index(drop=True)
                try:
                    ok = save_history(new_hist, GITHUB_REPO, GITHUB_TOKEN, sha=history_sha) if GITHUB_REPO and GITHUB_TOKEN else False
                    if ok:
                        st.success("Removed today's entry from GitHub history.")
                        st.experimental_rerun()
                    else:
                        new_hist.to_csv("history.csv", index=False)
                        st.success("Removed from local history.csv.")
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"Failed to update history: {e}")
