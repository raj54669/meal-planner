import pandas as pd
import os

MASTER_FILE = "master_list.csv"
HISTORY_FILE = "history.csv"

def load_master_list():
    if os.path.exists(MASTER_FILE):
        return pd.read_csv(MASTER_FILE)
    return pd.DataFrame(columns=["Recipe", "Item Type", "Calories"])

def save_master_list(df):
    df.to_csv(MASTER_FILE, index=False)

def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_csv(HISTORY_FILE)
    return pd.DataFrame(columns=["Recipe", "Date"])

def save_history(df):
    df.to_csv(HISTORY_FILE, index=False)
