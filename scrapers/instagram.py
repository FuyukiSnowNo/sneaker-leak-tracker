# scrapers/instagram.py
"""
Instagram scraper using Instaloader (free, no API key needed).

Risk factors:
  - Instagram rate-limits aggressively (~200 requests/hour anonymous)
  - Running too frequently can trigger soft bans on your IP
  - Recommended: run max once every 6 hours, use a logged-in session for higher limits

Setup:
  pip install instaloader

  Optional — log in once for higher rate limits:
    python -c "
    import instaloader
    L = instaloader.Instaloader()
    L.login('YOUR_USERNAME', 'YOUR_PASSWORD')
    L.save_session_to_file('ig_session')
    "
  Then set INSTALOADER_SESSION_FILE = 'ig_session' in config.py
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from scrapers.base import BaseScraper, LeakItem
import config

logger = logging.getLogger(__name__)

POSTS_PER_ACCOUNT = 12   # how many recent posts to check per account


class InstagramScraper:
    source_id   = "instagram"
    source_name = "Instagram"

    def __init__(self):
        try:
            import instaloader
            self._il = instaloader
        except ImportError:
            raise ImportError("Run: pip install instaloader")

        self.L = self._il.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            quiet=True,
        )

        # Use saved session if configured (recommended)
        session_file = getattr(config, "INSTALOADER_SESSION_FILE", None)
        if session_file:
            try:
                self.L.load_session_from_file(session_file)
                logger.info("Instagram: loaded saved session")
            except Exception as e:
                logger.warning(f"Instagram: session load failed ({e}), using anonymous")

    def scrape(self, since: Optional[datetime] = None) -> list[LeakItem]:
        accounts = getattr(config, "INSTAGRAM_ACCOUNTS", [])
        items    = []

        for acct in accounts:
            username = acct["username"]
            items   += self._scrape_account(username, since)
            time.sleep(getattr(config, "INSTAGRAM_DELAY", 5))  # be polite

        logger.info(f"Instagram total: {len(items)} posts")
        return items

    def _scrape_account(self, username: str, since: Optional[datetime]) -> list[LeakItem]:
        items = []
        try:
            profile = self._il.Profile.from_username(self.L.context, username)
            count   = 0

            for post in profile.get_posts():
                if count >= POSTS_PER_ACCOUNT:
                    break

                pub = post.date_utc.replace(tzinfo=timezone.utc)
                if since and pub < since:
                    break   # posts are newest-first — safe to stop early

                caption    = (post.caption or "").strip()
                first_line = caption.split("\n")[0][:80].strip()
                summary    = caption[:400].replace("\n", " ")

                # Get the display image URL from instaloader
                    img_url = ""
                    try:
                        img_url = post.url  # direct image URL
                    except Exception:
                        pass

                    item = LeakItem(
                    title        = first_line or f"@{username} post",
                    url          = f"https://www.instagram.com/p/{post.shortcode}/",
                    source       = self.source_id,
                    source_name  = f"IG @{username}",
                    summary      = summary,
                    published_at = pub,
                        image_url    = img_url,
                )

                text            = item.title + " " + item.summary
                item.brand      = BaseScraper._detect_brand(text)
                item.hype_score = BaseScraper._calc_hype(text)
                item.hype_tier  = BaseScraper._hype_tier(item.hype_score)
                item.tags       = BaseScraper._extract_tags(text)
                item.release_date = BaseScraper._extract_release_date(text)

                items.append(item)
                count += 1

        except Exception as e:
            logger.error(f"Instagram @{username}: {e}")

        return items
