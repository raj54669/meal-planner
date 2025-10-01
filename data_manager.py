import pandas as pd
import streamlit as st
from datetime import datetime
from io import StringIO
import hashlib
import os
import tempfile
import shutil

# ---------- Atomic Save ----------
def atomic_save(df: pd.DataFrame, filepath: str):
    """Safely save CSV without risk of corruption."""
    tmp_fd, tmp_path = tempfile.mkstemp()
    os.close(tmp_fd)
    try:
        df.to_csv(tmp_path, index=False)
        shutil.move(tmp_path, filepath)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ---------- Load Master ----------
def load_master_list(repo=None, branch="main", filename="master_list.csv"):
    try:
        if repo:
            file_content = repo.get_contents(filename, ref=branch)
            df = pd.read_csv(StringIO(file_content.decoded_content.decode("utf-8")))
        else:
            df = pd.read_csv(filename)
        return df
    except Exception as e:
        st.error(f"❌ Failed to load {filename} from branch '{branch}': {e}")
        return pd.DataFrame(columns=["Recipe", "Item Type"])

# ---------- Load History ----------
def load_history(repo=None, branch="main", filename="history.csv"):
    try:
        if repo:
            file_content = repo.get_contents(filename, ref=branch)
            df = pd.read_csv(StringIO(file_content.decoded_content.decode("utf-8")))
        else:
            df = pd.read_csv(filename)

        # 🔑 Ensure Date is always datetime
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

        return df
    except Exception as e:
        st.error(f"❌ Failed to load {filename} from branch '{branch}': {e}")
        return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, item_type="", repo=None, branch="main", filename="history.csv"):
    """Save today's recipe into history with duplicate protection."""
    today = datetime.today().date()

    # Load history
    history = load_history(repo, branch, filename)
    history["Date"] = pd.to_datetime(history["Date"], errors="coerce")

    # Find today's entries
    today_entries = history[history["Date"].dt.date == today]

    if not today_entries.empty:
        if today_entries.iloc[0]["Recipe"] == recipe:
            # ✅ Same recipe already saved → do nothing
            return history
        else:
            # 🔄 Different recipe exists → remove it before saving new
            history = history[history["Date"].dt.date != today].reset_index(drop=True)

    # Add today's recipe (new or replacement)
    new_row = pd.DataFrame([{
        "Date": today.strftime("%Y-%m-%d"),
        "Recipe": recipe,
        "Item Type": item_type
    }])
    updated = pd.concat([history, new_row], ignore_index=True)

    # Ensure Date is datetime
    updated["Date"] = pd.to_datetime(updated["Date"], errors="coerce")

    # Save back to GitHub or local
    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(
            file.path,
            f"Update history {today}",
            updated.to_csv(index=False),
            file.sha,
            branch=branch
        )
    else:
        atomic_save(updated, filename)

    return updated

# ---------- Delete Today ----------
def delete_today_pick(today_str=None, repo=None, branch="main", filename="history.csv"):
    """Delete today's recipe entry from history if it exists. 
    If no entry exists, just return history unchanged."""
    if today_str is None:
        today = datetime.today().date()
    else:
        today = pd.to_datetime(today_str, errors="coerce").date()

    # Load history
    history = load_history(repo, branch, filename)
    history["Date"] = pd.to_datetime(history["Date"], errors="coerce")

    # Check if today's entry exists
    today_entries = history[history["Date"].dt.date == today]
    if today_entries.empty:
        # ✅ No recipe saved today → just return unchanged
        return history

    # Remove today's entries
    updated = history[history["Date"].dt.date != today].reset_index(drop=True)

    # Ensure Date is datetime
    updated["Date"] = pd.to_datetime(updated["Date"], errors="coerce")

    # Save back
    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(
            file.path,
            f"Delete today's entry {today}",
            updated.to_csv(index=False),
            file.sha,
            branch=branch
        )
    else:
        atomic_save(updated, filename)

    return updated

    
# ---------- Add to Master ----------
def add_recipe_to_master(recipe, item_type, repo=None, branch="main", filename="master_list.csv"):
    new_row = pd.DataFrame([{"Recipe": recipe, "Item Type": item_type}])

    master = load_master_list(repo, branch, filename)
    updated = pd.concat([master, new_row], ignore_index=True)

    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(file.path, "Add recipe", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        atomic_save(updated, filename)

    return updated

# ---------- Edit Recipe in Master ----------
def edit_recipe_in_master(old_recipe, new_recipe, new_item_type, repo=None, branch="main", filename="master_list.csv"):
    master = load_master_list(repo, branch, filename)

    if old_recipe not in master["Recipe"].values:
        return master  # nothing to edit

    master.loc[master["Recipe"] == old_recipe, ["Recipe", "Item Type"]] = [new_recipe, new_item_type]

    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(file.path, f"Edit recipe {old_recipe}", master.to_csv(index=False), file.sha, branch=branch)
    else:
        atomic_save(master, filename)

    return master

# ---------- Delete Recipe from Master ----------
def delete_recipe_from_master(recipe, repo=None, branch="main", filename="master_list.csv"):
    master = load_master_list(repo, branch, filename)
    updated = master[master["Recipe"] != recipe].reset_index(drop=True)

    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(file.path, f"Delete recipe {recipe}", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        atomic_save(updated, filename)

    return updated

# ---------- Utility: Get File SHA ----------
def get_file_sha(filepath: str, repo=None, branch="main"):
    if repo:
        try:
            file = repo.get_contents(filepath, ref=branch)
            return file.sha
        except Exception as e:
            st.error(f"❌ Failed to get SHA for {filepath}: {e}")
            return None

    if not os.path.exists(filepath):
        return None

    with open(filepath, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()
