import pandas as pd
from datetime import datetime
from io import StringIO

# ---------- Load Master ----------
def load_master_list(repo=None, branch="main", use_github=False):
    try:
        if use_github:
            file = repo.get_contents("master_list.csv", ref=branch)
            return pd.read_csv(StringIO(file.decoded_content.decode()))
        else:
            return pd.read_csv("master_list.csv")
    except Exception:
        return pd.DataFrame(columns=["Recipe", "Item Type"])

# ---------- Load History ----------
def load_history(repo=None, branch="main", use_github=False):
    try:
        if use_github:
            file = repo.get_contents("history.csv", ref=branch)
            return pd.read_csv(StringIO(file.decoded_content.decode()))
        else:
            return pd.read_csv("history.csv")
    except Exception:
        return pd.DataFrame(columns=["Date", "Recipe"])

# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, repo=None, branch="main", use_github=False):
    today = datetime.today().strftime("%d-%m-%Y")
    new_row = pd.DataFrame([{"Date": today, "Recipe": recipe}])

    history = load_history(repo, branch, use_github)
    updated = pd.concat([history, new_row], ignore_index=True)

    if use_github:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, f"Update history {today}", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        updated.to_csv("history.csv", index=False)

# ---------- Add to Master ----------
def add_recipe_to_master(recipe, item_type, repo=None, branch="main", use_github=False):
    new_row = pd.DataFrame([{"Recipe": recipe, "Item Type": item_type}])

    master = load_master_list(repo, branch, use_github)
    updated = pd.concat([master, new_row], ignore_index=True)

    if use_github:
        file = repo.get_contents("master_list.csv", ref=branch)
        repo.update_file(file.path, "Add recipe", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        updated.to_csv("master_list.csv", index=False)

# ---------- Delete Today ----------
def delete_today_pick(repo=None, branch="main", use_github=False):
    today = datetime.today().strftime("%d-%m-%Y")
    history = load_history(repo, branch, use_github)
    updated = history[history["Date"] != today]

    if use_github:
        file = repo.get_contents("history.csv", ref=branch)
        repo.update_file(file.path, f"Delete today {today}", updated.to_csv(index=False), file.sha, branch=branch)
    else:
        updated.to_csv("history.csv", index=False)
