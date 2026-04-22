# scrapers/sneakernews.py
from scrapers.base import BaseScraper, LeakItem
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional

class SneakerNewsScraper(BaseScraper):
    source_id   = "sneakernews"
    source_name = "Sneaker News"
    rss_url     = "https://sneakernews.com/feed/"
    base_url    = "https://sneakernews.com"

    def scrape_html(self, since: Optional[datetime]) -> list[LeakItem]:
        resp = self._get("https://sneakernews.com/category/sneaker-release-dates/")
        soup = BeautifulSoup(resp.text, "lxml")
        items = []
        for card in soup.select(".post-block, article.post")[:50]:
            a     = card.select_one("h2 a, h3 a, .post-block__title a")
            if not a:
                continue
            title = a.get_text(strip=True)
            url   = a["href"]
            p     = card.select_one(".post-block__content, .entry-summary p")
            summary = p.get_text(strip=True)[:400] if p else ""
            items.append(LeakItem(
                title=title, url=url,
                source=self.source_id, source_name=self.source_name,
                summary=summary,
            ))
        return items
