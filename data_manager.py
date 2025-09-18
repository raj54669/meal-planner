import pandas as pd

MASTER_COLUMNS = ["Recipe", "Item Type", "Calories"]

def load_master_list(file_path="master_list.csv"):
    try:
        df = pd.read_csv(file_path)
        # Normalize column names
        df.columns = [col.strip().title().replace("_", " ") for col in df.columns]

        # Ensure all expected columns exist
        for col in MASTER_COLUMNS:
            if col not in df.columns:
                df[col] = None

        return df[MASTER_COLUMNS]
    except FileNotFoundError:
        return pd.DataFrame(columns=MASTER_COLUMNS)


def save_master_list(df, file_path="master_list.csv"):
    df.to_csv(file_path, index=False)
