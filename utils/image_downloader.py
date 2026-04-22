# utils/image_downloader.py
"""
Downloads sneaker images from scraped URLs and saves them locally.

Folder structure:
  images/
    sneakernews/
      abc123def456.jpg       ← hash of URL used as filename
    instagram/
      ...
    google/
      ...

The local file path is written back into LeakItem.image_path and
also updated in the database.
"""

import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

import config
from scrapers.base import LeakItem

logger = logging.getLogger(__name__)

IMAGES_DIR   = "images"
VALID_EXTS   = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE_MB  = 5
TIMEOUT      = 10
DELAY        = 0.3   # seconds between downloads


class ImageDownloader:
    def __init__(self, base_dir: str = IMAGES_DIR):
        self.base_dir = Path(base_dir)
        self.session  = requests.Session()
        self.session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Referer":    "https://www.google.com/",
        })

    def download_all(self, items: list[LeakItem]) -> tuple[int, int]:
        """
        Download images for a list of LeakItems.
        Sets item.image_path on success.
        Returns (downloaded, skipped) counts.
        """
        downloaded = skipped = 0
        for item in items:
            if not item.image_url:
                skipped += 1
                continue
            path = self._download(item.image_url, source=item.source)
            if path:
                item.image_path = str(path)
                downloaded += 1
            else:
                skipped += 1
            time.sleep(DELAY)
        return downloaded, skipped

    def _download(self, url: str, source: str = "misc") -> Optional[Path]:
        """
        Download a single image. Returns local Path on success, None on failure.
        Skips download if file already exists (deduplication by URL hash).
        """
        if not url or not url.startswith("http"):
            return None

        ext      = self._guess_ext(url)
        filename = self._url_hash(url) + ext
        folder   = self.base_dir / source
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / filename

        # Already downloaded — skip
        if dest.exists() and dest.stat().st_size > 0:
            logger.debug(f"Image already exists: {dest}")
            return dest

        try:
            resp = self.session.get(url, timeout=TIMEOUT, stream=True)
            resp.raise_for_status()

            # Validate content type
            ct = resp.headers.get("Content-Type", "")
            if not ct.startswith("image/"):
                logger.debug(f"Skipping non-image content-type '{ct}': {url}")
                return None

            # Check size before downloading fully
            size = int(resp.headers.get("Content-Length", 0))
            if size > MAX_SIZE_MB * 1024 * 1024:
                logger.debug(f"Image too large ({size} bytes), skipping: {url}")
                return None

            # Write to disk in chunks
            with open(dest, "wb") as f:
                downloaded = 0
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > MAX_SIZE_MB * 1024 * 1024:
                        logger.debug(f"Image exceeded size limit mid-download, skipping: {url}")
                        f.close()
                        dest.unlink(missing_ok=True)
                        return None

            logger.debug(f"Downloaded: {dest}")
            return dest

        except Exception as e:
            logger.warning(f"Image download failed ({url}): {e}")
            dest.unlink(missing_ok=True)
            return None

    @staticmethod
    def _url_hash(url: str) -> str:
        """Short MD5 hash of the URL — used as filename."""
        return hashlib.md5(url.encode()).hexdigest()[:16]

    @staticmethod
    def _guess_ext(url: str) -> str:
        """
        Try to determine file extension from URL.
        Falls back to .jpg if unknown.
        """
        path = urlparse(url).path.lower()
        for ext in VALID_EXTS:
            if path.endswith(ext):
                return ext
        # Check for ?format=webp style params
        if "webp" in url:
            return ".webp"
        if "png" in url:
            return ".png"
        return ".jpg"
