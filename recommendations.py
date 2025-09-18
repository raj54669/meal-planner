import pandas as pd

def get_today_suggestions(master_list, history, top_n=5):
    """
    Suggest recipes that haven't been eaten recently.
    Returns dataframe with columns: Recipe, Item Type, Last Eaten, Days Ago
    """
    df = master_list.copy()

    # Last eaten info from history
    last_eaten = history.groupby("Recipe")["Date"].max().reset_index()
    df = df.merge(last_eaten, on="Recipe", how="left").rename(columns={"Date": "Last Eaten"})

    # Calculate "Days Ago"
    df["Days Ago"] = df["Last Eaten"].apply(
        lambda x: (pd.Timestamp.today() - pd.to_datetime(x)).days
        if pd.notnull(x) else None
    )

    # Sort: most days ago first (or never eaten = highest priority)
    df = df.sort_values(by=["Days Ago"], ascending=[False], na_position="first")

    # Pick top N
    suggestions = df.head(top_n).reset_index(drop=True)

    return suggestions
