import pandas as pd

def format_table(df, show_item_type=False):
    df = df.copy()

    # Format Last Eaten date
    if 'Last Eaten' in df.columns:
        df['Last Eaten'] = df['Last Eaten'].apply(
            lambda x: pd.to_datetime(x).strftime("%d-%m-%Y") if pd.notnull(x) else "None"
        )

    # Reorder columns to show Item Type beside Recipe
    if show_item_type and "Item Type" in df.columns and "Recipe" in df.columns:
        cols = ["Recipe", "Item Type"] + [c for c in df.columns if c not in ["Recipe", "Item Type"]]
        df = df[cols]

    # Style adjustments
    return df.style.hide(axis="index") \
        .set_properties(subset=["Days Ago"], **{"text-align": "center", "width": "60px"})
