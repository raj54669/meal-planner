import pandas as pd
from datetime import datetime
from io import StringIO
import hashlib
import os

# ---------- Load Master ----------
def load_master_list(repo, branch="main", use_github=True):
    """
    Load master_list.csv from GitHub.
    Always returns DataFrame with columns [Recipe, Item Type].
    """
    try:
        file = repo.get_contents("master_list.csv", ref=branch)
        df = pd.read_csv(StringIO(file.decoded_content.decode()))
        if "Recipe" not in df.columns:
            df["Recipe"] = None
        if "Item Type" not in df.columns:
            df["Item Type"] = None
        return df
    except Exception as e:
        raise FileNotFoundError(f"Failed to load master_list.csv: {e}")

# ---------- Load History ----------
def load_history(repo, branch="main", use_github=True):
    """
    Load history.csv from GitHub.
    Always returns DataFrame with columns [Date, Recipe, Item Type].
    """
    try:
        file = repo.get_contents("history.csv", ref=branch)
        df = pd.read_csv(StringIO(file.decoded_content.decode()))
        if "Date" not in df.columns:
            df["Date"] = None
        if "Recipe" not in df.columns:
            df["Recipe"] = None
        if "Item Type" not in df.columns:
            df["Item Type"] = None
        return df
    except Exception as e:
        raise FileNotFoundError(f"Failed to load history.csv: {e}")

# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, repo, branch="main", use_github=True):
    """
    Append today's pick (Date, Recipe, Item Type) to history.csv in GitHub.
    """
    today = datetime.today().strftime("%d-%m-%Y")

    # Lookup Item Type from master
    master = load_master_list(repo, branch, use_github=True)
    item_type = master.loc[master["Recipe"] == recipe, "Item Type"].values
    item_type = item_type[0] if len(item_type) > 0 else None

    new_row = pd.DataFrame([{"Date": today, "Recipe": recipe, "Item Type": item_type}])

    history = load_history(repo, branch, use_github=True)
    updated = pd.concat([history, new_row], ignore_index=True)

    file = repo.get_contents("history.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        f"Update history {today}",
        updated.to_csv(index=False),
        file.sha,
        branch=branch
    )

# ---------- Add to Master ----------
def add_recipe_to_master(recipe, item_type, repo, branch="main", use_github=True):
    """
    Add a recipe to master_list.csv in GitHub.
    """
    new_row = pd.DataFrame([{"Recipe": recipe, "Item Type": item_type}])

    master = load_master_list(repo, branch, use_github=True)
    updated = pd.concat([master, new_row], ignore_index=True)

    file = repo.get_contents("master_list.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        "Add recipe",
        updated.to_csv(index=False),
        file.sha,
        branch=branch
    )

# ---------- Delete Today ----------
def delete_today_pick(repo, branch="main", use_github=True):
    """
    Delete today's pick from history.csv in GitHub.
    """
    today = datetime.today().strftime("%d-%m-%Y")
    history = load_history(repo, branch, use_github=True)
    updated = history[history["Date"] != today]

    file = repo.get_contents("history.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        f"Delete today {today}",
        updated.to_csv(index=False),
        file.sha,
        branch=branch
    )

# ---------- Utility: Get File SHA ----------
def get_file_sha(filepath: str) -> str:
    """
    Return SHA1 hash of a local file for change tracking,
    or None if file doesn't exist.
    """
    if not os.path.exists(filepath):
        return None
    sha1 = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()

# ---------- Save Master List ----------
def save_master_list(df, repo, branch="main"):
    """
    Save the master list DataFrame to GitHub.
    If master_list.csv does not exist, raise an error.
    """
    file = repo.get_contents("master_list.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        "Update master list",
        df.to_csv(index=False),
        file.sha,
        branch=branch
    )

# ---------- Save History ----------
def save_history(df, repo, branch="main"):
    """
    Save the history DataFrame to GitHub.
    If history.csv does not exist, raise an error.
    """
    file = repo.get_contents("history.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        "Update history",
        df.to_csv(index=False),
        file.sha,
        branch=branch
    )
