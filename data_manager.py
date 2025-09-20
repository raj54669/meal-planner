import pandas as pd
from datetime import datetime
from io import StringIO
import hashlib
import os

# ---------- Load Master ----------
def load_master_list(repo=None, branch="main"):
    try:
        if repo:
            file = repo.get_contents("master_list.csv", ref=branch)
            return pd.read_csv(StringIO(file.decoded_content.decode()))
        else:
            return pd.read_csv("master_list.csv")
    except Exception:
        return pd.DataFrame(columns=["Recipe", "Item Type"])

# ---------- Load History ----------
def load_history(repo=None, branch="main"):
    try:
        if repo:
            file = repo.get_contents("history.csv", ref=branch)
            return pd.read_csv(StringIO(file.decoded_content.decode()))
        else:
            return pd.read_csv("history.csv")
    except Exception:
        return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, item_type="", repo=None, branch="main"):
    today = datetime.today().strftime("%Y-%m-%d")
    new_row = pd.DataFrame([{"Date": today, "Recipe": recipe, "Item Type": item_type}])

    history = load_history(repo, branch)
    updated = pd.concat([history, new_row], ignore_index=True)

    if repo:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, f"Update history {today}", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        updated.to_csv("history.csv", index=False)

    return updated

# ---------- Add to Master ----------
def add_recipe_to_master(recipe, item_type, repo=None, branch="main"):
    new_row = pd.DataFrame([{"Recipe": recipe, "Item Type": item_type}])

    master = load_master_list(repo, branch)
    updated = pd.concat([master, new_row], ignore_index=True)

    if repo:
        file = repo.get_contents("master_list.csv", ref=branch)
        repo.update_file(file.path, "Add recipe", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        updated.to_csv("master_list.csv", index=False)

    return updated

# ---------- Delete Today ----------
def delete_today_pick(today_str=None, repo=None, branch="main"):
    if today_str is None:
        today_str = datetime.today().strftime("%Y-%m-%d")

    history = load_history(repo, branch)
    updated = history[history["Date"] != today_str]

    if repo:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, f"Delete today {today_str}", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        updated.to_csv("history.csv", index=False)

    return updated

# ---------- Utility: Get File SHA ----------
def get_file_sha(filepath: str, repo=None, branch="main"):
    """
    Return SHA from GitHub if repo is given, else local SHA1 hash.
    """
    if repo:
        try:
            file = repo.get_contents(filepath, ref=branch)
            return file.sha
        except Exception:
            return None

    if not os.path.exists(filepath):
        return None
    sha1 = hashlib.sha1()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()

# ---------- Save Master List ----------
def save_master_list(df, repo=None, branch="main", sha=None):
    if repo:
        file = repo.get_contents("master_list.csv", ref=branch)
        repo.update_file(
            file.path,
            "Update master list",
            df.to_csv(index=False),
            file.sha if sha is None else sha,
            branch=branch
        )
    else:
        df.to_csv("master_list.csv", index=False)
    return df

# ---------- Save History ----------
def save_history(df, repo=None, branch="main", sha=None):
    if repo:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(
            file.path,
            "Update history",
            df.to_csv(index=False),
            file.sha if sha is None else sha,
            branch=branch
        )
    else:
        df.to_csv("history.csv", index=False)
    return df
