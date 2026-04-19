"""Fetch repository tree and file bodies from GitHub Contents API for remote scanning."""

from __future__ import annotations

import base64
from typing import Any, Iterator
from urllib.parse import quote

import requests
from requests import RequestException

from gh_analyzer.github_client import API_ROOT, GitHubApiError, auth_headers, raise_for_error_response
from gh_analyzer.security_scanner import build_patterns, scan_text


def parse_repo(repo: str) -> tuple[str, str]:
    if repo.count("/") != 1:
        raise ValueError("repo must be in the form owner/repo")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise ValueError("repo must be in the form owner/repo")
    return owner, name


def _contents_url(owner: str, repo: str, path: str) -> str:
    base = f"{API_ROOT}/repos/{owner}/{repo}/contents"
    if not path:
        return base
    encoded = quote(path, safe="/")
    return f"{base}/{encoded}"


def _get_json(owner: str, repo: str, path: str) -> Any:
    url = _contents_url(owner, repo, path)
    try:
        response = requests.get(url, headers=auth_headers(), timeout=60)
    except RequestException as e:
        raise GitHubApiError(f"Request failed: {e}") from e
    if not response.ok:
        raise_for_error_response(response)
    return response.json()


def _decode_file_body(obj: dict[str, Any]) -> str:
    if obj.get("type") != "file":
        raise GitHubApiError(
            f"Expected a file object from API, got type={obj.get('type')!r}"
        )
    encoding = obj.get("encoding")
    content = obj.get("content")
    if encoding == "base64" and isinstance(content, str):
        raw = base64.b64decode(content.encode("ascii"), validate=False)
        return raw.decode("utf-8", errors="ignore")
    if isinstance(content, str) and not encoding:
        return content
    raise GitHubApiError(
        "File response missing base64 content; large files may need a different API."
    )


def iter_repo_files(owner: str, repo: str, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield ``(path_in_repo, decoded_text)`` for each file under ``path`` (recursive)."""
    payload = _get_json(owner, repo, path)

    if isinstance(payload, dict):
        t = payload.get("type")
        if t == "file":
            yield str(payload["path"]), _decode_file_body(payload)
            return
        if t in ("symlink", "submodule"):
            return
        raise GitHubApiError(f"Unexpected contents object type: {t!r}")

    if isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            t = item.get("type")
            child_path = item.get("path")
            if not isinstance(child_path, str):
                continue
            if t == "dir":
                yield from iter_repo_files(owner, repo, child_path)
            elif t == "file":
                body = _get_json(owner, repo, child_path)
                if not isinstance(body, dict):
                    raise GitHubApiError("Expected file object when fetching file path")
                yield child_path, _decode_file_body(body)
        return

    raise GitHubApiError("Unexpected response shape from contents API")


def scan_github_repo(repo: str) -> list[dict[str, object]]:
    """Scan all files in a GitHub repository via the Contents API."""
    owner, name = parse_repo(repo)
    patterns = build_patterns()
    findings: list[dict[str, object]] = []
    label_prefix = f"{owner}/{name}"
    for path_in_repo, text in iter_repo_files(owner, name, ""):
        label = f"{label_prefix}:{path_in_repo}"
        findings.extend(scan_text(label, text, patterns))
    return findings
