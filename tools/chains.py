#!/usr/bin/env python3
"""Whose homes are these? CMS's chain names set against the penalty history.

    python tools/chains.py             # fetch this month's provider file once, then report
    python tools/chains.py --offline   # report from the copy already on disk

A home's page answers "what has this home been fined". The question after it
is "who runs it, and what about their other homes", and nothing here answers
that yet. CMS's Provider Information file names a chain for each home that
belongs to one (`Chain Name`, `Chain ID`), and this reads it against the
penalty history to see what an owner page would have to stand on before any
page is built.

Written 2026-10-13. A measurement, not a page: it writes nothing under docs/.

## What the chain column is, and is not

It is CMS's own grouping of homes under one affiliated entity, as of the
month the file was published. It is not ownership history. A fine from 2019
is counted under the chain that has the home TODAY, which may have bought it
since; the provider file's `Provider Changed Ownership in Last 12 Months`
flag is counted below so the size of that problem is at least visible. Any
page built from this has to say so on the page.
"""

import argparse
import collections
import csv
import gzip
import io
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

import cms_ledger  # noqa: E402
import snapshot_cms  # noqa: E402

PROVIDER_INFO = "4pq5-n9py"
CACHE = os.path.join(HERE, "data", "cms-provider")
KEEP = ("ccn", "name", "state", "ownership_type", "chain_name", "chain_id", "changed_owner", "processed")
#: Header names in the current file, matched without regard to case.
COLUMNS = {
    "ccn": "cms certification number (ccn)", "name": "provider name", "state": "state",
    "ownership_type": "ownership type", "chain_name": "chain name", "chain_id": "chain id",
    "changed_owner": "provider changed ownership in last 12 months", "processed": "processing date",
}


def slim(raw_csv):
    """The eight columns kept, from the provider file's text. An unrecognised
    header is an error, never a guess."""
    reader = csv.reader(io.StringIO(raw_csv))
    head = [h.strip().lower() for h in next(reader)]
    missing = [v for v in COLUMNS.values() if v not in head]
    if missing:
        raise ValueError("provider file has no column %s" % ", ".join(missing))
    idx = [head.index(COLUMNS[k]) for k in KEEP]
    return [dict(zip(KEEP, (rec[i].strip() for i in idx))) for rec in reader if rec]


def fetch(get=snapshot_cms._get):
    meta = snapshot_cms.resolve(PROVIDER_INFO, get)
    raw, _ = snapshot_cms._get_or(get, meta["url"])
    rows = slim(raw.decode("utf-8-sig"))
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "provider_chains.csv.gz")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, KEEP)
        w.writeheader()
        w.writerows(rows)
    return rows


def cached():
    path = os.path.join(CACHE, "provider_chains.csv.gz")
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def figures(homes, history):
    """What an owner page would rest on. `homes` are provider rows, `history`
    the penalty history rows."""
    by_ccn = {h["ccn"].upper().zfill(6): h for h in homes}
    fines = collections.Counter()
    count = collections.Counter()
    unmatched = 0
    for row in history:
        ccn = row["ccn"].upper().zfill(6)
        if ccn not in by_ccn:
            unmatched += 1
            continue
        count[ccn] += 1
        fines[ccn] += float(row["amount"]) if row["amount"] else 0.0
    chains = collections.defaultdict(list)
    for ccn, h in by_ccn.items():
        if h["chain_id"]:
            chains[h["chain_id"]].append(ccn)
    in_chain = [c for members in chains.values() for c in members]
    alone = [c for c in by_ccn if not by_ccn[c]["chain_id"]]

    def per_home(ccns):
        return sum(fines[c] for c in ccns) / len(ccns) if ccns else 0.0

    table = []
    for chain_id, members in chains.items():
        names = collections.Counter(by_ccn[c]["chain_name"] for c in members)
        table.append({"chain_id": chain_id, "name": names.most_common(1)[0][0], "names": len(names),
                      "homes": len(members), "fined_homes": sum(1 for c in members if count[c]),
                      "penalties": sum(count[c] for c in members),
                      "fines": sum(fines[c] for c in members)})
    return {
        "homes": len(by_ccn), "in_chain": len(in_chain), "chains": len(chains),
        "single_home_chains": sum(1 for m in chains.values() if len(m) == 1),
        "ids_with_two_names": sum(1 for t in table if t["names"] > 1),
        "changed_owner": sum(1 for h in by_ccn.values() if h["changed_owner"].upper().startswith("Y")),
        "history_rows": len(history), "history_unmatched": unmatched,
        "fines_per_home_chain": per_home(in_chain), "fines_per_home_alone": per_home(alone),
        "share_of_fines_chain": (sum(fines[c] for c in in_chain) / sum(fines.values())) if fines else 0.0,
        "table": sorted(table, key=lambda t: -t["fines"]),
        "processed": sorted({h["processed"] for h in homes})[-1] if homes else "",
    }


def text(f, top=10):
    money = lambda x: "${:,.0f}".format(x)  # noqa: E731
    lines = [
        "CMS provider file processed %s, against the penalty history" % f["processed"],
        "",
        "  homes in the provider file           %6d" % f["homes"],
        "  of them in a chain                   %6d  (%.0f%%)" % (f["in_chain"], 100.0 * f["in_chain"] / f["homes"]),
        "  chains                               %6d  (%d of them one home in this file)" % (
            f["chains"], f["single_home_chains"]),
        "  chain ids carrying two names         %6d" % f["ids_with_two_names"],
        "  homes that changed owner in 12 months %5d" % f["changed_owner"],
        "  penalty rows                         %6d  (%d for homes no longer in the provider file)" % (
            f["history_rows"], f["history_unmatched"]),
        "",
        "  fines since 2016 per home, chain     %s" % money(f["fines_per_home_chain"]),
        "  fines since 2016 per home, no chain  %s" % money(f["fines_per_home_alone"]),
        "  share of all matched fines, chains   %.0f%%" % (100.0 * f["share_of_fines_chain"]),
        "",
        "  The %d chains with the most in fines, counted under today's chain:" % top,
    ]
    for t in f["table"][:top]:
        lines.append("    %-44s %4d homes  %4d fined  %12s" % (t["name"][:44], t["homes"], t["fined_homes"],
                                                                 money(t["fines"])))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="CMS chain names against the penalty history")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args(argv)
    homes = cached() if a.offline else fetch()
    with gzip.open(cms_ledger.HISTORY, "rt", encoding="utf-8", newline="") as handle:
        history = list(csv.DictReader(handle))
    print(text(figures(homes, history), a.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
