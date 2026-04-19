"""GitHub REST client for listing pull requests.

Uses ``GITHUB_TOKEN`` for Bearer authentication when set. The ``metrics`` CLI
requires the token; unit tests mock ``requests.get`` and do not hit the network.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
from requests import RequestException

from gh_analyzer.github_client import (
    API_ROOT,
    GitHubApiError,
    auth_headers,
    raise_for_error_response,
)
from gh_analyzer.iso_datetime import parse_iso_datetime

# Backwards-compatible re-exports for callers/tests that import from this module.
__all__ = ["API_ROOT", "GitHubApiError", "fetch_pull_requests"]


def _pr_slice(pr: dict[str, Any]) -> dict[str, str | None]:
    return {
        "created_at": pr["created_at"],
        "merged_at": pr.get("merged_at"),
        "state": pr["state"],
    }


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
            since_dt = parse_iso_datetime(since)
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
                headers=auth_headers(),
                params=params,
                timeout=60,
            )
        except RequestException as e:
            raise GitHubApiError(f"Request failed: {e}") from e

        if not response.ok:
            raise_for_error_response(response)

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
                    created = parse_iso_datetime(str(row["created_at"]))
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
