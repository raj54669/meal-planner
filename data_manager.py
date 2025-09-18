# -----------------------------
# FILE: data_manager.py
# -----------------------------
import requests
import base64
import pandas as pd
from io import StringIO


def _github_get_file(repo, path, token, branch="main"):
    url = f"https://api.github.com/repos/{repo}/contents/{path}?ref={branch}"
    headers = {
        "Accept": "application/vnd.github+json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        payload = r.json()
        content = base64.b64decode(payload["content"]) if payload.get("content") else b""
        sha = payload.get("sha")
        return content, sha
    elif r.status_code == 404:
        # file not found
        return None, None
    else:
        r.raise_for_status()


def _github_put_file(repo, path, token, content_bytes, message="update file", sha=None, branch="main"):
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(url, json=payload, headers=headers, timeout=15)
    if r.status_code in (200, 201):
        return r.json()["content"]["sha"]
    else:
        # raise for caller to display friendly error
        r.raise_for_status()


def load_master_list(repo=None, token=None, path="master_list.csv", branch="main"):
    if repo and token:
        try:
            content, sha = _github_get_file(repo, path, token, branch=branch)
            if content is None:
                # no file in repo
                return pd.DataFrame(columns=["Recipe", "Item Type"]), None
            s = content.decode("utf-8")
            df = pd.read_csv(StringIO(s))
            return df, sha
        except Exception:
            raise
    else:
        # local fallback handled by caller
        raise RuntimeError("GitHub not configured")


def load_history(repo=None, token=None, path="history.csv", branch="main"):
    if repo and token:
        try:
            content, sha = _github_get_file(repo, path, token, branch=branch)
            if content is None:
                return pd.DataFrame(columns=["Date", "Recipe", "Item Type"]), None
            s = content.decode("utf-8")
            df = pd.read_csv(StringIO(s), parse_dates=["Date"]) if s.strip() else pd.DataFrame(columns=["Date", "Recipe", "Item Type"])
            return df, sha
        except Exception:
            raise
    else:
        raise RuntimeError("GitHub not configured")


def save_master_list(df, repo=None, token=None, path="master_list.csv", sha=None, message=None, branch="main"):
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    if repo and token:
        msg = message or "Update master_list.csv via Streamlit app"
        try:
            new_sha = _github_put_file(repo, path, token, csv_bytes, message=msg, sha=sha, branch=branch)
            return True, new_sha
        except Exception as e:
            # bubble up error
            raise
    else:
        # local fallback
        df.to_csv(path, index=False)
        return False, None


def save_history(df, repo=None, token=None, path="history.csv", sha=None, message=None, branch="main"):
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    if repo and token:
        msg = message or "Update history.csv via Streamlit app"
        try:
            new_sha = _github_put_file(repo, path, token, csv_bytes, message=msg, sha=sha, branch=branch)
            return True, new_sha
        except Exception as e:
            raise
    else:
        df.to_csv(path, index=False)
        return False, None


