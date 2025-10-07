# recommendations.py
import pandas as pd
import random
from datetime import date

def recommend(master_df: pd.DataFrame, history_df: pd.DataFrame, min_count: int = 5, max_count: int = 7) -> pd.DataFrame:
    """
    Simple recommendation engine:
    - excludes recipes eaten in last 7 days
    - tries to avoid repeating same Item Type as last day (if known)
    - sorts by days-ago (descending) and breaks ties randomly
    - returns between min_count and max_count rows (if available)
    """
    if master_df is None or master_df.empty:
        return pd.DataFrame()

    # compute last eaten per recipe
    last_dates = {}
    if history_df is not None and not history_df.empty and "Date" in history_df.columns:
        hist = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
        last_dates = hist.groupby("Recipe")["Date"].first().to_dict()

    # build candidate df
    candidates = master_df.copy()
    candidates["Last Eaten"] = candidates["Recipe"].map(lambda r: last_dates.get(r))
    today = date.today()

    def compute_days(d):
        try:
            if pd.isna(d):
                return pd.NA
            dt = pd.to_datetime(d, errors="coerce")
            if pd.isna(dt):
                return pd.NA
            return int((today - dt.date()).days)
        except Exception:
            return pd.NA

    candidates["Days Ago"] = candidates["Last Eaten"].apply(compute_days)

    # convert Days Ago to numeric for safe comparisons
    candidates["DaysAgo_num"] = pd.to_numeric(candidates["Days Ago"], errors="coerce")

    # filter out eaten in last 7 days: keep rows where DaysAgo_num is NaN (never eaten) or >= 7
    candidates = candidates[(candidates["DaysAgo_num"].isna()) | (candidates["DaysAgo_num"] >= 7)].copy()

    # avoid same item type as last saved day if possible
    last_item_type = None
    if history_df is not None and not history_df.empty and "Item Type" in history_df.columns:
        hist = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
        if not hist.empty:
            last_item_type = hist.iloc[0].get("Item Type")

    # scoring: larger Days Ago => higher priority; NA treated as "never eaten" and given high score
    def score_row(r):
        da = r.get("DaysAgo_num")
        if pd.isna(da):
            return 9999 + random.random()
        return float(da) + random.random() * 0.01

    candidates["score"] = candidates.apply(score_row, axis=1)

    # sort by score desc
    candidates = candidates.sort_values("score", ascending=False).reset_index(drop=True)

    # --- Probabilistic item-type skipping logic ---
    skip_same_type_prob = 0.7  # 70% chance to skip same type as last day

    picks = []
    picked_recipes = set()
    picked_types = []

    for _, row in candidates.iterrows():
        if len(picks) >= max_count:
            break
        recipe_name = row.get("Recipe")
        itype = row.get("Item Type")

        # For the very first pick, try (probabilistically) to avoid yesterday’s item type
        if last_item_type and len(picks) == 0 and itype == last_item_type:
            if random.random() < skip_same_type_prob:
                continue

        # Within the same recommendation batch, try to avoid consecutive same types
        if picked_types and itype == picked_types[-1] and random.random() < 0.5:
            continue

        if recipe_name in picked_recipes:
            continue

        picks.append(row)
        picked_recipes.add(recipe_name)
        picked_types.append(itype)

    # Fill up to min_count if needed (ignoring item-type constraints)
    if len(picks) < min_count:
        for _, row in candidates.iterrows():
            if len(picks) >= min_count:
                break
            recipe_name = row.get("Recipe")
            if recipe_name in picked_recipes:
                continue
            picks.append(row)
            picked_recipes.add(recipe_name)
            picked_types.append(row.get("Item Type"))

    # if fewer than min_count, fill with top candidates ignoring item-type constraints
    if len(picks) < min_count:
        for _, row in candidates.iterrows():
            # compare by unique index (picks contains Series objects); use Recipe name to decide uniqueness
            recipe_name = row.get("Recipe")
            if any(p.get("Recipe") == recipe_name for p in picks):
                continue
            picks.append(row)
            if len(picks) >= min_count:
                break

    if not picks:
        return pd.DataFrame()

    rec_df = pd.DataFrame(picks)
    if "score" in rec_df.columns:
        rec_df = rec_df.drop(columns=["score"])
    if "DaysAgo_num" in rec_df.columns:
        rec_df = rec_df.drop(columns=["DaysAgo_num"])
    return rec_df.reset_index(drop=True)
