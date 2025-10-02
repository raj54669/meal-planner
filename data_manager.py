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
    today = datetime.today().strftime("%Y-%m-%d")

    # Load history
    history = load_history(repo, branch, filename).copy()
    if history.empty:
        history = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

    # Ensure Date column is datetime
    if "Date" in history.columns:
        history["Date"] = pd.to_datetime(history["Date"], errors="coerce")

    # Check existing entry for today
    today_rows = history[history["Date"].dt.strftime("%Y-%m-%d") == today]

    if not today_rows.empty:
        current_recipe = str(today_rows.iloc[0]["Recipe"]).strip()
        current_type = str(today_rows.iloc[0]["Item Type"]).strip()

        # Case 1: Same recipe → do nothing
        if current_recipe.lower() == recipe.strip().lower():
            st.info(f"ℹ️ {recipe} is already selected for today.")
            return history

        # Case 2: Different recipe → replace today's entry
        history = history[history["Date"].dt.strftime("%Y-%m-%d") != today]

    # Case 3: No entry yet, or replaced entry
    new_row = pd.DataFrame([{"Date": today, "Recipe": recipe.strip(), "Item Type": str(item_type).strip()}])
    updated = pd.concat([history, new_row], ignore_index=True)

    # Ensure Date stays datetime
    updated["Date"] = pd.to_datetime(updated["Date"], errors="coerce")

    # Save (GitHub or local)
    if repo:
        try:
            file = repo.get_contents(filename, ref=branch)
            repo.update_file(
                file.path,
                f"Update history {today}",
                updated.to_csv(index=False),
                file.sha,
                branch=branch
            )
        except Exception:
            try:
                repo.create_file(filename, f"Create history {today}", updated.to_csv(index=False), branch=branch)
            except Exception as e:
                st.error(f"❌ GitHub save failed: {e}")
    else:
        atomic_save(updated, filename)

    return updated

# ---------- Delete Today ----------
def delete_today_pick(today_str=None, repo=None, branch="main", filename="history.csv"):
    if today_str is None:
        today_str = datetime.today().strftime("%Y-%m-%d")

    history = load_history(repo, branch, filename).copy()
    if history.empty:
        return history  # nothing to delete

    # Ensure Date is datetime
    if "Date" in history.columns:
        history["Date"] = pd.to_datetime(history["Date"], errors="coerce")

    # Filter out today's rows
    updated = history[history["Date"].dt.strftime("%Y-%m-%d") != today_str].reset_index(drop=True)

    # If no change, just return history silently
    if len(updated) == len(history):
        return history

    # Save back only if something was removed
    if repo:
        file = repo.get_contents(filename, ref=branch)
        repo.update_file(
            file.path,
            f"Delete today {today_str}",
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
