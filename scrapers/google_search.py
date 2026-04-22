# scrapers/google_search.py
"""
Google Custom Search API — IMAGE search mode.

Searches Google Images for sneaker leak phrases and returns:
  - image_url  : direct link to the image file
  - url        : the page the image came from
  - title      : image/page title
  - summary    : snippet from the source page

Free tier: 100 queries/day (each query = 10 image results)
Paid:      $5 per 1,000 queries

Setup:
  1. https://console.cloud.google.com
     → APIs & Services → Enable "Custom Search API"
     → Credentials → Create API Key → paste as GOOGLE_API_KEY in config.py

  2. https://programmablesearchengine.google.com
     → Create engine → add sneaker sites
     → Turn ON "Image search" toggle
     → Copy Search Engine ID → paste as GOOGLE_CX in config.py
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import requests
from scrapers.base import BaseScraper, LeakItem
import config

logger = logging.getLogger(__name__)

# Each query = 1 API call = up to 10 image results
# 8 queries = 80 images per scan, well within 100/day free limit
DEFAULT_QUERIES = [
    "nike shoes leaked -kit -uniform -jersey",
    "jordan sneaker leaked colorway unreleased",
    "adidas yeezy leaked 2025",
    "new balance sneaker leak unreleased",
    "sneaker collab leaked exclusive sample",
    "travis scott nike leaked",
    "off white nike unreleased leak",
    "sneaker friends family exclusive leak",
]


class GoogleSearchScraper:
    source_id   = "google_images"
    source_name = "Google Images"
    _endpoint   = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        self.api_key = getattr(config, "GOOGLE_API_KEY", None)
        self.cx      = getattr(config, "GOOGLE_CX", None)
        if not self.api_key or not self.cx:
            raise ValueError(
                "Set GOOGLE_API_KEY and GOOGLE_CX in config.py"
            )
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    def scrape(self, since: Optional[datetime] = None) -> list[LeakItem]:
        queries       = getattr(config, "GOOGLE_QUERIES", DEFAULT_QUERIES)
        date_restrict = getattr(config, "GOOGLE_DATE_RESTRICT", "d30")
        items         = []
        seen_urls     = set()

        for query in queries:
            try:
                results = self._image_search(query, date_restrict)
                logger.info(f"Google Images [{query[:35]}]: {len(results)} results")

                for r in results:
                    # image_url = direct link to the image file
                    image_url  = r.get("link", "")
                    # page_url  = the webpage the image lives on
                    page_url   = r.get("image", {}).get("contextLink", image_url)

                    if not image_url or image_url in seen_urls:
                        continue
                    seen_urls.add(image_url)

                    title   = r.get("title", "").strip()
                    snippet = r.get("snippet", "").strip()

                    # Width/height from API — useful for filtering tiny thumbnails
                    img_info = r.get("image", {})
                    width    = img_info.get("width", 0)
                    height   = img_info.get("height", 0)

                    # Skip tiny images (likely icons/logos, not shoe photos)
                    if width and height and (width < 200 or height < 200):
                        continue

                    item = LeakItem(
                        title        = title or query,
                        url          = page_url,
                        source       = self.source_id,
                        source_name  = self.source_name,
                        summary      = snippet or f"Image result for: {query}",
                        image_url    = image_url,   # ← direct image URL in CSV
                    )
                    text              = title + " " + snippet + " " + query
                    item.brand        = BaseScraper._detect_brand(text)
                    item.hype_score   = BaseScraper._calc_hype(text)
                    item.hype_tier    = BaseScraper._hype_tier(item.hype_score)
                    item.tags         = BaseScraper._extract_tags(text)
                    item.release_date = BaseScraper._extract_release_date(text)
                    items.append(item)

                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Google Images [{query[:40]}]: {e}")

        logger.info(f"Google Images total: {len(items)} images across {len(queries)} queries")
        return items

    def _image_search(self, query: str, date_restrict: str) -> list[dict]:
        """Call the API with searchType=image to hit the Images tab."""
        resp = self.session.get(self._endpoint, params={
            "key":          self.api_key,
            "cx":           self.cx,
            "q":            query,
            "searchType":   "image",      # ← THIS is what hits the Images tab
            "num":          10,
            "dateRestrict": date_restrict,
            "imgSize":      "large",      # prefer large images (actual shoe photos)
            "safe":         "off",
        }, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise ValueError(data["error"].get("message", str(data["error"])))
        return data.get("items", [])
