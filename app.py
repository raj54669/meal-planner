# -----------------------------
# FILE: app.py
# -----------------------------
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os

from data_manager import load_master_list, save_master_list, load_history, save_history
from recommendations import recommend
from ui_widgets import apply_compact_css, render_selectable_table

# --- Config from Streamlit secrets / env ---
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN") if "GITHUB_TOKEN" in st.secrets else os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = st.secrets.get("GITHUB_REPO") if "GITHUB_REPO" in st.secrets else os.environ.get("GITHUB_REPO")
GITHUB_BRANCH = st.secrets.get("GITHUB_BRANCH") if "GITHUB_BRANCH" in st.secrets else os.environ.get("GITHUB_BRANCH", "main")

st.set_page_config(page_title="NextBite – Meal Planner App", page_icon="🍴", layout="centered")

# Apply compact CSS (reduces top whitespace and adjusts table styling)
apply_compact_css()

st.title("🍴 NextBite – Meal Planner App")

# Helper safe rerun (some Streamlit builds may not expose experimental_rerun)
def safe_rerun():
    try:
        st.experimental_rerun()
    except Exception:
        # if not available, do nothing; user can refresh
        pass

# Load data
try:
    master_df, master_sha = load_master_list(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
    history_df, history_sha = load_history(GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH)
except Exception as e:
    st.warning(f"Failed to load from GitHub: {e}")
    st.info("Falling back to local CSV files if present.")
    master_df = pd.read_csv("master_list.csv") if os.path.exists("master_list.csv") else pd.DataFrame(columns=["Recipe", "Item Type"])
    history_df = pd.read_csv("history.csv", parse_dates=["Date"]) if os.path.exists("history.csv") else pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    master_sha = None
    history_sha = None

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
if "Date" in history_df.columns:
    history_df["Date"] = pd.to_datetime(history_df["Date"], errors="coerce")

# Sidebar navigation (keep core workflow)
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Pick Today’s Recipe", "Master List", "History"]) 

# utility: today's pick
today = date.today()
today_entries = history_df.dropna(subset=["Date"]).copy()
if not today_entries.empty:
    today_entries["DateOnly"] = pd.to_datetime(today_entries["Date"]).dt.date
else:
    today_entries["DateOnly"] = pd.Series(dtype="object")

today_pick = None
if not today_entries.empty:
    sel_today = today_entries[today_entries["DateOnly"] == today]
    if not sel_today.empty:
        today_pick = sel_today.sort_values("Date", ascending=False).iloc[0]["Recipe"]

# ----------------- PICK TODAY -----------------
if page == "Pick Today’s Recipe":
    st.header("Pick Today’s Recipe")
    if today_pick:
        st.success(f"✅ Today's pick is **{today_pick}** (saved earlier).")
        st.write("If you want to change it, delete today's entry from the History tab then pick again.")

    st.write("")
    mode = st.radio("Choose option:", ["By Item Type", "Today's Suggestions"], horizontal=True)

    if mode == "By Item Type":
        types = master_df["Item Type"].dropna().astype(str).unique().tolist()
        if not types:
            st.warning("Master list is empty. Please add recipes in Master List.")
        else:
            selected_type = st.selectbox("Select Item Type:", ["-- Choose --"] + types, index=0)
            if selected_type and selected_type != "-- Choose --":
                filtered = master_df[master_df["Item Type"] == selected_type].copy()
                # compute last eaten & days ago
                if history_df is not None and not history_df.empty:
                    last_dates = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False).groupby("Recipe")["Date"].first().to_dict()
                else:
                    last_dates = {}
                filtered["Last Eaten"] = filtered["Recipe"].map(lambda r: last_dates.get(r))
                filtered["Days Ago"] = filtered["Last Eaten"].apply(lambda d: (today - pd.to_datetime(d).date()).days if pd.notna(d) else pd.NA)

                # show selectable table and radio selection
                selected = render_selectable_table(filtered, select_key="by_type_select", show_cols=["Recipe", "Last Eaten", "Days Ago"], radio_label="Select recipe to save for today")

                if selected and st.button("Save Today's Pick (By Type)"):
                    new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": selected, "Item Type": selected_type}
                    new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                    try:
                        ok, new_sha = save_history(new_history, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=history_sha)
                        if ok:
                            st.success(f"Saved **{selected}** to history (GitHub).")
                            safe_rerun()
                        else:
                            # fallback
                            new_history.to_csv("history.csv", index=False)
                            st.success(f"Saved **{selected}** to local history.csv (no GitHub configured).")
                            safe_rerun()
                    except Exception as e:
                        st.error(f"Failed to save history: {e}")

    else:
        # Today's Suggestions
        rec_df = recommend(master_df, history_df, min_count=5, max_count=7)
        if rec_df is None or rec_df.empty:
            st.warning("No suggestions available. Add more recipes or relax rules.")
        else:
            # format Last Eaten and Days Ago types
            if "Last Eaten" in rec_df.columns:
                rec_df["Last Eaten"] = pd.to_datetime(rec_df["Last Eaten"], errors="coerce")
            rec_df["Days Ago"] = rec_df["Days Ago"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)

            # show with Item Type next to Recipe
            selected = render_selectable_table(rec_df, select_key="suggest_select", show_cols=["Recipe", "Item Type", "Last Eaten", "Days Ago"], radio_label="Select recipe to save for today")
            if selected and st.button("Save Today's Pick (Suggestion)"):
                chosen = rec_df[rec_df["Recipe"] == selected].iloc[0]
                new_row = {"Date": today.strftime("%Y-%m-%d"), "Recipe": selected, "Item Type": chosen["Item Type"]}
                new_history = pd.concat([history_df, pd.DataFrame([new_row])], ignore_index=True)
                try:
                    ok, new_sha = save_history(new_history, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=history_sha)
                    if ok:
                        st.success(f"Saved **{selected}** to history (GitHub).")
                        safe_rerun()
                    else:
                        new_history.to_csv("history.csv", index=False)
                        st.success(f"Saved **{selected}** to local history.csv (no GitHub configured).")
                        safe_rerun()
                except Exception as e:
                    st.error(f"Failed to save history: {e}")

