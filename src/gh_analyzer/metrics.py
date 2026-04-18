from datetime import datetime


def _parse_github_datetime(dt: str) -> datetime:
    try:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Invalid datetime format, expect ISO 8601, got: {dt}") from e


def _cycle_time_seconds(created_at: str, merged_at: str | None) -> float | None:
    if merged_at is None:
        return None
    created_dt = _parse_github_datetime(created_at)
    merged_dt = _parse_github_datetime(merged_at)
    delta = merged_dt - created_dt
    if delta.total_seconds() < 0:
        raise ValueError("merged_at is earlier than created_at")
    return delta.total_seconds()


def compute_pr_metrics(prs: list[dict[str, str | None]]) -> dict[str, float | int | None]:
    """Compute summary metrics for a list of pull requests."""
    merged_prs = []
    for pr in prs:
        if pr["merged_at"] is not None:
            seconds = _cycle_time_seconds(pr["created_at"], pr["merged_at"])
            if seconds is not None:
                merged_prs.append(seconds)
    return {
        "total_pr_count": len(prs),
        "merged_pr_count": len(merged_prs),
        "average_cycle_time_seconds": sum(merged_prs) / len(merged_prs) if merged_prs else None
    }


compute_pr_metrics_summary = compute_pr_metrics