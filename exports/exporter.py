# exports/exporter.py
import csv
import json
import os
from datetime import datetime, timezone
from typing import Optional

from database.db import Database
import config


def export(
    db: Database,
    fmt: str = "csv",
    output: str = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
):
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    rows  = db.query(since=since, until=until, limit=999999)
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output is None:
        output = os.path.join(config.EXPORT_DIR, f"leaks_{ts}.{fmt}")

    if fmt == "csv":
        _to_csv(rows, output)
    elif fmt == "json":
        _to_json(rows, output)
    else:
        raise ValueError(f"Unknown format: {fmt}")

    print(f"Exported {len(rows)} rows → {output}")
    return output


def _to_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _to_json(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, default=str)
