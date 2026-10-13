#!/usr/bin/env python3
"""A page for each nursing-home chain: its homes, and what each was penalised.

    python tools/chains.py          # once a month: fetch CMS's provider file
    python tools/chain_pages.py     # writes docs/chains/

A home's page answers "what was this home penalised". The question after it
is "who runs it, and how have their other homes done", and CMS's Provider
Information file names a chain for about seven homes in ten.

## The one thing every page here has to say

**The chain is today's.** CMS's file says which chain a home belongs to in
the month it was published and nothing about when that began. A fine from
2019 is listed under whoever has the home now, who may have bought it since.
(CMS does publish change-of-ownership dates in another dataset, which
this does not read yet: see the README.) So no page here says a chain "was fined" anything: it says what the homes it
has today were fined, and says that in the first paragraph, above the table.

Chains are listed alphabetically, never ranked. A total is not a rate: a
chain with 300 homes has more of everything than one with three, and no
figure here is adjusted for size, state or the kind of resident.

Written 2026-10-13 on the branch `chain-pages`. Not linked from any other
page and not in the sitemap, and the weekly task does not build it.
"""

import collections
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

import chains  # noqa: E402
import facility_pages  # noqa: E402
import findings  # noqa: E402

OUT = os.path.join(HERE, "docs", "chains")
SITE = facility_pages.SITE
CHAIN_FILE = re.compile(r"^[0-9]+-[a-z0-9-]*\.html$")

TODAY = ("<strong>These are the homes CMS lists under this chain today.</strong> CMS's file does not say when "
         "each joined it. A penalty from before a home changed hands is still shown against the home, and so "
         "appears here; it is not a penalty against this chain's management.")


def page_name(chain_id, name):
    return "%s-%s.html" % (chain_id, facility_pages.slug(name))


def gather(homes, history):
    """{chain_id: {"name", "homes": [per-home dict]}} from provider rows and
    penalty history rows."""
    by_ccn = collections.defaultdict(list)
    for row in history:
        by_ccn[row["ccn"].upper().zfill(6)].append(row)
    out = {}
    for h in homes:
        if not h["chain_id"]:
            continue
        ccn = h["ccn"].upper().zfill(6)
        rows = by_ccn.get(ccn, [])
        fines = [r for r in rows if r["kind"] == "Fine"]
        chain = out.setdefault(h["chain_id"], {"id": h["chain_id"], "name": h["chain_name"], "homes": []})
        chain["homes"].append({
            "ccn": ccn, "name": h["name"], "state": h["state"],
            "changed_owner": h["changed_owner"].upper().startswith("Y"),
            "fines": len(fines), "dollars": sum(float(r["amount"] or 0) for r in fines),
            "denials": len(rows) - len(fines),
            "dropped": sum(1 for r in rows if r["in_latest"] == "no"),
            "first": min((r["date"] for r in rows), default=""),
        })
    for chain in out.values():
        chain["homes"].sort(key=lambda x: (x["state"], x["name"]))
    return out


def totals(chain):
    homes = chain["homes"]
    return {"homes": len(homes), "penalised": sum(1 for h in homes if h["fines"] or h["denials"]),
            "fines": sum(h["fines"] for h in homes), "dollars": sum(h["dollars"] for h in homes),
            "denials": sum(h["denials"] for h in homes), "dropped": sum(h["dropped"] for h in homes),
            "changed": sum(1 for h in homes if h["changed_owner"]),
            "states": len({h["state"] for h in homes})}


def _head(title, description, canonical):
    e = html.escape
    return ["<!DOCTYPE html>", '<html lang="en"><head><meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>%s</title>" % e(title), '<meta name="description" content="%s">' % e(description),
            '<link rel="stylesheet" href="../facilities/style.css">',
            '<link rel="canonical" href="%s">' % e(canonical), '</head><body><main class="page">']


