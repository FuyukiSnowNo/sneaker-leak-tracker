# scrapers/base.py
"""
Base scraper class.
Strategy:
  1. Try RSS feed first (fast, structured, polite)
  2. Fall back to HTML scraping if RSS unavailable or empty

Each scraped item now includes:
  image_url  — direct URL to the sneaker image (og:image or first <img>)
  image_path — local file path after downloading (filled by ImageDownloader)
"""

import time
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

import requests
import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

import config

logger = logging.getLogger(__name__)


@dataclass
class LeakItem:
    title: str
    url: str
    source: str
    source_name: str
    summary: str = ""
    published_at: Optional[datetime] = None
    scraped_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    brand: str = "Other"
    hype_score: int = 0
    hype_tier: str = "LOW"
    release_date: str = "TBD"
    tags: list = field(default_factory=list)
    image_url: str = ""       # ← NEW: source image URL
    image_path: str = ""      # ← NEW: local downloaded file path

    def to_dict(self) -> dict:
        return {
            "title":        self.title,
            "url":          self.url,
            "source":       self.source,
            "source_name":  self.source_name,
            "summary":      self.summary,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "scraped_at":   self.scraped_at.isoformat(),
            "brand":        self.brand,
            "hype_score":   self.hype_score,
            "hype_tier":    self.hype_tier,
            "release_date": self.release_date,
            "tags":         ",".join(self.tags),
            "image_url":    self.image_url,
            "image_path":   self.image_path,
        }


