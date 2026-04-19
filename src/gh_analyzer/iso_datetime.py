"""Parse GitHub-style ISO-8601 timestamps (including ``Z`` suffix)."""

from __future__ import annotations

from datetime import datetime


def parse_iso_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Invalid ISO 8601 datetime: {value!r}") from e
