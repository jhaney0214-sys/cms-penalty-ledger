#!/usr/bin/env python3
"""When did each home's current owner take it over? CMS's change-of-ownership file.

    python tools/ownership.py           # once a quarter: fetch and cache
    python tools/ownership.py --offline # print what the cache says

The chain pages need this. CMS's Provider Information file names the chain a
home belongs to today and not when that began, so a 2019 fine at a home bought
in 2023 would sit under the buyer. CMS's *Skilled Nursing Facility Change of
Ownership* (data.cms.gov, quarterly, a U.S. government work) lists every
change since 2016-01-01 with the home's certification number (`CCN - BUYER`)
and an effective date. Only the latest date per home is kept: a fine dated
before it was against an earlier owner.

Measured 2026-10-17 on the file of 2026-07-17: 5,227 rows, effective
2016-01-01 to 2026-02-01; 5,171 of 5,225 homes join the provider file, and all
86 homes it marks "changed owner in the last 12 months" are in it. 27% of the
fine dollars at chained homes ($325M of $1.21B) are dated before the home's
latest change of owner.

What it cannot say, both ways: whether a change was between two companies
under the same chain (a fine before the date is shown as an earlier owner's
either way, moving dollars away from the chain), and changes the file does
not hold. The 2026-06-01 edition runs to changes effective by 2026-02-01, and
some homes named for Journey Healthcare, which bought in Georgia in 2024, have
no row, so their earlier owners' fines still sit under Journey.

The file is not UTF-8 (it carries Windows-1252 non-breaking spaces in names);
only the two columns read here are kept.
"""

import argparse
import csv
import datetime
import gzip
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

import snapshot_cms  # noqa: E402

CATALOG = "https://data.cms.gov/data.json"
TITLE = "Skilled Nursing Facility Change of Ownership : "
CACHE = os.path.join(HERE, "data", "cms-provider", "ownership_changes.csv.gz")
KEEP = ("ccn", "owner_since", "edition")


def newest(catalog):
    """(edition date, CSV URL) of the newest change-of-ownership file. The
    dataset id changes with every edition, so it is found by title."""
    best = None
    for ds in catalog.get("dataset", []):
        title = ds.get("title", "")
        if not title.startswith(TITLE):
            continue
        edition = title[len(TITLE):].strip()
        urls = [d.get("downloadURL") for d in ds.get("distribution", [])
                if (d.get("downloadURL") or "").lower().endswith(".csv")]
        if urls and (best is None or edition > best[0]):
            best = (edition, urls[0])
    if best is None:
        raise ValueError("no %r dataset in the catalog" % TITLE.strip(" :"))
    return best


def _date(text):
    m, d, y = text.strip().split("/")
    return datetime.date(int(y), int(m), int(d)).isoformat()


def latest(raw_csv):
    """{ccn: latest effective date (ISO)} from the file's text. A missing
    column is an error, never a guess."""
    reader = csv.reader(io.StringIO(raw_csv))
    head = [h.strip().upper() for h in next(reader)]
    for col in ("CCN - BUYER", "EFFECTIVE DATE"):
        if col not in head:
            raise ValueError("change-of-ownership file has no column %s" % col)
    ci, di = head.index("CCN - BUYER"), head.index("EFFECTIVE DATE")
    out = {}
    for rec in reader:
        if len(rec) <= max(ci, di) or not rec[ci].strip().strip("0"):
            continue
        ccn, when = rec[ci].strip().upper().zfill(6), _date(rec[di])
        if when > out.get(ccn, ""):
            out[ccn] = when
    return out


def fetch(get=snapshot_cms._get):
    raw, _ = snapshot_cms._get_or(get, CATALOG)
    edition, url = newest(json.loads(raw.decode("utf-8")))
    raw, _ = snapshot_cms._get_or(get, url)
    since = latest(raw.decode("cp1252", errors="replace"))
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with gzip.open(CACHE, "wt", encoding="utf-8", newline="") as handle:
        w = csv.writer(handle)
        w.writerow(KEEP)
        w.writerows((c, d, edition) for c, d in sorted(since.items()))
    return since, edition


def cached(path=CACHE):
    """({ccn: owner_since}, edition), or ({}, None) when nothing is cached."""
    if not os.path.exists(path):
        return {}, None
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {r["ccn"]: r["owner_since"] for r in rows}, (rows[0]["edition"] if rows else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description="CMS change-of-ownership dates per home")
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args(argv)
    since, edition = cached() if a.offline else fetch()
    dates = sorted(since.values())
    print("%d homes with a change of owner since 2016, edition %s, effective %s to %s" % (
        len(since), edition, dates[0] if dates else "-", dates[-1] if dates else "-"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
