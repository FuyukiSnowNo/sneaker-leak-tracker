#!/usr/bin/env python3
"""
main.py — Sneaker Leak Tracker CLI

Usage:
  python main.py scan
  python main.py scan --from 2025-01-01 --to 2025-04-21
  python main.py schedule --interval 6
  python main.py stats --from 2025-01-01
  python main.py export --format csv
  python main.py export --format json --output exports/leaks.json
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

from rich.console import Console

import config
from database.db import Database

console = Console()


def parse_date(s: str) -> datetime:
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        console.print(f"[red]Invalid date '{s}'. Use YYYY-MM-DD format.[/red]")
        sys.exit(1)


def cmd_scan(args):
    from scheduler.runner import run_scan
    db    = Database()
    since = parse_date(args.since) if args.since else None
    until = parse_date(args.until) if args.until else None
    run_scan(db, since=since, download_images=not args.no_images)


def cmd_schedule(args):
    from scheduler.runner import start_scheduler
    db       = Database()
    interval = args.interval or config.DEFAULT_INTERVAL_HOURS
    start_scheduler(db, interval_hours=interval)


def cmd_stats(args):
    from stats.analyzer import print_report
    db    = Database()
    since = parse_date(args.since) if args.since else None
    until = parse_date(args.until) if args.until else None
    print_report(db, since=since, until=until)


def cmd_weekly(args):
    """Run Instagram + Google for last 7 days, right now."""
    from scheduler.runner import run_weekly_scan
    db = Database()
    run_weekly_scan(db)


def cmd_export(args):
    from exports.exporter import export
    db    = Database()
    since = parse_date(args.since) if args.since else None
    until = parse_date(args.until) if args.until else None
    export(db, fmt=args.format, output=args.output, since=since, until=until)


def main():
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        prog="sneaker-leak-tracker",
        description="Automated sneaker leak scraper & stats tracker",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── scan ─────────────────────────────────────────────────────────────
    p_scan = sub.add_parser("scan", help="Run a one-time scrape")
    p_scan.add_argument("--from", dest="since", metavar="YYYY-MM-DD",
                        help="Only fetch articles published after this date")
    p_scan.add_argument("--no-images", dest="no_images", action="store_true", help="Skip image downloading")
    p_scan.add_argument("--to",   dest="until", metavar="YYYY-MM-DD",
                        help="Only fetch articles published before this date")

    # ── weekly ────────────────────────────────────────────────────────────
    sub.add_parser("weekly", help="Run Instagram + Google scan for last 7 days (now)")

    # ── schedule ─────────────────────────────────────────────────────────
    p_sched = sub.add_parser("schedule", help="Run on a repeating schedule")
    p_sched.add_argument("--interval", type=int, metavar="HOURS",
                         help=f"Scrape every N hours (default: {config.DEFAULT_INTERVAL_HOURS})")

    # ── stats ─────────────────────────────────────────────────────────────
    p_stats = sub.add_parser("stats", help="Print stats report")
    p_stats.add_argument("--from", dest="since", metavar="YYYY-MM-DD")
    p_stats.add_argument("--to",   dest="until", metavar="YYYY-MM-DD")

    # ── export ────────────────────────────────────────────────────────────
    p_exp = sub.add_parser("export", help="Export data to CSV or JSON")
    p_exp.add_argument("--format", choices=["csv", "json"], default="csv")
    p_exp.add_argument("--output", metavar="PATH",
                       help="Output file path (default: exports/leaks_TIMESTAMP.csv)")
    p_exp.add_argument("--from", dest="since", metavar="YYYY-MM-DD")
    p_exp.add_argument("--to",   dest="until", metavar="YYYY-MM-DD")

    args = parser.parse_args()

    dispatch = {
        "scan":     cmd_scan,
        "weekly":   cmd_weekly,
        "schedule": cmd_schedule,
        "stats":    cmd_stats,
        "export":   cmd_export,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
