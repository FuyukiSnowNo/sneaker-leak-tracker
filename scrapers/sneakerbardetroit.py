# scrapers/sneakerbardetroit.py
from scrapers.base import BaseScraper

class SneakerBarDetroitScraper(BaseScraper):
    source_id   = "sneakerbardetroit"
    source_name = "Sneaker Bar Detroit"
    rss_url     = "https://sneakerbardetroit.com/feed/"
    base_url    = "https://sneakerbardetroit.com"
