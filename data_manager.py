# data_manager.py
import os
import base64
import json
import requests
import pandas as pd
from io import StringIO

# Config read from env or Streamlit secrets (in app.py we will pass these)
GITHUB_API_BASE = "https://api.github.com"

def _get_headers(token):
    if not token:
        return {}
    return {"Authorization": f"token {token}"}

def _download_csv_from_github(repo, path, token, branch="main"):
    """Return (df, sha). If file missing, return (empty df, None)."""
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
    params = {"ref": branch}
    res = requests.get(url, headers=_get_headers(token), params=params)
    if res.status_code == 200:
        j = res.json()
        content = base64.b64decode(j["content"]).decode("utf-8")
        sha = j.get("sha")
        df = pd.read_csv(StringIO(content))
        return df, sha
    else:
        # file not found -> return empty df
        if res.status_code == 404:
            return pd.DataFrame(), None
        res.raise_for_status()

def _put_file_to_github(repo, path, token, content_str, sha=None, message="Update via NextBite", branch="main"):
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
    b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    payload = {"message": message, "content": b64, "branch": branch}
    if sha:
        payload["sha"] = sha
    res = requests.put(url, headers=_get_headers(token), data=json.dumps(payload))
    if res.status_code in (200, 201):
        return True
    else:
        # raise for debugging
        raise Exception(f"GitHub PUT failed: {res.status_code} {res.text}")

# Public API
def load_master_list(repo, token, path="master_list.csv", branch="main"):
    df, sha = _download_csv_from_github(repo, path, token, branch=branch)
    # normalize columns
    if not df.empty:
        df.columns = [c.strip() for c in df.columns]
        # Accept various column names: Recipe or recipe, Item Type or Type
        colmap = {}
        cols = [c.lower().replace(" ", "") for c in df.columns]
        if "recipe" not in [c.lower() for c in df.columns]:
            for c in df.columns:
                if c.lower() in ("name", "recipe_name"):
                    colmap[c] = "Recipe"
        if "item type" not in [c.lower() for c in df.columns]:
            for c in df.columns:
                if c.lower() in ("type", "itemtype"):
                    colmap[c] = "Item Type"
        if colmap:
            df = df.rename(columns=colmap)
    else:
        # empty df default columns
        df = pd.DataFrame(columns=["Recipe", "Item Type"])
    # ensure columns exist
    if "Recipe" not in df.columns:
        df["Recipe"] = ""
    if "Item Type" not in df.columns:
        df["Item Type"] = ""
    return df[["Recipe", "Item Type"]], sha

def save_master_list(df, repo, token, sha=None, path="master_list.csv", msg="Update master_list.csv", branch="main"):
    csv = df.to_csv(index=False)
    return _put_file_to_github(repo, path, token, csv, sha=sha, message=msg, branch=branch)

def load_history(repo, token, path="history.csv", branch="main"):
    df, sha = _download_csv_from_github(repo, path, token, branch=branch)
    if df.empty:
        df = pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
    else:
        # normalize
        df.columns = [c.strip() for c in df.columns]
        # try to parse Date
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        else:
            df["Date"] = pd.to_datetime(pd.Series([pd.NaT]*len(df)))
        if "Recipe" not in df.columns:
            df["Recipe"] = ""
        if "Item Type" not in df.columns:
            df["Item Type"] = ""
    return df[["Date", "Recipe", "Item Type"]], sha

def save_history(df, repo, token, sha=None, path="history.csv", msg="Update history.csv", branch="main"):
    # Ensure Date formatted ISO
    df_to_save = df.copy()
    if "Date" in df_to_save.columns:
        df_to_save["Date"] = pd.to_datetime(df_to_save["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
    csv = df_to_save.to_csv(index=False)
    return _put_file_to_github(repo, path, token, csv, sha=sha, message=msg, branch=branch)
