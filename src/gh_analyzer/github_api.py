"""Minimal GitHub REST client for listing pull requests.

If GITHUB_TOKEN is unset, requests are unauthenticated. GitHub then applies
a low REST rate limit (roughly 60 requests per hour per IP); authenticated
requests get a much higher allowance. Set GITHUB_TOKEN for reliable use.
"""

from __future__ import annotations

import os
from typing import Any

import requests

API_ROOT = "https://api.github.com"


class GitHubApiError(Exception):
    """Raised when a GitHub API HTTP request fails or returns an error status."""


def _auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _pr_slice(pr: dict[str, Any]) -> dict[str, Any]:
    return {
        "created_at": pr["created_at"],
        "merged_at": pr.get("merged_at"),
        "state": pr["state"],
    }


def fetch_pull_requests(repo: str) -> list[dict[str, Any]]:
    """Return all pull requests for ``owner/repo`` with ``state=all`` (open, closed, merged).

    Pages are requested with ``per_page=100`` until a page returns fewer than
    ``per_page`` items or an empty list.
    """
    if repo.count("/") != 1:
        raise ValueError("repo must be in the form owner/repo")
    owner, repo_name = repo.split("/", 1)
    if not owner or not repo_name:
        raise ValueError("repo must be in the form owner/repo")

    url = f"{API_ROOT}/repos/{owner}/{repo_name}/pulls"
    out: list[dict[str, Any]] = []
    page = 1
    per_page = 100

    while True:
        response = requests.get(
            url,
            headers=_auth_headers(),
            params={"state": "all", "per_page": per_page, "page": page},
            timeout=60,
        )
        if not response.ok:
            raise GitHubApiError(
                f"HTTP {response.status_code}: {response.text[:500]}"
            )

        batch: list[dict[str, Any]] = response.json()
        if not batch:
            break

        out.extend(_pr_slice(pr) for pr in batch)

        if len(batch) < per_page:
            break
        page += 1

    return out
