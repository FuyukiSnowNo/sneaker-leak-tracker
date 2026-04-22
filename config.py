# ─────────────────────────────────────────────
#  config.py — Sneaker Leak Tracker Settings
# ─────────────────────────────────────────────

# ── Sources ───────────────────────────────────
# Set enabled=False to skip a source
SOURCES = [
    {
        "id": "sneakernews",
        "name": "Sneaker News",
        "rss": "https://sneakernews.com/feed/",
        "base_url": "https://sneakernews.com",
        "enabled": True,
    },
    {
        "id": "sneakerbardetroit",
        "name": "Sneaker Bar Detroit",
        "rss": "https://sneakerbardetroit.com/feed/",
        "base_url": "https://sneakerbardetroit.com",
        "enabled": True,
    },
    {
        "id": "sneakerfreaker",
        "name": "Sneaker Freaker",
        "rss": "https://www.sneakerfreaker.com/feed",
        "base_url": "https://www.sneakerfreaker.com",
        "enabled": True,
    },
    {
        "id": "hypebeast",
        "name": "Hypebeast",
        "rss": "https://hypebeast.com/footwear/feed",
        "base_url": "https://hypebeast.com",
        "enabled": True,
    },
    {
        "id": "kicksonfire",
        "name": "Kicks on Fire",
        "rss": "https://www.kicksonfire.com/feed/",
        "base_url": "https://www.kicksonfire.com",
        "enabled": True,
    },
]

# ── Database ───────────────────────────────────
DATABASE_PATH = "leaks.db"

# ── Scheduler ─────────────────────────────────
# Default interval in hours when running `schedule` mode
DEFAULT_INTERVAL_HOURS = 6

# ── Scraper ────────────────────────────────────
REQUEST_TIMEOUT = 15       # seconds
REQUEST_DELAY = 1.5        # seconds between requests (be polite)
MAX_ITEMS_PER_SOURCE = 50  # max RSS items to parse per run
USER_AGENT = (
    "Mozilla/5.0 (compatible; SneakerLeakTracker/1.0; "
    "+https://github.com/FuyukiSnowNo/sneaker-leak-tracker)"
)

# ── Brand Detection ────────────────────────────
# Checked in order — first match wins
BRAND_RULES = [
    ("Yeezy",       ["yeezy"]),
    ("Jordan",      ["jordan", "aj1", "aj2", "aj3", "aj4", "aj5", "aj6",
                     "air jordan", "jumpman"]),
    ("Nike",        ["nike", "dunk", "air max", "air force", "af1", "blazer",
                     "cortez", "pegasus", "vaporfly", "zoom"]),
    ("Adidas",      ["adidas", "ultraboost", "nmd", "samba", "gazelle",
                     "superstar", "stan smith", "forum"]),
    ("New Balance", ["new balance", "nb 9060", "nb550", "nb2002", "nb1906",
                     "990v", "993", "574"]),
    ("Asics",       ["asics", "gel-", "gel lyte"]),
    ("Puma",        ["puma", "suede", "clyde"]),
    ("Reebok",      ["reebok", "classic leather", "question"]),
    ("Converse",    ["converse", "chuck taylor", "chuck 70"]),
    ("Vans",        ["vans", "old skool", "sk8-hi", "era"]),
]
DEFAULT_BRAND = "Other"

# ── Hype Keywords ──────────────────────────────
# Each matched keyword adds its weight to the hype score (max 10)
HYPE_KEYWORDS = {
    # Collab signals (high weight)
    "travis scott":   3,
    "off-white":      3,
    "off white":      3,
    "sacai":          3,
    "fear of god":    3,
    "fragment":       2,
    "union":          2,
    "cactus jack":    3,
    "a$ap":           2,
    "pharrell":       2,
    "virgil":         2,
    "kaws":           2,
    "clot":           2,
    "atmos":          2,
    "concepts":       2,
    "bodega":         2,
    "stüssy":         2,
    "stussy":         2,
    "supreme":        3,
    "palace":         2,

    # Release signals (medium weight)
    "limited":        1,
    "exclusive":      1,
    "raffle":         2,
    "lottery":        1,
    "sample":         2,
    "unreleased":     2,
    "prototype":      2,
    "friends & family": 3,
    "friends and family": 3,
    "pe ":            2,   # Player Exclusive
    "player exclusive": 2,

    # Collector signals (lower weight)
    "og":             1,
    "retro":          1,
    "grail":          2,
    "deadstock":      1,
    "ds ":            1,
    "colorway":       0,   # neutral — just marks it
}

# Hype tiers
HYPE_TIERS = {
    (0, 1):   "LOW",
    (2, 4):   "MEDIUM",
    (5, 7):   "HIGH",
    (8, 99):  "GRAIL",
}

# ── Instagram ─────────────────────────────────
# Accounts to monitor (no @ needed)
INSTAGRAM_ACCOUNTS = [
    "sneakerbardetroit",
    "sneakernews",
    "sneakerfreakermag",
    "donniebsoles",
]

# Your Instagram credentials (used to load/save session)
# Run once: instaloader --login YOUR_USERNAME  to create a session file
# After that, leave password blank — session file handles auth
INSTAGRAM_USERNAME = "jokerices@gmail.com"
INSTAGRAM_PASSWORD = "*hcGFh!nuHm;B8s"   # leave blank after first login

# ── Google Custom Search API ───────────────────
# Get your key: https://console.cloud.google.com/  (enable Custom Search API)
# Get your CX:  https://programmablesearchengine.google.com/
GOOGLE_API_KEY = "AIzaSyApgOVgx9kgCgPf57Nvz1NodG7bW5RiVWg"
GOOGLE_CX      = "80f1a2f5b491a4823"

# These are the exact queries that will be run each weekly scan
# Each query = 1 API credit (free tier = 100/day)
GOOGLE_SEARCH_QUERIES = [
    "nike shoes leaked -kit -uniform -jersey",
    "jordan sneaker leak 2025",
    "adidas yeezy leak 2025",
    "sneaker leak unreleased colorway 2025",
    "new balance leak upcoming release 2025",
    "travis scott sneaker collab leak",
    "off-white nike unreleased 2025",
    "sneaker exclusive friends family leak",
]

# ── Weekly scan schedule ───────────────────────
# Day of week for weekly Instagram + Google scan
# Options: "monday" "tuesday" ... "sunday"
WEEKLY_SCAN_DAY  = "saturday"
WEEKLY_SCAN_TIME = "05:00"   # 24h format, local time

# ── Export ─────────────────────────────────────
EXPORT_DIR = "exports"

# ── Logging ────────────────────────────────────
LOG_LEVEL = "INFO"   # DEBUG | INFO | WARNING | ERROR