def chain_page(chain, processed, pages):
    """`pages` is {ccn: file name} for the homes that have a page."""
    e, t = html.escape, totals(chain)
    name = facility_pages.display(chain["name"])
    money = facility_pages.money
    parts = _head("%s: its nursing homes and their CMS penalties" % name,
                  "The %d nursing homes CMS lists under %s today, and every penalty CMS has published "
                  "against each." % (t["homes"], name),
                  "%s/chains/%s" % (SITE, page_name(chain["id"], chain["name"])[:-5]))
    parts += [
        '<p class="meta"><a href="../">Nursing Home Penalty Ledger</a> &rsaquo; <a href="./">Chains</a></p>',
        "<h1>%s</h1>" % e(name),
        "<p>%d nursing homes in %d state%s, in CMS's provider file of %s.</p>" % (
            t["homes"], t["states"], "" if t["states"] == 1 else "s", e(processed)),
        "<p>%s</p>" % TODAY,
        "<p>CMS's archive holds %s fines totalling %s and %s payment denials against these homes, at %d of "
        "the %d. CMS's current file no longer shows %s of those penalties.%s</p>" % (
            "{:,}".format(t["fines"]), money(t["dollars"]), "{:,}".format(t["denials"]), t["penalised"],
            t["homes"], "{:,}".format(t["dropped"]),
            " %d of the homes changed owner in the last twelve months." % t["changed"] if t["changed"] else ""),
        "<p>These are counts, not rates. They are not adjusted for how many homes the chain has, how large "
        "they are, or which states inspect them.</p>",
        '<div class="table-wrap"><table><thead><tr><th>Home</th><th>State</th><th class="num">Fines</th>'
        '<th class="num">Total</th><th class="num">Payment denials</th><th>Earliest</th></tr></thead><tbody>',
    ]
    for h in chain["homes"]:
        label = e(facility_pages.display(h["name"]))
        if h["ccn"] in pages:
            label = '<a href="../facilities/%s">%s</a>' % (e(pages[h["ccn"]][:-5]), label)
        if h["changed_owner"]:
            label += '<br><span class="meta">changed owner in the last 12 months</span>'
        parts.append('<tr><td>%s</td><td>%s</td><td class="num">%d</td><td class="num">%s</td>'
                     '<td class="num">%d</td><td>%s</td></tr>' % (
                         label, e(h["state"]), h["fines"], money(h["dollars"]) if h["fines"] else "",
                         h["denials"], e(h["first"][:4])))
    parts += ["</tbody></table></div>",
              '<p class="meta">Chain names and membership: CMS Provider Information, processed %s. Penalties: '
              "CMS's archive of monthly editions. Both public record. A home with no link has no penalty CMS "
              "has stopped publishing, so it has no page here.</p>" % e(processed),
              "</main></body></html>"]
    return "\n".join(parts) + "\n"


def index_page(found, processed):
    e = html.escape
    rows = sorted(found.values(), key=lambda c: facility_pages.display(c["name"]).lower())
    homes = sum(len(c["homes"]) for c in rows)
    parts = _head("Nursing-home chains and their homes' CMS penalties",
                  "%d chains and the %s nursing homes CMS lists under them, alphabetically." % (
                      len(rows), "{:,}".format(homes)), "%s/chains/" % SITE)
    parts += ['<p class="meta"><a href="../">Nursing Home Penalty Ledger</a></p>', "<h1>Chains</h1>",
              "<p>%d chains, and the %s homes CMS lists under them in its provider file of %s. Listed "
              "alphabetically and not ranked: a total is not a rate, and a chain with more homes has more of "
              "everything.</p>" % (len(rows), "{:,}".format(homes), e(processed)),
              "<p>%s</p>" % TODAY.replace("this chain", "each chain"),
              '<div class="table-wrap"><table><thead><tr><th>Chain</th><th class="num">Homes</th>'
              '<th class="num">Homes penalised</th></tr></thead><tbody>']
    for c in rows:
        t = totals(c)
        parts.append('<tr><td><a href="%s">%s</a></td><td class="num">%d</td><td class="num">%d</td></tr>' % (
            e(page_name(c["id"], c["name"])[:-5]), e(facility_pages.display(c["name"])), t["homes"],
            t["penalised"]))
    parts += ["</tbody></table></div>", "</main></body></html>"]
    return "\n".join(parts) + "\n"


def build(out=OUT, homes=None, history=None, facilities=facility_pages.OUT):
    homes = chains.cached() if homes is None else homes
    history = findings.read_history() if history is None else history
    processed = max(h["processed"] for h in homes)
    pages = {}
    if os.path.isdir(facilities):
        pages = {n[:6]: n for n in os.listdir(facilities) if facility_pages.FACILITY_FILE.match(n)}
    found = gather(homes, history)
    os.makedirs(out, exist_ok=True)
    keep = {"index.html"}
    for chain in found.values():
        name = page_name(chain["id"], chain["name"])
        keep.add(name)
        facility_pages._write(os.path.join(out, name), chain_page(chain, processed, pages))
    facility_pages._write(os.path.join(out, "index.html"), index_page(found, processed))
    for name in os.listdir(out):
        if name not in keep and CHAIN_FILE.match(name):
            os.remove(os.path.join(out, name))
    return found


if __name__ == "__main__":
    built = build()
    print("%d chain pages in %s" % (len(built), OUT))
