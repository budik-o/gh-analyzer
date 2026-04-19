"""Shared GitHub REST helpers (base URL, auth headers, HTTP error mapping)."""

from __future__ import annotations

import os

import requests

API_ROOT = "https://api.github.com"


class GitHubApiError(Exception):
    """Raised when a GitHub API HTTP request fails or returns an error status."""


def auth_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def raise_for_error_response(response: requests.Response) -> None:
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
