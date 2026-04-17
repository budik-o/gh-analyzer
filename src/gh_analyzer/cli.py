"""CLI entrypoint for gh-analyzer."""

from __future__ import annotations

import argparse
import json


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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        print(f"'scan' command recognized for repo: {args.repo}")
        return 0

    if args.command == "metrics":
        print(f"'metrics' command recognized for repo: {args.repo}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
