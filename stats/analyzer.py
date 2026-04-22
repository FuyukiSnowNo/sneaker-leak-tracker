# stats/analyzer.py
"""
Generates stats reports from the database.
Uses `rich` for pretty terminal output.
"""

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich import box

from database.db import Database

console = Console()


def print_report(
    db: Database,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
):
    until = until or datetime.now(timezone.utc)
    label = _period_label(since, until)

    total        = len(db.query(since=since, until=until, limit=99999))
    brand_counts = db.brand_counts(since=since, until=until)
    src_counts   = db.source_counts(since=since, until=until)
    hype_dist    = db.hype_distribution(since=since, until=until)
    daily        = db.daily_counts(since=since, until=until)
    top_hype     = db.top_hype(since=since, until=until, n=10)

    days   = max((until - since).days, 1) if since else 1
    avg    = round(total / days, 1)
    peak   = max(daily, key=lambda d: d["count"], default={"day": "N/A", "count": 0})
    grails = sum(r["count"] for r in hype_dist if r["hype_tier"] == "GRAIL")
    highs  = sum(r["count"] for r in hype_dist if r["hype_tier"] in ("HIGH", "GRAIL"))

    # ── Header ──────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold white]📊  SNEAKER LEAK REPORT[/bold white]\n"
        f"[dim]{label}[/dim]",
        style="red", box=box.HEAVY
    ))
    console.print()

    # ── Summary row ─────────────────────────────────────────────────────
    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    summary.add_column(style="dim")
    summary.add_column(style="bold white")
    summary.add_row("Total leaks captured", str(total))
    summary.add_row("Period (days)",        str(days))
    summary.add_row("Avg leaks / day",      str(avg))
    summary.add_row("Peak day",             f"{peak['day']}  ({peak['count']} leaks)")
    summary.add_row("High-hype leaks",      f"{highs}  ({_pct(highs, total)}%)")
    summary.add_row("GRAIL tier leaks",     str(grails))
    console.print(summary)
    console.print()

    # ── Brand breakdown ─────────────────────────────────────────────────
    bt = Table(title="[bold]TOP BRANDS[/bold]", box=box.SIMPLE_HEAD, min_width=40)
    bt.add_column("#",      style="dim",        width=4)
    bt.add_column("Brand",  style="bold white")
    bt.add_column("Count",  justify="right")
    bt.add_column("Share",  justify="right",   style="dim")
    bt.add_column("Bar",    style="red")
    for i, row in enumerate(brand_counts[:10], 1):
        bar = "█" * int(row["count"] / max(brand_counts[0]["count"], 1) * 20)
        bt.add_row(str(i), row["brand"], str(row["count"]),
                   f"{_pct(row['count'], total)}%", bar)
    console.print(bt)
    console.print()

    # ── Sources ─────────────────────────────────────────────────────────
    st = Table(title="[bold]MOST ACTIVE SOURCES[/bold]", box=box.SIMPLE_HEAD, min_width=40)
    st.add_column("Source", style="bold white")
    st.add_column("Count",  justify="right")
    st.add_column("Share",  justify="right", style="dim")
    for row in src_counts:
        st.add_row(row["source_name"], str(row["count"]),
                   f"{_pct(row['count'], total)}%")
    console.print(st)
    console.print()

    # ── Hype distribution ────────────────────────────────────────────────
    ht = Table(title="[bold]HYPE DISTRIBUTION[/bold]", box=box.SIMPLE_HEAD, min_width=40)
    ht.add_column("Tier",   style="bold")
    ht.add_column("Count",  justify="right")
    ht.add_column("Share",  justify="right", style="dim")
    tier_colors = {"GRAIL": "magenta", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}
    for row in hype_dist:
        color = tier_colors.get(row["hype_tier"], "white")
        ht.add_row(
            f"[{color}]{row['hype_tier']}[/{color}]",
            str(row["count"]),
            f"{_pct(row['count'], total)}%"
        )
    console.print(ht)
    console.print()

    # ── Top hype leaks ───────────────────────────────────────────────────
    if top_hype:
        tt = Table(title="[bold]TOP HYPE LEAKS[/bold]", box=box.SIMPLE_HEAD)
        tt.add_column("Score", justify="center", width=6)
        tt.add_column("Tier",  width=8)
        tt.add_column("Title", style="bold white", max_width=44)
        tt.add_column("Brand", style="dim",        width=12)
        tt.add_column("Date",  style="dim",        width=12)
        tier_colors = {"GRAIL": "magenta", "HIGH": "red", "MEDIUM": "yellow", "LOW": "green"}
        for row in top_hype:
            color = tier_colors.get(row["hype_tier"], "white")
            tt.add_row(
                f"[bold]{row['hype_score']}[/bold]",
                f"[{color}]{row['hype_tier']}[/{color}]",
                row["title"],
                row["brand"],
                row["release_date"],
            )
        console.print(tt)
        console.print()

    # ── Daily trend sparkline ────────────────────────────────────────────
    if daily:
        _print_sparkline(daily)

    console.print()


def _print_sparkline(daily: list[dict]):
    """Tiny ASCII bar chart of daily leak counts."""
    if not daily:
        return
    counts = [d["count"] for d in daily]
    mx     = max(counts) or 1
    bars   = "▁▂▃▄▅▆▇█"
    line   = "".join(bars[min(int(c / mx * 7), 7)] for c in counts)
    console.print(Panel(
        f"[dim]Daily trend (each char = 1 day)[/dim]\n[bold red]{line}[/bold red]\n"
        f"[dim]Min: {min(counts)}  Max: {mx}  Days: {len(daily)}[/dim]",
        title="LEAK VOLUME TREND",
        box=box.SIMPLE
    ))


def _pct(part, total) -> str:
    if total == 0:
        return "0.0"
    return f"{part / total * 100:.1f}"


def _period_label(since, until) -> str:
    fmt = "%b %d %Y"
    if since:
        return f"{since.strftime(fmt)} → {until.strftime(fmt)}"
    return f"All time → {until.strftime(fmt)}"
