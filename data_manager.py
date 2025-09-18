import pandas as pd
from datetime import datetime

MASTER_FILE = "master_list.csv"
HISTORY_FILE = "history.csv"

# -------------------------
# Load Master List
# -------------------------
def load_master_list():
    try:
        return pd.read_csv(MASTER_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Recipe", "Item Type"])

# -------------------------
# Load History
# -------------------------
def load_history():
    try:
        return pd.read_csv(HISTORY_FILE)
    except FileNotFoundError:
        return pd.DataFrame(columns=["Date", "Recipe"])

# -------------------------
# Save Today's Pick
# -------------------------
def save_today_pick(recipe, history_df):
    today = datetime.today().strftime("%d-%m-%Y")

    # if already picked today → replace
    if not history_df.empty and today in history_df["Date"].values:
        history_df.loc[history_df["Date"] == today, "Recipe"] = recipe
    else:
        new_row = pd.DataFrame([{"Date": today, "Recipe": recipe}])
        history_df = pd.concat([history_df, new_row], ignore_index=True)

    history_df.to_csv(HISTORY_FILE, index=False)
    return history_df
