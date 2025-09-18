# data_manager.py
import base64
import requests
import pandas as pd
import io
import os
from typing import Tuple

# Filenames when using local fallback
MASTER_FN = "master_list.csv"
HISTORY_FN = "history.csv"

# ---------- GitHub helpers ----------
def _gh_get_file(repo: str, path: str, token: str, branch: str = "main"):
    """
    Returns (content_bytes, sha) or raises Exception on failure.
    """
    api = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    headers = {"Authorization": f"token {token}"}
    r = requests.get(api, headers=headers, timeout=15)
    if r.status_code in (200,):
        j = r.json()
        content = base64.b64decode(j["content"])
        return content, j["sha"]
    else:
        raise Exception(f"GitHub GET failed: {r.status_code} {r.text}")

def _gh_put_file(repo: str, path: str, token: str, content_bytes: bytes, message: str, branch: str="main", sha: str=None):
    """
    Create or update file. Returns (ok_bool, new_sha_str)
    """
    api = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Authorization": f"token {token}"}
    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
    body = {
        "message": message,
        "content": content_b64,
        "branch": branch
    }
    if sha:
        body["sha"] = sha
    r = requests.put(api, json=body, headers=headers, timeout=20)
    if r.status_code in (200, 201):
        j = r.json()
        return True, j["content"]["sha"]
    else:
        # return False and full response text for debugging
        raise Exception(f"GitHub PUT failed: {r.status_code} {r.text}")

# ---------- Public functions ----------
def load_master_list(repo: str = None, token: str = None, branch: str="main") -> Tuple[pd.DataFrame, str]:
    """
    Returns (master_df, sha) when using GitHub; or raises exception (so caller can fallback to local).
    """
    if repo and token:
        # try GitHub
        content, sha = _gh_get_file(repo, MASTER_FN, token, branch=branch)
        df = pd.read_csv(io.BytesIO(content))
        return df, sha
    else:
        raise Exception("GitHub not configured")

def save_master_list(df: pd.DataFrame, repo: str = None, token: str = None, branch: str="main", sha: str=None) -> Tuple[bool, str]:
    """
    Save master list. If GitHub configured attempts to push. Returns (ok, new_sha).
    If GitHub not configured returns (False, None) after writing local file.
    """
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    if repo and token:
        new_sha = None
        ok, new_sha = _gh_put_file(repo, MASTER_FN, token, csv_bytes, message="Update master_list.csv", branch=branch, sha=sha)
        return ok, new_sha
    else:
        # fallback write
        df.to_csv(MASTER_FN, index=False)
        return False, None

def load_history(repo: str = None, token: str = None, branch: str="main") -> Tuple[pd.DataFrame, str]:
    if repo and token:
        content, sha = _gh_get_file(repo, HISTORY_FN, token, branch=branch)
        df = pd.read_csv(io.BytesIO(content), parse_dates=["Date"], dayfirst=False)
        return df, sha
    else:
        raise Exception("GitHub not configured")

def save_history(df: pd.DataFrame, repo: str = None, token: str = None, branch: str="main", sha: str=None) -> Tuple[bool, str]:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    if repo and token:
        ok, new_sha = _gh_put_file(repo, HISTORY_FN, token, csv_bytes, message="Update history.csv", branch=branch, sha=sha)
        return ok, new_sha
    else:
        df.to_csv(HISTORY_FN, index=False)
        return False, None
