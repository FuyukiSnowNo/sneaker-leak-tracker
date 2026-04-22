# scheduler/runner.py
import logging
import time
from datetime import datetime, timezone, timedelta

import schedule
from rich.console import Console

from database.db import Database
from utils.image_downloader import ImageDownloader
import config

console = Console()
logger  = logging.getLogger(__name__)


def _get_scrapers() -> list:
    from scrapers.sneakernews       import SneakerNewsScraper
    from scrapers.sneakerbardetroit import SneakerBarDetroitScraper
    from scrapers.others            import (
        SneakerFreakerScraper, HypebeastScraper, KicksOnFireScraper
    )
    rss_map = {
        "sneakernews":       SneakerNewsScraper,
        "sneakerbardetroit": SneakerBarDetroitScraper,
        "sneakerfreaker":    SneakerFreakerScraper,
        "hypebeast":         HypebeastScraper,
        "kicksonfire":       KicksOnFireScraper,
    }
    scrapers = [
        cls() for src in config.SOURCES
        if src["enabled"]
        for sid, cls in rss_map.items()
        if sid == src["id"]
    ]

    if getattr(config, "INSTAGRAM_ENABLED", True):
        try:
            from scrapers.instagram import InstagramScraper
            scrapers.append(InstagramScraper())
        except Exception as e:
            logger.warning(f"Instagram scraper skipped: {e}")

    if getattr(config, "GOOGLE_ENABLED", True):
        api_key = getattr(config, "GOOGLE_API_KEY", "")
        cx      = getattr(config, "GOOGLE_CX", "")
        if api_key and api_key not in ("", "YOUR_GOOGLE_API_KEY"):
            try:
                from scrapers.google_search import GoogleSearchScraper
                scrapers.append(GoogleSearchScraper())
            except Exception as e:
                logger.warning(f"Google scraper skipped: {e}")
        else:
            logger.info("Google Search: set GOOGLE_API_KEY + GOOGLE_CX in config.py to enable")

    return scrapers


def run_scan(db: Database, since: datetime = None, download_images: bool = True) -> dict:
    scrapers = _get_scrapers()
    since    = since or datetime.now(timezone.utc) - timedelta(hours=config.DEFAULT_INTERVAL_HOURS)
    downloader = ImageDownloader() if download_images else None

    total_new = total_skip = total_imgs = 0
    source_results = {}

    console.print(f"\n[bold red]▶ SCAN STARTED[/bold red]  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"[dim]  Since: {since.strftime('%Y-%m-%d %H:%M')} UTC · Sources: {len(scrapers)} · Images: {'yes' if download_images else 'no'}[/dim]\n")

    all_new_items = []

    for scraper in scrapers:
        console.print(f"  [yellow]→[/yellow] {scraper.source_name}...", end=" ")
        try:
            items = scraper.scrape(since=since)

            # Download images before inserting so image_path is stored immediately
            if downloader and items:
                imgs_dl, imgs_skip = downloader.download_all(items)
                total_imgs += imgs_dl
                console.print(
                    f"[green]{len(items)} scraped[/green]  "
                    f"[dim]{imgs_dl} imgs downloaded · ", end=""
                )
            else:
                console.print(f"[green]{len(items)} scraped[/green]  [dim]", end="")

            new, skip = db.insert_many(items)
            total_new  += new
            total_skip += skip
            all_new_items.extend(items)
            source_results[scraper.source_name] = {
                "scraped": len(items), "new": new, "skip": skip
            }
            console.print(f"{new} new · {skip} dupes[/dim]")

        except Exception as e:
            source_results[scraper.source_name] = {"error": str(e)}
            console.print(f"[red]ERROR: {e}[/red]")
            logger.exception(f"Scraper {scraper.source_id} failed")

    console.print(
        f"\n[bold green]✓ DONE[/bold green]  "
        f"{total_new} new leaks · {total_imgs} images downloaded  "
        f"[dim](DB total: {db.count()})[/dim]\n"
    )

    return {
        "scanned_at":        datetime.now(timezone.utc).isoformat(),
        "new":               total_new,
        "skipped":           total_skip,
        "images_downloaded": total_imgs,
        "sources":           source_results,
    }


def start_scheduler(db: Database, interval_hours: int = config.DEFAULT_INTERVAL_HOURS):
    console.print(f"[bold]Scheduler started — every {interval_hours}h[/bold]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    run_scan(db)
    schedule.every(interval_hours).hours.do(run_scan, db=db)
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scheduler stopped.[/yellow]")
