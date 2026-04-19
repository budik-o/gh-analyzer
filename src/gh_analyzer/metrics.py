from __future__ import annotations

from gh_analyzer.iso_datetime import parse_iso_datetime


def _cycle_time_seconds(created_at: str, merged_at: str | None) -> float | None:
    if merged_at is None:
        return None
    created_dt = parse_iso_datetime(created_at)
    merged_dt = parse_iso_datetime(merged_at)
    delta = merged_dt - created_dt
    if delta.total_seconds() < 0:
        raise ValueError("merged_at is earlier than created_at")
    return delta.total_seconds()


def compute_pr_metrics(prs: list[dict[str, str | None]]) -> dict[str, float | int | None]:
    """Compute summary metrics for a list of pull requests."""
    merged_seconds = []
    for pr in prs:
        if pr["merged_at"] is not None:
            seconds = _cycle_time_seconds(pr["created_at"], pr["merged_at"])
            if seconds is not None:
                merged_seconds.append(seconds)
    return {
        "total_pr_count": len(prs),
        "merged_pr_count": len(merged_seconds),
        "average_cycle_time_seconds": sum(merged_seconds) / len(merged_seconds) if merged_seconds else None
    }

