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
        # File missing → return empty structure
        return pd.DataFrame(columns=["Recipe", "Item Type"])

# ---------- Load History ----------
def load_history(repo, branch="main"):
    try:
        file = repo.get_contents("history.csv", ref=branch)
        return pd.read_csv(StringIO(file.decoded_content.decode()))
    except Exception:
        # File missing → return empty structure
        return pd.DataFrame(columns=["Date", "Recipe", "Item Type"])

# ---------- Save Today’s Pick ----------
def save_today_pick(recipe, item_type, repo, branch="main"):
    today = datetime.today().strftime("%d-%m-%Y")
    new_row = pd.DataFrame([{"Date": today, "Recipe": recipe, "Item Type": item_type}])

    history = load_history(repo, branch)
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
def add_recipe_to_master(recipe, item_type, repo, branch="main"):
    master = load_master_list(repo, branch)
    updated = pd.concat([master, pd.DataFrame([{"Recipe": recipe, "Item Type": item_type}])], ignore_index=True)

    file = repo.get_contents("master_list.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        "Add recipe",
        updated.to_csv(index=False),
        file.sha,
        branch=branch
    )

# ---------- Delete Today ----------
def delete_today_pick(repo, branch="main"):
    today = datetime.today().strftime("%d-%m-%Y")
    history = load_history(repo, branch)
    updated = history[history["Date"] != today]

    file = repo.get_contents("history.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        f"Delete today {today}",
        updated.to_csv(index=False),
        file.sha,
        branch=branch
    )

# ---------- Save Master List ----------
def save_master_list(df, repo, branch="main"):
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
    file = repo.get_contents("history.csv", ref=branch)  # ❌ will raise if not found
    repo.update_file(
        file.path,
        "Update history",
        df.to_csv(index=False),
        file.sha,
        branch=branch
    )

# ---------- Get File SHA ----------
def get_file_sha(file_path, repo, branch="main"):
    try:
        contents = repo.get_contents(file_path, ref=branch)
        return contents.sha
    except Exception:
        return None
