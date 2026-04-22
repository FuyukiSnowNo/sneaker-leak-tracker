# scrapers/google_search.py
"""
Google Custom Search API scraper.

Free tier: 100 queries/day
Paid:      $5 per 1,000 queries after that

Setup:
  1. https://console.cloud.google.com
     → APIs & Services → Enable "Custom Search API"
     → Credentials → Create API Key
     → Paste into GOOGLE_API_KEY in config.py

  2. https://programmablesearchengine.google.com
     → New Search Engine → "Search the entire web"
     → Copy the Search Engine ID (cx value)
     → Paste into GOOGLE_CX in config.py
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from scrapers.base import BaseScraper, LeakItem
import config

logger = logging.getLogger(__name__)

DEFAULT_QUERIES = [
    "nike sneaker leaked 2025 -kit -uniform -jersey",
    "jordan sneaker leaked colorway 2025",
    "adidas yeezy leaked 2025",
    "new balance sneaker leak unreleased 2025",
    "sneaker collab leaked exclusive 2025",
    "site:sneakerbardetroit.com leak 2025",
    "site:sneakernews.com leaked unreleased",
    "donnie soles leaked sneaker",
]


class GoogleSearchScraper:
    source_id   = "google"
    source_name = "Google Search"
    _endpoint   = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        self.api_key = getattr(config, "GOOGLE_API_KEY", None)
        self.cx      = getattr(config, "GOOGLE_CX", None)
        if not self.api_key or not self.cx:
            raise ValueError(
                "Set GOOGLE_API_KEY and GOOGLE_CX in config.py\n"
                "See scrapers/google_search.py for setup steps."
            )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    def scrape(self, since: Optional[datetime] = None) -> list[LeakItem]:
        queries      = getattr(config, "GOOGLE_QUERIES", DEFAULT_QUERIES)
        date_restrict = getattr(config, "GOOGLE_DATE_RESTRICT", "d30")
        items        = []
        seen_urls    = set()

        for query in queries:
            try:
                results = self._search(query, date_restrict)
                for r in results:
                    url = r.get("link", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title   = r.get("title", "").strip()
                    snippet = r.get("snippet", "").strip()

                    item = LeakItem(
                        title        = title,
                        url          = url,
                        source       = self.source_id,
                        source_name  = self.source_name,
                        summary      = snippet,
                        published_at = self._parse_published(r),
                    )
                    text            = title + " " + snippet
                    item.brand      = BaseScraper._detect_brand(text)
                    item.hype_score = BaseScraper._calc_hype(text)
                    item.hype_tier  = BaseScraper._hype_tier(item.hype_score)
                    item.tags       = BaseScraper._extract_tags(text)
                    item.release_date = BaseScraper._extract_release_date(text)
                    items.append(item)

                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Google [{query[:40]}]: {e}")

        logger.info(f"Google Search: {len(items)} results from {len(queries)} queries")
        return items

    def _search(self, query: str, date_restrict: str) -> list[dict]:
        resp = self.session.get(self._endpoint, params={
            "key":          self.api_key,
            "cx":           self.cx,
            "q":            query,
            "num":          10,
            "dateRestrict": date_restrict,
        }, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise ValueError(data["error"].get("message", str(data["error"])))
        return data.get("items", [])

    @staticmethod
    def _parse_published(result: dict) -> Optional[datetime]:
        try:
            metatags = result.get("pagemap", {}).get("metatags", [{}])[0]
            for key in ("article:published_time", "og:updated_time", "date"):
                val = metatags.get(key)
                if val:
                    from dateutil import parser as dp
                    dt = dp.parse(val)
                    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
        except Exception:
            pass
        return None
