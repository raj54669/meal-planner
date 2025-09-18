# recommendations.py
from datetime import datetime, timedelta
import pandas as pd
import random

def days_ago_from_date(d):
    if pd.isna(d):
        return None
    if isinstance(d, str):
        try:
            d = pd.to_datetime(d)
        except Exception:
            return None
    if isinstance(d, pd.Timestamp):
        dd = d.date()
    elif isinstance(d, datetime):
        dd = d.date()
    elif isinstance(d, (int, float)):
        return None
    else:
        try:
            dd = d
        except Exception:
            return None
    return (datetime.today().date() - dd).days

def recommend(master_df, history_df, min_count=5, max_count=7):
    """
    Return DataFrame of recommendations with columns: Recipe, Item Type, Last Eaten (date or None), Days Ago (int or large)
    """
    mf = master_df.copy()
    if mf.empty:
        return mf

    # last eaten map
    last_dates = {}
    if history_df is not None and not history_df.empty:
        hist_clean = history_df.dropna(subset=["Date", "Recipe"]).copy()
        hist_clean["Date"] = pd.to_datetime(hist_clean["Date"], errors="coerce")
        # get most recent date per recipe
        last_dates = hist_clean.groupby("Recipe")["Date"].max().to_dict()

    # yesterday's item type
    last_item_type = None
    if history_df is not None and not history_df.empty:
        # get most recent by Date
        hr = history_df.dropna(subset=["Date"]).copy()
        if not hr.empty:
            most_recent = hr.sort_values("Date", ascending=False).iloc[0]
            last_item_type = most_recent.get("Item Type")

    rows = []
    for _, r in mf.iterrows():
        recipe = r.get("Recipe")
        item = r.get("Item Type")
        last = last_dates.get(recipe)
        days_ago = days_ago_from_date(last)
        if days_ago is None:
            # never eaten -> give large number to prioritize
            days_ago_val = 99999
        else:
            days_ago_val = int(days_ago)
        rows.append({"Recipe": recipe, "Item Type": item, "Last Eaten": last, "Days Ago": days_ago_val})

    rec_df = pd.DataFrame(rows)

    # Rule: remove those eaten within 7 days
    rec_df = rec_df[rec_df["Days Ago"] > 7]

    # Rule: remove same item type as yesterday
    if last_item_type:
        rec_df = rec_df[rec_df["Item Type"] != last_item_type]

    # If too few after strict rules, relax rules STEPWISE until min_count achieved
    if len(rec_df) < min_count:
        # try relaxing item-type constraint
        rec_df_relax1 = pd.DataFrame(rows)
        rec_df_relax1 = rec_df_relax1[rec_df_relax1["Days Ago"] > 7]
        if len(rec_df_relax1) >= min_count:
            rec_df = rec_df_relax1
        else:
            # relax 7-day constraint but keep item-type filter
            rec_df_relax2 = pd.DataFrame(rows)
            if last_item_type:
                rec_df_relax2 = rec_df_relax2[rec_df_relax2["Item Type"] != last_item_type]
            if len(rec_df_relax2) >= min_count:
                rec_df = rec_df_relax2
            else:
                # fallback to all recipes
                rec_df = pd.DataFrame(rows)

    # Sort by Days Ago descending (largest days_ago first = not eaten longest)
    rec_df = rec_df.sort_values("Days Ago", ascending=False)

    # For ties (same Days Ago) randomize internal order
    grouped = []
    for days, group in rec_df.groupby("Days Ago"):
        grp = group.sample(frac=1, random_state=random.randint(0, 9999)).to_dict("records")
        grouped.extend(grp)

    out = pd.DataFrame(grouped)
    # Take 5-7: ensure at least min_count if available
    final = out.head(min(max_count, len(out)))
    if len(final) < min_count:
        # if still less, try to add additional items from master (never-eaten included earlier)
        extra_candidates = [r for r in out.to_dict("records")]
        final = pd.DataFrame(extra_candidates).head(min_count)

    return final.reset_index(drop=True)