# ----------------- MASTER LIST -----------------
elif page == "Master List":
    st.header("Master List")
    st.write("Add / Edit / Delete recipes. Edit opens a popup modal.")

    with st.form("add_recipe", clear_on_submit=True):
        new_name = st.text_input("Recipe Name")
        new_type = st.text_input("Item Type")
        submitted = st.form_submit_button("Add Recipe")
        if submitted:
            if not new_name.strip():
                st.warning("Provide a recipe name.")
            else:
                new_master = pd.concat([master_df, pd.DataFrame([{"Recipe": new_name.strip(), "Item Type": new_type.strip()}])], ignore_index=True)
                try:
                    ok, new_master_sha = save_master_list(new_master, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=master_sha)
                    if ok:
                        st.success(f"Added {new_name} to GitHub master list.")
                        safe_rerun()
                    else:
                        new_master.to_csv("master_list.csv", index=False)
                        st.success(f"Added {new_name} to local master_list.csv.")
                        safe_rerun()
                except Exception as e:
                    st.error(f"Failed to save master list: {e}")

    st.markdown("### Current Recipes")
    if master_df.empty:
        st.info("No recipes found. Add some above.")
    else:
        # render rows with Edit/Delete buttons
        for idx, row in master_df.reset_index(drop=True).iterrows():
            cols = st.columns([4, 2, 1])
            cols[0].write(row["Recipe"])
            cols[1].write(row["Item Type"])
            if cols[2].button("✏️ Edit", key=f"edit_{idx}"):
                # inline edit (simple)
                new_name = st.text_input("Edit name:", value=row["Recipe"], key=f"edit_name_{idx}")
                new_type = st.text_input("Edit type:", value=row["Item Type"], key=f"edit_type_{idx}")
                if st.button("Save Edit", key=f"save_edit_{idx}"):
                    master_df.at[idx, "Recipe"] = new_name
                    master_df.at[idx, "Item Type"] = new_type
                    try:
                        ok, new_master_sha = save_master_list(master_df, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=master_sha)
                        if ok:
                            st.success("Updated master list on GitHub.")
                            safe_rerun()
                        else:
                            master_df.to_csv("master_list.csv", index=False)
                            st.success("Updated local master_list.csv.")
                            safe_rerun()
                    except Exception as e:
                        st.error(f"Failed to save master list: {e}")
            if cols[2].button("🗑️ Delete", key=f"del_{idx}"):
                if st.confirm(f"Delete '{row['Recipe']}'? This action cannot be undone."):
                    new_master = master_df.drop(idx).reset_index(drop=True)
                    try:
                        ok, new_master_sha = save_master_list(new_master, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=master_sha)
                        if ok:
                            st.success("Deleted from GitHub master list.")
                            safe_rerun()
                        else:
                            new_master.to_csv("master_list.csv", index=False)
                            st.success("Deleted from local master_list.csv.")
                            safe_rerun()
                    except Exception as e:
                        st.error(f"Failed to delete: {e}")

# ----------------- HISTORY -----------------
elif page == "History":
    st.header("History")
    st.write("Use the static filter buttons below to view historical picks.")
    col1, col2, col3, col4 = st.columns(4)
    btn_prev_month = col1.button("Previous Month")
    btn_curr_month = col2.button("Current Month")
    btn_prev_week = col3.button("Previous Week")
    btn_curr_week = col4.button("Current Week")

    filtered_df = history_df.copy()
    if history_df.empty:
        st.info("History is empty.")
    else:
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

        if not filtered_df.empty:
            filtered_df = filtered_df.copy()
            filtered_df["Days Ago"] = filtered_df["Date"].apply(lambda d: (date.today() - d.date()).days if pd.notna(d) else pd.NA)
            display_cols = ["Date", "Recipe", "Item Type", "Days Ago"]
            # format Date column to DD-MM-YYYY
            df_display = filtered_df[display_cols].copy()
            df_display["Date"] = pd.to_datetime(df_display["Date"]).dt.strftime("%d-%m-%Y")
            st.dataframe(df_display.sort_values("Date", ascending=False).reset_index(drop=True), use_container_width=True)

            if st.button("Remove Today's Entry (if exists)"):
                new_hist = history_df[history_df["Date"].dt.date != date.today()].reset_index(drop=True)
                try:
                    ok, new_history_sha = save_history(new_hist, GITHUB_REPO, GITHUB_TOKEN, branch=GITHUB_BRANCH, sha=history_sha)
                    if ok:
                        st.success("Removed today's entry from GitHub history.")
                        safe_rerun()
                    else:
                        new_hist.to_csv("history.csv", index=False)
                        st.success("Removed from local history.csv.")
                        safe_rerun()
                except Exception as e:
                    st.error(f"Failed to update history: {e}")

# -----------------------------
# End of app.py
# -----------------------------
