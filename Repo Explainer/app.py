import os
import re
import json
from urllib.parse import urlparse
from flask import Flask, request, render_template, jsonify
import requests
from analyzer import analyze_repo_tree

app = Flask(__name__)

GITHUB_API = "https://api.github.com"
# Optionally set GITHUB_TOKEN env var for higher rate limits & private repos
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

HEADERS = {"Accept": "application/vnd.github+json"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def parse_github_url(url):
    """
    Accepts typical GitHub repo URLs and returns (owner, repo, branch_or_default)
    Examples:
      https://github.com/owner/repo
      https://github.com/owner/repo/
      https://github.com/owner/repo/tree/branch/path
    """
    parsed = urlparse(url)
    if parsed.netloc not in ("github.com", "www.github.com"):
        raise ValueError("Not a github.com URL")

    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("URL does not contain owner/repo")

    owner, repo = parts[0], parts[1].replace(".git", "")
    # find branch if tree/<branch> provided
    branch = None
    if len(parts) >= 4 and parts[2] == "tree":
        branch = parts[3]
    return owner, repo, branch


def get_default_branch(owner, repo):
    url = f"{GITHUB_API}/repos/{owner}/{repo}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json().get("default_branch", "main")


def get_repo_tree(owner, repo, branch):
    # Use the Git Trees API with recursive=1 to get a listing of repository files.
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


def get_blob(owner, repo, sha):
    url = f"{GITHUB_API}/repos/{owner}/{repo}/git/blobs/{sha}"
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.json()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    repo_url = data.get("repo_url")
    branch_override = data.get("branch")
    # small safety limits by default
    max_files = int(data.get("max_files", 2000))
    max_file_size_bytes = int(data.get("max_file_size_bytes", 200 * 1024))  # 200 KB

    if not repo_url:
        return jsonify({"error": "repo_url is required"}), 400

    try:
        owner, repo, branch_from_url = parse_github_url(repo_url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    branch = branch_override or branch_from_url or get_default_branch(owner, repo)

    try:
        tree_resp = get_repo_tree(owner, repo, branch)
    except requests.HTTPError as e:
        return jsonify({"error": f"GitHub API error: {e}"}), 500

    if "tree" not in tree_resp:
        return jsonify({"error": "unexpected response from GitHub trees API"}), 500

    entries = tree_resp["tree"]
    files = [e for e in entries if e["type"] == "blob"]
    if len(files) > max_files:
        # return partial result but warn client
        files = files[:max_files]
        warning = f"Repo contains more than {max_files} files. Truncated."
    else:
        warning = None

    files_info = []
    # fetch blobs for content up to the size threshold
    for f in files:
        path = f["path"]
        size = f.get("size", 0)
        sha = f.get("sha")
        content = None
        # we will fetch content only for reasonably sized files (to avoid heavy downloads)
        if size and size <= max_file_size_bytes:
            try:
                blob = get_blob(owner, repo, sha)
                encoding = blob.get("encoding", "base64")
                if encoding == "base64":
                    import base64
                    raw = base64.b64decode(blob["content"])
                    try:
                        content = raw.decode("utf-8", errors="replace")
                    except Exception:
                        content = None
                else:
                    content = blob.get("content")
            except Exception:
                content = None

        files_info.append({
            "path": path,
            "size": size,
            "mode": f.get("mode"),
            "sha": sha,
            "content": content
        })

    # analyze files for imports, links, line counts etc.
    result = analyze_repo_tree(files_info, repo_owner=owner, repo_name=repo, branch=branch)

    response = {
        "owner": owner,
        "repo": repo,
        "branch": branch,
        "file_count": len(entries),
        "files_returned": len(files_info),
        "warning": warning,
        **result
    }
    return jsonify(response, 200)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
