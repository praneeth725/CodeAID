"""
core/repo_loader.py
-------------------
Handles loading Python source files from:
  1. A public GitHub repository URL (downloaded as ZIP via GitHub API)
  2. A user-uploaded ZIP archive

Returns a list of dicts: [{"path": relative_path, "source": file_content}, ...]
"""

import os
import io
import re
import zipfile
import tempfile
import requests


# ─────────────────────────────────────────────
# Public entry points
# ─────────────────────────────────────────────

def load_from_github(url: str) -> tuple[list[dict], str]:
    """
    Download a public GitHub repo as a ZIP and extract Python files.
    Accepts URLs like:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch
      https://github.com/owner/repo.git

    Returns:
        (files, repo_name)  where files = [{"path": str, "source": str}, ...]
    """
    owner, repo, branch = _parse_github_url(url)
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

    try:
        response = requests.get(zip_url, timeout=30)
        if response.status_code == 404:
            # Try 'master' if 'main' failed or vice versa
            alt_branch = "master" if branch == "main" else "main"
            zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{alt_branch}.zip"
            response = requests.get(zip_url, timeout=30)

        if response.status_code != 200:
            raise ValueError(
                f"Could not download repository. HTTP {response.status_code}. "
                "Check that the URL is correct and the repository is public."
            )
    except requests.exceptions.ConnectionError:
        raise ValueError(
            "Network error: Could not reach GitHub. Please check your internet connection."
        )
    except requests.exceptions.Timeout:
        raise ValueError("Request timed out. The repository may be too large or GitHub is slow.")

    zip_bytes = io.BytesIO(response.content)
    files = _extract_python_files_from_zip(zip_bytes)

    if not files:
        raise ValueError(
            "No Python (.py) files found in the repository. "
            "Make sure this is a Python project."
        )

    return files, f"{owner}/{repo}"


def load_from_zip(zip_bytes: bytes) -> tuple[list[dict], str]:
    """
    Load Python files from a ZIP file uploaded by the user.

    Returns:
        (files, archive_name)
    """
    try:
        zip_buffer = io.BytesIO(zip_bytes)
        files = _extract_python_files_from_zip(zip_buffer)
    except zipfile.BadZipFile:
        raise ValueError("The uploaded file is not a valid ZIP archive.")

    if not files:
        raise ValueError(
            "No Python (.py) files found in the ZIP. "
            "Make sure the archive contains a Python project."
        )

    return files, "uploaded_project"


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _parse_github_url(url: str) -> tuple[str, str, str]:
    """
    Parse a GitHub URL into (owner, repo, branch).
    Handles various URL formats robustly.
    """
    url = url.strip().rstrip("/")

    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    # Pattern: https://github.com/owner/repo[/tree/branch]
    pattern = r"github\.com[/:]([^/]+)/([^/]+)(?:/tree/([^/]+))?"
    match = re.search(pattern, url)

    if not match:
        raise ValueError(
            f"Invalid GitHub URL: '{url}'\n"
            "Expected format: https://github.com/owner/repository"
        )

    owner = match.group(1)
    repo = match.group(2)
    branch = match.group(3) or "main"

    return owner, repo, branch


def _extract_python_files_from_zip(zip_buffer: io.BytesIO) -> list[dict]:
    """
    Extract all .py files from a ZIP archive.
    Skips: hidden files, __pycache__, .git, test files (optional),
           empty files, and non-UTF-8 files.

    Returns list of {"path": str, "source": str}
    """
    files = []
    skip_dirs = {"__pycache__", ".git", ".tox", ".venv", "venv", "env", "node_modules", ".eggs"}
    skip_files = {"setup.py", "conftest.py"}  # keep these actually — useful for analysis

    with zipfile.ZipFile(zip_buffer, "r") as zf:
        # Get the top-level folder name (GitHub adds reponame-branch/ prefix)
        all_names = zf.namelist()
        prefix = _detect_zip_prefix(all_names)

        for name in all_names:
            if not name.endswith(".py"):
                continue

            # Strip the GitHub-added prefix to get a clean relative path
            rel_path = name[len(prefix):] if prefix and name.startswith(prefix) else name
            rel_path = rel_path.lstrip("/")

            if not rel_path:
                continue

            # Skip hidden files and junk directories
            parts = rel_path.replace("\\", "/").split("/")
            if any(part.startswith(".") for part in parts):
                continue
            if any(part in skip_dirs for part in parts):
                continue

            try:
                raw = zf.read(name)
                if not raw.strip():
                    continue  # skip empty files
                source = raw.decode("utf-8")
            except (UnicodeDecodeError, KeyError):
                # Skip files that aren't valid UTF-8
                continue

            files.append({
                "path": rel_path,
                "source": source,
            })

    # Sort by path for consistent ordering
    files.sort(key=lambda f: f["path"])
    return files


def _detect_zip_prefix(names: list[str]) -> str:
    """
    GitHub ZIP archives wrap everything in a top-level folder like 'repo-main/'.
    Detect and return that prefix so we can strip it.
    """
    if not names:
        return ""

    # Find common prefix
    first = names[0]
    if "/" not in first:
        return ""

    prefix = first.split("/")[0] + "/"

    # Verify all entries share this prefix
    if all(n.startswith(prefix) or n == prefix.rstrip("/") for n in names):
        return prefix

    return ""
