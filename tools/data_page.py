#!/usr/bin/env python3
"""The two history files as downloads, with what every column means.

    python tools/data_page.py     # writes docs/data.html and docs/download/

A reporter, a lawyer or a researcher who uses this needs three things a page
per home does not give: the whole file, a definition of each column, and a
line to cite. This writes all three from the files themselves, so the counts
on the page are the counts in the download and a column added to a file
without a definition here stops the build.

The downloads are byte-for-byte the files under snapshots/ and the page
prints each one's SHA-256, so a copy passed along can be checked against the
one served.
"""

import collections
import csv
import gzip
import hashlib
import html
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

import cms_ledger  # noqa: E402
import ratings_history  # noqa: E402

DOCS = os.path.join(HERE, "docs")
SITE = "https://penalty-ledger.pages.dev"
REPOSITORY = "https://github.com/jhaney0214-sys/cms-penalty-ledger"

#: column -> what it holds. Every column of each file must be here.
PENALTY_COLUMNS = collections.OrderedDict([
    ("ccn", "CMS Certification Number of the home, six characters, zero-padded."),
    ("name", "The home's name as CMS last published it with this penalty."),
    ("address", "Street address, as CMS published it."),
    ("city", "City."),
    ("state", "Two-letter state or territory code."),
    ("zip", "ZIP code."),
    ("date", "The penalty's date in CMS's file (YYYY-MM-DD)."),
    ("kind", "Fine (a civil money penalty) or Payment Denial (a denial of payment for new admissions). "
             "The two are never summed."),
    ("fine_id", "CMS's identifier for a fine, in editions that carry one; blank before CMS published it "
                "and for payment denials."),
    ("amount", "A fine's amount in dollars, as last published. Blank for a payment denial."),
    ("denial_start", "The date a payment denial began. Blank for a fine."),
    ("denial_days", "The length of a payment denial in days, as last published. Blank for a fine."),
    ("first_amount", "The amount as FIRST published, when CMS later revised it; blank when it never changed."),
    ("first_denial_days", "The denial's length as first published, when CMS later revised it."),
    ("revisions", "How many times CMS changed the amount or length while it listed the penalty."),
    ("first_seen", "The date of the first archived monthly edition that lists the penalty."),
    ("last_seen", "The date of the last archived edition, or weekly capture, that lists it."),
    ("appearances", "How many editions list it."),
    ("gaps", "How many times it left CMS's file and came back."),
    ("in_latest", "yes if CMS's latest file still lists it; no if CMS has stopped publishing it."),
])
RATING_COLUMNS = collections.OrderedDict([
    ("ccn", "CMS Certification Number of the home."),
    ("from_edition", "The first archived monthly edition in this run of unchanged ratings."),
    ("to_edition", "The last edition in the run."),
    ("editions", "How many editions the run covers."),
    ("overall", "Overall star rating, 1 to 5; blank where CMS published none."),
    ("inspection", "Health inspection rating."),
    ("quality", "Quality measures rating."),
    ("staffing", "Staffing rating."),
    ("in_latest", "yes if the run reaches CMS's latest archived edition."),
])

FILES = (
    {"key": "penalties", "source": cms_ledger.HISTORY, "name": "penalties_history.csv.gz",
     "title": "Every penalty in CMS's archive", "columns": PENALTY_COLUMNS,
     "row": "One row for each penalty CMS has published against a nursing home, with the first and last "
            "edition that listed it and whether CMS still does."},
    {"key": "ratings", "source": ratings_history.HISTORY, "name": "ratings_history.csv.gz",
     "title": "Star ratings, edition by edition", "columns": RATING_COLUMNS,
     "row": "One row for each stretch of editions in which a home's four ratings did not change."},
)


def describe(spec):
    """Counts and checks for one file. A column with no definition, or a
    definition with no column, is an error."""
    with open(spec["source"], "rb") as handle:
        raw = handle.read()
    rows = list(csv.reader(gzip.decompress(raw).decode("utf-8").splitlines()))
    head, body = rows[0], rows[1:]
    if head != list(spec["columns"]):
        raise ValueError("%s: columns %s are not the ones defined (%s)" % (
            spec["name"], head, list(spec["columns"])))
    out = {"name": spec["name"], "rows": len(body), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
           "homes": len({r[0] for r in body})}
    if spec["key"] == "penalties":
        i = {c: n for n, c in enumerate(head)}
        out.update(first=min(r[i["date"]] for r in body), last=max(r[i["date"]] for r in body),
                   through=max(r[i["last_seen"]] for r in body),
                   dropped=sum(r[i["in_latest"]] == "no" for r in body),
                   fines=sum(r[i["kind"]] == "Fine" for r in body))
    else:
        out.update(first=min(r[1] for r in body), last=max(r[2] for r in body), through=max(r[2] for r in body))
    return out