class BaseScraper:
    """Override rss_url and/or scrape_html() in subclasses."""

    source_id: str = ""
    source_name: str = ""
    rss_url: str = ""
    base_url: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})

    # ── Public API ────────────────────────────────────────────────────────

    def scrape(self, since: Optional[datetime] = None) -> list[LeakItem]:
        items = []
        try:
            items = self._scrape_rss(since)
            logger.info(f"[{self.source_id}] RSS: {len(items)} items")
        except Exception as e:
            logger.warning(f"[{self.source_id}] RSS failed ({e}), trying HTML")
            try:
                items = self.scrape_html(since)
                logger.info(f"[{self.source_id}] HTML: {len(items)} items")
            except Exception as e2:
                logger.error(f"[{self.source_id}] HTML failed too: {e2}")

        for item in items:
            item.brand        = self._detect_brand(item.title + " " + item.summary)
            item.hype_score   = self._calc_hype(item.title + " " + item.summary)
            item.hype_tier    = self._hype_tier(item.hype_score)
            item.tags         = self._extract_tags(item.title + " " + item.summary)
            item.release_date = self._extract_release_date(item.title + " " + item.summary)
            # Fetch og:image from article page if not already set
            if not item.image_url and item.url:
                item.image_url = self._fetch_og_image(item.url)

        time.sleep(config.REQUEST_DELAY)
        return items

    # ── RSS ───────────────────────────────────────────────────────────────

    def _scrape_rss(self, since: Optional[datetime]) -> list[LeakItem]:
        feed = feedparser.parse(
            self.rss_url,
            request_headers={"User-Agent": config.USER_AGENT}
        )
        if feed.bozo and not feed.entries:
            raise ValueError(f"feedparser error: {feed.bozo_exception}")

        items = []
        for entry in feed.entries[: config.MAX_ITEMS_PER_SOURCE]:
            pub = self._parse_date(entry.get("published", "") or entry.get("updated", ""))
            if since and pub and pub < since:
                continue

            summary = entry.get("summary", "") or entry.get("description", "")
            summary = BeautifulSoup(summary, "lxml").get_text(" ", strip=True)[:500]

            # Try to pull image from RSS media fields first
            image_url = (
                entry.get("media_thumbnail", [{}])[0].get("url", "")
                or entry.get("media_content", [{}])[0].get("url", "")
                or ""
            )

            items.append(LeakItem(
                title        = entry.get("title", "Untitled").strip(),
                url          = entry.get("link", ""),
                source       = self.source_id,
                source_name  = self.source_name,
                summary      = summary,
                published_at = pub,
                image_url    = image_url,
            ))
        return items

    # ── HTML fallback ─────────────────────────────────────────────────────

    def scrape_html(self, since: Optional[datetime]) -> list[LeakItem]:
        resp = self._get(self.base_url)
        soup = BeautifulSoup(resp.text, "lxml")
        items = []

        for article in soup.select("article")[:config.MAX_ITEMS_PER_SOURCE]:
            a = article.find("a", href=True)
            if not a:
                continue
            title = a.get_text(strip=True)
            url   = a["href"]
            if not url.startswith("http"):
                url = self.base_url.rstrip("/") + "/" + url.lstrip("/")
            p       = article.find("p")
            summary = p.get_text(strip=True)[:500] if p else ""
            img     = article.find("img")
            image_url = img.get("src", "") if img else ""

            items.append(LeakItem(
                title       = title,
                url         = url,
                source      = self.source_id,
                source_name = self.source_name,
                summary     = summary,
                image_url   = image_url,
            ))
        return items

    # ── Image helpers ─────────────────────────────────────────────────────

    def _fetch_og_image(self, url: str) -> str:
        """
        Fetches the article page and extracts the og:image meta tag.
        Falls back to first <img> in the article body.
        Returns empty string on failure.
        """
        try:
            resp = self.session.get(url, timeout=8)
            soup = BeautifulSoup(resp.text, "lxml")

            # 1. og:image (most reliable)
            og = soup.find("meta", property="og:image")
            if og and og.get("content"):
                return og["content"].strip()

            # 2. twitter:image
            tw = soup.find("meta", attrs={"name": "twitter:image"})
            if tw and tw.get("content"):
                return tw["content"].strip()

            # 3. First <img> inside <article> or <main>
            container = soup.find("article") or soup.find("main")
            if container:
                img = container.find("img", src=True)
                if img:
                    src = img["src"]
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        from urllib.parse import urlparse
                        base = urlparse(url)
                        src  = f"{base.scheme}://{base.netloc}{src}"
                    return src
        except Exception as e:
            logger.debug(f"og:image fetch failed for {url}: {e}")
        return ""

    # ── Misc helpers ──────────────────────────────────────────────────────

    def _get(self, url: str) -> requests.Response:
        resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _parse_date(s: str) -> Optional[datetime]:
        if not s:
            return None
        try:
            dt = dateparser.parse(s)
            if dt and dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

    @staticmethod
    def _detect_brand(text: str) -> str:
        t = text.lower()
        for brand, keywords in config.BRAND_RULES:
            if any(kw in t for kw in keywords):
                return brand
        return config.DEFAULT_BRAND

    @staticmethod
    def _calc_hype(text: str) -> int:
        t = text.lower()
        score = sum(w for kw, w in config.HYPE_KEYWORDS.items() if kw in t)
        return min(score, 10)

    @staticmethod
    def _hype_tier(score: int) -> str:
        for (lo, hi), tier in config.HYPE_TIERS.items():
            if lo <= score <= hi:
                return tier
        return "LOW"

    @staticmethod
    def _extract_tags(text: str) -> list:
        t = text.lower()
        found = []
        for kw in config.HYPE_KEYWORDS:
            if kw in t and len(kw) > 3:
                found.append(kw.strip())
        for brand, _ in config.BRAND_RULES:
            if brand.lower() in t:
                found.append(brand)
        return list(dict.fromkeys(found))[:8]

    @staticmethod
    def _extract_release_date(text: str) -> str:
        import re
        patterns = [
            r'\b(january|february|march|april|may|june|july|august|'
            r'september|october|november|december)\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
            r'\b\d{4}-\d{2}-\d{2}\b',
            r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\.?\s+\d{1,2}\b',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(0).strip().title()
        return "TBD"
