# -----------------------------
# FILE: recommendations.py
# -----------------------------
import pandas as pd
import random
from datetime import date


def recommend(master_df, history_df, min_count=5, max_count=7):
    # Return a DataFrame with columns: Recipe, Item Type, Last Eaten (datetime or NaT), Days Ago
    if master_df is None or master_df.empty:
        return pd.DataFrame()

    # compute last eaten per recipe
    last_eaten = {}
    if history_df is not None and not history_df.empty:
        hist = history_df.dropna(subset=["Date"]).sort_values("Date", ascending=False)
        last_eaten = hist.groupby("Recipe")["Date"].first().to_dict()

    candidates = master_df.copy()
    candidates["Last Eaten"] = candidates["Recipe"].map(lambda r: last_eaten.get(r))
    candidates["Days Ago"] = candidates["Last Eaten"].apply(lambda d: (date.today() - pd.to_datetime(d).date()).days if pd.notna(d) else None)

    # filter out recipes eaten within last 7 days
    filtered = candidates[candidates["Days Ago"].isna() | (candidates["Days Ago"] >= 7)].copy()

    if filtered.empty:
        # relax rule: allow ones older than 0 days
        filtered = candidates.copy()

    # sort by Days Ago desc (not eaten longest first). For NaN (never eaten) treat as large number
    def key_func(row):
        if pd.isna(row["Days Ago"]):
            return 10**6
        return int(row["Days Ago"])

    shuffled = filtered.sample(frac=1, random_state=42)  # deterministic shuffle for tie-breaks
    sorted_cands = shuffled.sort_values("Days Ago", ascending=False, key=lambda col: col.fillna(10**6))

    # build recommendations avoiding same item type consecutively
    recs = []
    last_type = None
    for _, r in sorted_cands.iterrows():
        if len(recs) >= max_count:
            break
        if last_type is None or r["Item Type"] != last_type:
            recs.append(r)
            last_type = r["Item Type"]

    # If not enough, fill remaining without type rule
    if len(recs) < min_count:
        # fill from sorted list ignoring last_type
        for _, r in sorted_cands.iterrows():
            if r["Recipe"] in [x["Recipe"] for x in recs]:
                continue
            recs.append(r)
            if len(recs) >= min_count:
                break

    if not recs:
        return pd.DataFrame()

    out = pd.DataFrame(recs)
    # compute Days Ago numeric
    out["Days Ago"] = out["Days Ago"].apply(lambda x: int(x) if pd.notna(x) else pd.NA)
    return out.reset_index(drop=True)