def _n(value):
    return "{:,}".format(value)


def page(facts):
    e = html.escape
    p = facts["penalties"]
    through = max(f["through"] for f in facts.values())
    parts = [
        "<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>Download the data: every CMS nursing-home penalty since %s</title>" % p["first"][:4],
        '<meta name="description" content="%s penalties against %s nursing homes, %s of which CMS no longer '
        'publishes, as one file with every column defined and a line to cite.">' % (
            _n(p["rows"]), _n(p["homes"]), _n(p["dropped"])),
        '<link rel="stylesheet" href="facilities/style.css">',
        '<link rel="canonical" href="%s/data">' % SITE,
        '</head><body><main class="page">',
        '<p class="meta"><a href="./">Nursing Home Penalty Ledger</a> &rsaquo; The data</p>',
        "<h1>Download the data</h1>",
        "<p>Everything the pages on this site show comes from two files. Both are here whole, with what each "
        "column holds. They are built from the monthly editions the Centers for Medicare &amp; Medicaid "
        "Services publishes and then archives; CMS's current file keeps about three years, and these keep "
        "every edition back to January 2019.</p>",
    ]
    for spec in FILES:
        f = facts[spec["key"]]
        parts += [
            "<h2>%s</h2>" % e(spec["title"]),
            "<p>%s</p>" % e(spec["row"]),
            '<p><a href="download/%s"><strong>%s</strong></a> &middot; %s rows &middot; %s homes &middot; '
            "%.1f MB, gzip-compressed CSV, UTF-8</p>" % (e(f["name"]), e(f["name"]), _n(f["rows"]),
                                                         _n(f["homes"]), f["bytes"] / 1e6),
        ]
        if spec["key"] == "penalties":
            parts.append("<p>Penalties dated %s to %s, through CMS's file of %s. %s are fines and %s are payment "
                         "denials. <strong>%s of the %s are no longer in CMS's current file.</strong></p>" % (
                             f["first"], f["last"], f["through"], _n(f["fines"]), _n(f["rows"] - f["fines"]),
                             _n(f["dropped"]), _n(f["rows"])))
        else:
            parts.append("<p>Editions %s to %s.</p>" % (f["first"], f["last"]))
        parts.append('<div class="table-wrap"><table><thead><tr><th>Column</th><th>What it holds</th></tr>'
                     "</thead><tbody>")
        parts += ["<tr><td><code>%s</code></td><td>%s</td></tr>" % (e(c), e(d)) for c, d in spec["columns"].items()]
        parts.append("</tbody></table></div>")
        parts.append('<p class="meta">SHA-256 <code>%s</code></p>' % f["sha256"])
    parts += [
        "<h2>How to cite it</h2>",
        "<p>Nursing Home Penalty Ledger, penalty history through CMS's file of %s, %s/data. Built from the "
        "Centers for Medicare &amp; Medicaid Services' Provider Data Catalog and its archive of monthly "
        "editions (data.cms.gov).</p>" % (through, SITE),
        "<p>Give the date: the files grow each month, and a count quoted without one cannot be checked. "
        "For a single home, cite its page, which links each penalty to the CMS edition that carried it.</p>",
        "<h2>What it is, and what it is not</h2>",
        "<ul>",
        "<li>The facts are CMS's public record. This site arranges them and adds nothing: every row can be "
        "found in the CMS edition named by its <code>first_seen</code> date.</li>",
        "<li>A penalty CMS no longer publishes was not withdrawn or overturned by that. CMS's file is a rolling "
        "window, and a row leaves it by age.</li>",
        "<li>An amount can change while CMS lists it. <code>amount</code> is the last one published and "
        "<code>first_amount</code> the first; a source quoting either may be right.</li>",
        "<li>Fines and payment denials are different penalties and are never added together here.</li>",
        "<li>A star rating moves when a home changes and also when CMS changes its method. The file cannot "
        "tell the two apart.</li>",
        "<li>In CMS's edition of 2019-10-09, 101 home numbers were stored as numbers "
        "(<code>14E169</code> as <code>1.40E+170</code>). Each is restored here where exactly one home it "
        "could be is known from the editions on either side.</li>",
        "</ul>",
        '<p class="meta">Found an error? Open an issue at <a href="%s/issues">the repository</a>. The scripts '
        "that build both files are there too.</p>" % REPOSITORY,
        "</main></body></html>",
    ]
    return "\n".join(parts) + "\n"


def build(docs=DOCS):
    facts = {spec["key"]: describe(spec) for spec in FILES}
    out = os.path.join(docs, "download")
    os.makedirs(out, exist_ok=True)
    for spec in FILES:
        shutil.copyfile(spec["source"], os.path.join(out, spec["name"]))
    with open(os.path.join(docs, "data.html"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(page(facts))
    return facts


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
