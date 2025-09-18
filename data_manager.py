import pandas as pd
import os

MASTER_FILE = "master_list.csv"
HISTORY_FILE = "history.csv"

def load_master_list():
    if os.path.exists(MASTER_FILE):
        return pd.read_csv(MASTER_FILE)
    return pd.DataFrame(columns=["Recipe", "Item Type"])

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    return pd.DataFrame(columns=["Recipe", "Date"])

def save_today_pick(recipe):
    try:
        history_df = load_history()
        new_entry = {"Recipe": recipe, "Date": pd.Timestamp.today().strftime("%Y-%m-%d")}
        history_df = pd.concat([history_df, pd.DataFrame([new_entry])], ignore_index=True)
        history_df.to_csv(HISTORY_FILE, index=False)
        return True
    except Exception as e:
        print("Error saving history:", e)
        return False

def save_new_recipe(recipe, item_type):
    try:
        master_df = load_master_list()
        new_entry = {"Recipe": recipe, "Item Type": item_type}
        master_df = pd.concat([master_df, pd.DataFrame([new_entry])], ignore_index=True)
        master_df.to_csv(MASTER_FILE, index=False)
        return True
    except Exception as e:
        print("Error saving recipe:", e)
        return False
