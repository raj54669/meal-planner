# data_manager.py
import pandas as pd
from datetime import datetime
from io import StringIO

# ---------- Load Master ----------
def load_master_list(repo, branch="main"):
    try:
        file = repo.get_contents("master_list.csv", ref=branch)
        return pd.read_csv(StringIO(file.decoded_content.decode()))
    except Exception:
        return pd.DataFrame(columns=["Recipe", "Item Type"])

# ---------- Load History ----------
def load_history(repo, branch="main"):
    try:
        file = repo.get_contents("history.csv", ref=branch)
        return pd.read_csv(StringIO(file.decoded_content.decode()))
    except Exception:
        return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, item_type, repo=None, branch="main", use_github=False):
    today = datetime.today().strftime("%d-%m-%Y")
    new_row = pd.DataFrame([{"Date": today, "Recipe": recipe, "Item Type": item_type}])

    history = load_history(repo, branch, use_github)
    updated = pd.concat([history, new_row], ignore_index=True)

    if use_github:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(
            file.path,
            f"Update history {today}",
            updated.to_csv(index=False),
            file.sha,
            branch=branch
        )
    else:
        updated.to_csv("history.csv", index=False)
        
# ---------- Add to Master ----------
def add_recipe_to_master(recipe, item_type, repo, branch="main"):
    master = load_master_list(repo, branch)
    updated = pd.concat([master, pd.DataFrame([{"Recipe": recipe, "Item Type": item_type}])], ignore_index=True)

    try:
        file = repo.get_contents("master_list.csv", ref=branch)
        repo.update_file(file.path, "Add recipe", updated.to_csv(index=False), file.sha, branch=branch)
    except Exception:
        repo.create_file("master_list.csv", "Create master list", updated.to_csv(index=False), branch=branch)

# ---------- Delete Today ----------
def delete_today_pick(date_str, repo, branch="main"):
    history = load_history(repo, branch)
    updated = history[history["Date"] != date_str]

    try:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, f"Delete {date_str}", updated.to_csv(index=False), file.sha, branch=branch)
    except Exception:
        repo.create_file("history.csv", "Create history", updated.to_csv(index=False), branch=branch)

# ---------- Save Master List ----------
def save_master_list(df, repo, branch="main"):
    try:
        file = repo.get_contents("master_list.csv", ref=branch)
        repo.update_file(file.path, "Update master list", df.to_csv(index=False), file.sha, branch=branch)
    except Exception:
        repo.create_file("master_list.csv", "Create master list", df.to_csv(index=False), branch=branch)

# ---------- Save History ----------
def save_history(df, repo, branch="main"):
    try:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, "Update history", df.to_csv(index=False), file.sha, branch=branch)
    except Exception:
        repo.create_file("history.csv", "Create history", df.to_csv(index=False), branch=branch)

# ---------- Get File SHA ----------
def get_file_sha(file_path, repo, branch="main"):
    try:
        contents = repo.get_contents(file_path, ref=branch)
        return contents.sha
    except Exception:
        return None
