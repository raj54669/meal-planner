# data_manager.py
import pandas as pd
from datetime import datetime
from io import StringIO
import os

# ---------- Load Master ----------
def load_master_list(repo=None, branch="main"):
    """
    Load master_list.csv either from a GitHub repo (repo: PyGithub Repo object)
    or from the local file if repo is None (fallback).
    Returns a DataFrame.
    """
    if repo is not None:
        try:
            file = repo.get_contents("master_list.csv", ref=branch)
            text = file.decoded_content.decode()
            return pd.read_csv(StringIO(text))
        except Exception:
            # return empty frame with expected columns
            return pd.DataFrame(columns=["Recipe", "Item Type"])
    else:
        # local fallback (read if exists)
        if os.path.exists("master_list.csv"):
            try:
                return pd.read_csv("master_list.csv")
            except Exception:
                return pd.DataFrame(columns=["Recipe", "Item Type"])
        return pd.DataFrame(columns=["Recipe", "Item Type"])


# ---------- Load History ----------
def load_history(repo=None, branch="main"):
    """
    Load history.csv from GitHub repo or local file. Parse Date column to datetime.
    """
    if repo is not None:
        try:
            file = repo.get_contents("history.csv", ref=branch)
            text = file.decoded_content.decode()
            # parse dates while reading
            return pd.read_csv(StringIO(text), parse_dates=["Date"])
        except Exception:
            return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    else:
        if os.path.exists("history.csv"):
            try:
                return pd.read_csv("history.csv", parse_dates=["Date"])
            except Exception:
                return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
        return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])


# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, item_type="", repo=None, branch="main"):
    """
    Append today's pick to history and save via repo.create_file/update_file.
    Date saved in ISO format YYYY-MM-DD (easy to parse).
    """
    if repo is None:
        raise RuntimeError("GitHub repo not provided to save_today_pick.")

    today_iso = datetime.today().strftime("%Y-%m-%d")
    new_row = pd.DataFrame([{"Date": today_iso, "Recipe": recipe, "Item Type": item_type}])

    history = load_history(repo, branch)
    updated = pd.concat([history, new_row], ignore_index=True)

    content = updated.to_csv(index=False)
    try:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, f"Update history {today_iso}", content, file.sha, branch=branch)
    except Exception:
        # create if not exists
        repo.create_file("history.csv", f"Create history {today_iso}", content, branch=branch)


# ---------- Add to Master ----------
def add_recipe_to_master(recipe, item_type, repo=None, branch="main"):
    """
    Add a recipe to master_list and update/create file in repo.
    """
    if repo is None:
        raise RuntimeError("GitHub repo not provided to add_recipe_to_master.")

    master = load_master_list(repo, branch)
    updated = pd.concat([master, pd.DataFrame([{"Recipe": recipe, "Item Type": item_type}])], ignore_index=True)

    content = updated.to_csv(index=False)
    try:
        file = repo.get_contents("master_list.csv", ref=branch)
        repo.update_file(file.path, "Add recipe", content, file.sha, branch=branch)
    except Exception:
        repo.create_file("master_list.csv", "Create master list", content, branch=branch)


# ---------- Delete Today ----------
def delete_today_pick(date_str, repo=None, branch="main"):
    """
    Remove rows with Date == date_str (date_str should match saved format, e.g. '2025-09-19').
    """
    if repo is None:
        raise RuntimeError("GitHub repo not provided to delete_today_pick.")

    history = load_history(repo, branch)
    # ensure Date column is datetime; compare strings as ISO if necessary
    try:
        # If Date is datetime-type, compare to parsed date_str
        history["Date"] = pd.to_datetime(history["Date"], errors="coerce")
        parsed = pd.to_datetime(date_str, errors="coerce")
        if pd.notna(parsed):
            updated = history[history["Date"] != parsed]
        else:
            updated = history[history["Date"].astype(str) != date_str]
    except Exception:
        updated = history[history["Date"].astype(str) != date_str]

    content = updated.to_csv(index=False)
    try:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, f"Delete {date_str}", content, file.sha, branch=branch)
    except Exception:
        repo.create_file("history.csv", f"Create history remove {date_str}", content, branch=branch)


# ---------- Save Master List ----------
def save_master_list(df, repo=None, branch="main", sha=None):
    """
    Save the master list DataFrame to GitHub (update or create).
    """
    if repo is None:
        raise RuntimeError("GitHub repo not provided to save_master_list.")

    content = df.to_csv(index=False)
    try:
        if sha is None:
            file = repo.get_contents("master_list.csv", ref=branch)
            sha = file.sha
        repo.update_file("master_list.csv", "Update master list", content, sha, branch=branch)
    except Exception:
        repo.create_file("master_list.csv", "Create master list", content, branch=branch)


# ---------- Save History ----------
def save_history(df, repo=None, branch="main", sha=None):
    """
    Save history DataFrame to GitHub (update or create).
    """
    if repo is None:
        raise RuntimeError("GitHub repo not provided to save_history.")

    content = df.to_csv(index=False)
    try:
        if sha is None:
            file = repo.get_contents("history.csv", ref=branch)
            sha = file.sha
        repo.update_file("history.csv", "Update history", content, sha, branch=branch)
    except Exception:
        repo.create_file("history.csv", "Create history", content, branch=branch)



# ---------- Utility: Get File SHA ----------
def get_file_sha(filepath: str, repo=None, branch="main"):
    """
    Return the file sha from GitHub if repo provided; otherwise fallback to local sha1.
    """
    if repo is not None:
        try:
            contents = repo.get_contents(filepath, ref=branch)
            return contents.sha
        except Exception:
            return None
    # local fallback
    if not os.path.exists(filepath):
        return None
    import hashlib
    sha1 = hashlib.sha1()
    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            sha1.update(chunk)
    return sha1.hexdigest()
