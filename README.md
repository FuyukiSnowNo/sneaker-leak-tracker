# 👟 Nike Sneaker Leak Tracker

Automated scraper that monitors sneaker news sites for leaks, upcoming releases, and hype trends — over any time period you define.

## What it does

- Scrapes **Sneaker News**, **Sneaker Bar Detroit**, **Sneaker Freaker**, **Kicks on Fire**, and **Hypebeast** on a schedule
- Stores everything in a local **SQLite database**
- Detects brand, hype keywords, and release dates automatically
- Generates **stats reports**: leak frequency, top brands, hype trends over time
- Exports to **CSV / JSON** for spreadsheets or dashboards

---

## Setup

```bash
git clone https://github.com/FuyukiSnowNo/sneaker-leak-tracker
cd sneaker-leak-tracker

python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Run

### One-time scan
```bash
python main.py scan
```

### Scan a specific date range
```bash
python main.py scan --from 2025-01-01 --to 2025-04-21
```

### Start the scheduler (runs every N hours)
```bash
python main.py schedule --interval 6
```

### Generate a stats report
```bash
python main.py stats --from 2025-01-01 --to 2025-04-21
```

### Export data
```bash
python main.py export --format csv --output exports/leaks.csv
python main.py export --format json --output exports/leaks.json
```

---

## Config

Edit `config.py` to toggle sources, adjust scrape intervals, and tune hype keywords.

---

## Project Structure

```
sneaker-leak-tracker/
├── main.py                  # CLI entry point
├── config.py                # Settings & keywords
├── requirements.txt
├── scrapers/
│   ├── base.py              # Base scraper class (RSS + HTML fallback)
│   ├── sneakernews.py
│   ├── sneakerbardetroit.py
│   ├── sneakerfreaker.py
│   ├── hypebeast.py
│   └── kicksonfire.py
├── database/
│   └── db.py                # SQLite handler
├── stats/
│   └── analyzer.py          # Stats, trends, reports
├── scheduler/
│   └── runner.py            # Periodic scraping loop
└── exports/                 # CSV / JSON output folder
```

---

## Database Schema

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Primary key |
| `title` | TEXT | Sneaker name / article title |
| `summary` | TEXT | Description |
| `url` | TEXT | Source URL (unique) |
| `source` | TEXT | Site name |
| `brand` | TEXT | Detected brand |
| `hype_score` | INTEGER | 0–10 hype keyword score |
| `release_date` | TEXT | Parsed release date |
| `scraped_at` | TEXT | When we captured it |
| `published_at` | TEXT | Original publish date |
| `tags` | TEXT | Comma-separated tags |

---

## Stats Output Example

```
📊 SNEAKER LEAK REPORT — Jan 1 → Apr 21 2025
──────────────────────────────────────────────
Total leaks captured:     847
Unique brands:            23
Avg leaks/day:            7.3
Peak day:                 Mar 12 (31 leaks)

TOP BRANDS
  1. Nike / Dunk          312  (36.8%)
  2. Jordan               198  (23.4%)
  3. Adidas / Yeezy       156  (18.4%)
  4. New Balance           89  (10.5%)
  5. Other                 92  (10.9%)

HIGH HYPE LEAKS (score 7+): 124
  Top: Travis Scott x Nike SB Dunk Low (score: 9)
       Off-White x Air Jordan 4 (score: 8)

MOST ACTIVE SOURCES
  sneakernews.com         341
  sneakerbardetroit.com   289
  hypebeast.com           217
```
