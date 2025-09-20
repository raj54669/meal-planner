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
            dt = pd.to_datetime(d).date()
            return (today - dt).days
        except Exception:
            return None
    candidates["Days Ago"] = candidates["Last Eaten"].apply(compute_days)

    # filter out eaten in last 7 days
    candidates = candidates[~candidates["Days Ago"].apply(lambda x: pd.notna(x) and x < 7)]
    
    # avoid same item type as last saved day if possible
    last_item_type = None
    if history_df is not None and not history_df.empty and "Item Type" in history_df.columns:
        hist = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
        if not hist.empty:
            last_item_type = hist.iloc[0].get("Item Type")

    # scoring: larger Days Ago => higher priority; None treated as -1 to push down (or up? treat None as very large to give priority)
    def score_row(r):
        da = r["Days Ago"]
        if da is None:
            # never eaten: give a high score
            return 9999 + random.random()
        return float(da) + random.random() * 0.01

    candidates["score"] = candidates.apply(score_row, axis=1)

    # sort by score desc
    candidates = candidates.sort_values("score", ascending=False).reset_index(drop=True)

    # try to pick a set that respects the no same-item-type-consecutive rule
    # simple greedy: pick top until reach max_count, but skip a recipe if it would make two consecutive same item types with previous picked
    picks = []
    picked_types = []
    for _, row in candidates.iterrows():
        if len(picks) >= max_count:
            break
        itype = row.get("Item Type")
        # if first pick, avoid last_item_type if possible
        if last_item_type and len(picks) == 0 and itype == last_item_type:
            # skip if there exists other candidate not equal
            others = candidates[candidates["Item Type"] != last_item_type]
            if not others.empty:
                continue
        # avoid consecutive within picks
        if picked_types and itype == picked_types[-1]:
            # try skipping if others exist
            continue
        picks.append(row)
        picked_types.append(itype)

    # if fewer than min_count, fill with top candidates ignoring item-type constraints
    if len(picks) < min_count:
        extra_needed = min_count - len(picks)
        for _, row in candidates.iterrows():
            if any(row.equals(p) for p in picks):
                continue
            picks.append(row)
            if len(picks) >= min_count:
                break

    if not picks:
        return pd.DataFrame()

    rec_df = pd.DataFrame(picks)
    # drop helper score col
    if "score" in rec_df.columns:
        rec_df = rec_df.drop(columns=["score"])
    return rec_df.reset_index(drop=True)
