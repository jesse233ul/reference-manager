import base64
import getpass
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


REPOSITORY = "jesse233ul/reference-manager"
BRANCH = "main"

FILES = [
    "reference_manager_qt.py",
    "README.md",
    ".gitignore",
    "requirements.txt",
    "Start Reference Manager Qt.cmd",
    "Build Reference Manager.cmd",
    "ReferenceManager.spec",
    "version_info.txt",
    "app_icon.ico",
    "app_icon.png",
    "refmanager/__init__.py",
    "refmanager/app.py",
    "refmanager/main_window.py",
    "refmanager/metadata.py",
    "refmanager/paths.py",
    "refmanager/qt_compat.py",
    "refmanager/store.py",
    "refmanager/styles.py",
    "refmanager/widgets.py",
    "refmanager/windows_context.py",
]


def github_request(method: str, url: str, token: str, payload: dict | None = None) -> dict | None:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "reference-manager-upload-script",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}\n{detail}") from exc


def existing_file_sha(path: str, token: str) -> str | None:
    encoded_path = urllib.parse.quote(path, safe="/")
    url = f"https://api.github.com/repos/{REPOSITORY}/contents/{encoded_path}?ref={BRANCH}"
    try:
        result = github_request("GET", url, token)
    except RuntimeError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise
    return str(result["sha"]) if result and "sha" in result else None


def upload_file(path: Path, token: str) -> None:
    repo_path = path.as_posix()
    encoded_path = urllib.parse.quote(repo_path, safe="/")
    url = f"https://api.github.com/repos/{REPOSITORY}/contents/{encoded_path}"
    content = base64.b64encode(path.read_bytes()).decode("ascii")
    payload = {
        "message": f"Upload {repo_path}",
        "content": content,
        "branch": BRANCH,
    }
    sha = existing_file_sha(repo_path, token)
    if sha:
        payload["sha"] = sha
    github_request("PUT", url, token, payload)
    print(f"uploaded {repo_path}")


def main() -> int:
    root = Path(__file__).resolve().parent
    token = getpass.getpass("GitHub token: ").strip()
    if not token:
        print("No token provided.", file=sys.stderr)
        return 1

    missing = [name for name in FILES if not (root / name).exists()]
    if missing:
        print("Missing files:", file=sys.stderr)
        for name in missing:
            print(f"  {name}", file=sys.stderr)
        return 1

    for name in FILES:
        upload_file(root / name, token)

    print(f"Done: https://github.com/{REPOSITORY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
