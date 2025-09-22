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
            return df
        else:
            return pd.read_csv(filename)
    except Exception as e:
        st.error(f"❌ Failed to load {filename} from branch '{branch}': {e}")
        return pd.DataFrame(columns=["Recipe", "Item Type"])

# ---------- Load History ----------
def load_history(repo=None, branch="main", filename="history.csv"):
    try:
        if repo:
            file_content = repo.get_contents(filename, ref=branch)
            df = pd.read_csv(StringIO(file_content.decoded_content.decode("utf-8")))
            return df
        else:
            return pd.read_csv(filename)
    except Exception as e:
        st.error(f"❌ Failed to load {filename} from branch '{branch}': {e}")
        return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, item_type="", repo=None, branch="main", filename="history.csv"):
    today = datetime.today().strftime("%Y-%m-%d")
    new_row = pd.DataFrame([{"Date": today, "Recipe": recipe, "Item Type": item_type}])

    history = load_history(repo, branch, filename)
    history = history[history["Date"] != today]  # drop today's old if exists
    updated = pd.concat([history, new_row], ignore_index=True)

    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(file.path, f"Update history {today}", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        atomic_save(updated, filename)

    return updated

# ---------- Delete Today ----------
def delete_today_pick(today_str=None, repo=None, branch="main", filename="history.csv"):
    if today_str is None:
        today_str = datetime.today().strftime("%Y-%m-%d")

    history = load_history(repo, branch, filename)
    updated = history[history["Date"] != today_str].reset_index(drop=True)

    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(file.path, f"Delete today {today_str}", updated.to_csv(index=False), file.sha, branch=branch)
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
