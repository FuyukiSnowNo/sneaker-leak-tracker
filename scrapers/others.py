# scrapers/sneakerfreaker.py
from scrapers.base import BaseScraper

class SneakerFreakerScraper(BaseScraper):
    source_id   = "sneakerfreaker"
    source_name = "Sneaker Freaker"
    rss_url     = "https://www.sneakerfreaker.com/feed"
    base_url    = "https://www.sneakerfreaker.com"


# scrapers/hypebeast.py
from scrapers.base import BaseScraper

class HypebeastScraper(BaseScraper):
    source_id   = "hypebeast"
    source_name = "Hypebeast"
    rss_url     = "https://hypebeast.com/footwear/feed"
    base_url    = "https://hypebeast.com/footwear"


# scrapers/kicksonfire.py
from scrapers.base import BaseScraper

class KicksOnFireScraper(BaseScraper):
    source_id   = "kicksonfire"
    source_name = "Kicks on Fire"
    rss_url     = "https://www.kicksonfire.com/feed/"
    base_url    = "https://www.kicksonfire.com"
