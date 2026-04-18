"""CLI entrypoint for gh-analyzer."""

from __future__ import annotations

import argparse
import json
import os

from gh_analyzer.github_api import GitHubApiError, fetch_pull_requests
from gh_analyzer.metrics import compute_pr_metrics
from gh_analyzer.security_scanner import scan_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gh-analyzer",
        description="GitHub Analyzer CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a path for potential secrets")
    scan_parser.add_argument("path", help="Path to scan")

    metrics_parser = subparsers.add_parser("metrics", help="Show basic repository metrics")
    metrics_parser.add_argument("repo", help="Repository in owner/name format")
    metrics_parser.add_argument(
        "--since",
        default=None,
        metavar="ISO8601",
        help="Only include PRs created at or after this time (e.g. 2020-01-01T00:00:00Z)",
    )

    return parser


def _print_metrics(metrics: dict[str, float | int | None]) -> None:
    total = metrics["total_pr_count"]
    merged = metrics["merged_pr_count"]
    avg_sec = metrics["average_cycle_time_seconds"]
    if avg_sec is None:
        avg_hours_display = "N/A"
    else:
        avg_hours = float(avg_sec) / 3600.0
        avg_hours_display = f"{avg_hours:.2f}"

    print(f"Total PRs: {total}")
    print(f"Merged PRs: {merged}")
    print(f"Avg cycle time (hours): {avg_hours_display}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        findings = scan_path(args.path)
        print(json.dumps(findings, indent=2))
        return 1 if findings else 0

    if args.command == "metrics":
        if not os.environ.get("GITHUB_TOKEN"):
            print(
                "Error: GITHUB_TOKEN is not set. "
                "Create a personal access token and export it before running metrics."
            )
            return 2

        try:
            prs = fetch_pull_requests(args.repo, since=args.since)
            metrics = compute_pr_metrics(prs)
        except (GitHubApiError, ValueError) as e:
            print(str(e))
            return 2

        _print_metrics(metrics)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
