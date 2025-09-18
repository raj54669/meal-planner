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
