"""GitHub REST client for listing pull requests.

Uses ``GITHUB_TOKEN`` for Bearer authentication when set. The ``metrics`` CLI
requires the token; unit tests mock ``requests.get`` and do not hit the network.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests
from requests import RequestException

API_ROOT = "https://api.github.com"


class GitHubApiError(Exception):
    """Raised when a GitHub API HTTP request fails or returns an error status."""


def _auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _parse_iso8601(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as e:
        raise ValueError(f"Invalid ISO 8601 datetime: {value!r}") from e


def _pr_slice(pr: dict[str, Any]) -> dict[str, str | None]:
    return {
        "created_at": pr["created_at"],
        "merged_at": pr.get("merged_at"),
        "state": pr["state"],
    }


def _raise_for_error_response(response: requests.Response) -> None:
    status = response.status_code
    text_snippet = response.text[:500]
    if status == 401:
        raise GitHubApiError(
            "Authentication failed (401): invalid or expired GITHUB_TOKEN."
        )
    if status == 404:
        raise GitHubApiError(
            "Repository not found (404): check owner/repo spelling."
        )
    if status == 429:
        raise GitHubApiError(
            "GitHub API rate limit reached (429). Try again later."
        )
    if status == 403:
        remaining = response.headers.get("X-RateLimit-Remaining", "")
        if remaining == "0" or "rate limit" in response.text.lower():
            raise GitHubApiError(
                "GitHub API rate limit reached (403). Try again later or use GITHUB_TOKEN."
            )
    raise GitHubApiError(f"HTTP {status}: {text_snippet}")


def fetch_pull_requests(
    repo: str,
    since: str | None = None,
) -> list[dict[str, str | None]]:
    """Fetch pull requests from GitHub API with pagination.

    Each item has ``created_at``, ``merged_at``, and ``state`` only.

    If ``since`` is an ISO 8601 instant, only PRs with ``created_at`` at or
    after that time are kept (client-side; the pulls API has no ``since`` param).
    In that case requests use ``sort=created`` and ``direction=desc`` (newest
    first). Once a full page's oldest ``created_at`` is before ``since``, no
    later page can contribute matches, so pagination stops early.

    Without ``since``, pagination runs until a page is empty or shorter than
    ``per_page`` (GitHub default ordering).
    """
    if repo.count("/") != 1:
        raise ValueError("repo must be in the form owner/repo")
    owner, repo_name = repo.split("/", 1)
    if not owner or not repo_name:
        raise ValueError("repo must be in the form owner/repo")

    since_dt: datetime | None = None
    if since is not None and since != "":
        try:
            since_dt = _parse_iso8601(since)
        except ValueError as e:
            raise ValueError(
                f"since must be ISO 8601 (e.g. 2020-01-01T00:00:00Z), got: {since!r}"
            ) from e

    url = f"{API_ROOT}/repos/{owner}/{repo_name}/pulls"
    out: list[dict[str, str | None]] = []
    page = 1
    per_page = 100

    while True:
        params: dict[str, Any] = {
            "state": "all",
            "per_page": per_page,
            "page": page,
        }
        if since_dt is not None:
            params["sort"] = "created"
            params["direction"] = "desc"

        try:
            response = requests.get(
                url,
                headers=_auth_headers(),
                params=params,
                timeout=60,
            )
        except RequestException as e:
            raise GitHubApiError(f"Request failed: {e}") from e

        if not response.ok:
            _raise_for_error_response(response)

        payload = response.json()
        if not isinstance(payload, list):
            raise GitHubApiError(
                "Unexpected response shape: expected list of pull requests"
            )
        batch: list[dict[str, Any]] = payload

        if not batch:
            break

        oldest_on_page: datetime | None = None
        for pr in batch:
            row = _pr_slice(pr)
            if since_dt is not None:
                try:
                    created = _parse_iso8601(str(row["created_at"]))
                except (TypeError, ValueError) as e:
                    raise GitHubApiError(
                        f"Invalid created_at from API: {row.get('created_at')!r}"
                    ) from e
                if oldest_on_page is None or created < oldest_on_page:
                    oldest_on_page = created
                if created < since_dt:
                    continue
            out.append(row)

        if (
            since_dt is not None
            and oldest_on_page is not None
            and oldest_on_page < since_dt
        ):
            break

        if len(batch) < per_page:
            break
        page += 1

    return out
