# Nursing Home Penalty Ledger

Every penalty the Centers for Medicare & Medicaid Services (CMS) has published against a US nursing home, counted against the homes it inspected, and kept after CMS stops publishing it.

CMS publishes nursing-home penalties as a rolling three-year window. A fine older than that disappears from the current file. This project rebuilds every penalty CMS published from 2019-01 onward out of CMS's own archive of past editions, and captures each new edition weekly, so a penalty that ages out stays visible here.

**Correction, 2026-09-19: older history *can* be recovered.** This README used to say it could not. CMS keeps 97 monthly snapshot ZIPs of the whole nursing-home dataset, listed as JSON at `data.cms.gov/provider-data/api/1/archive/aggregate/theme/nursing-homes/relative`. They run from 2019-01-17 to 2026-08-26, and the oldest one contains `Penalties_Download.csv` and `HealthDeficiencies_Download.csv`. So penalties back to about 2016, and the citations this page says are not archived, are both obtainable now. What makes this worth building is not that it alone keeps the history. It's that no consumer tool shows it: ProPublica's Nursing Home Inspect, LTCCC's NursingHome411, The Care Ratings and Care Compare all stop at about three years. **Backfilled 2026-09-19.** `tools/backfill_cms.py` in the workstation read 83 distinct editions and rebuilt 83,164 penalties. 67,468 of them CMS no longer publishes, and each facility's page now lists those under "Penalties CMS no longer publishes", with the edition that last listed them. Penalties whose amount CMS revised while listing them (29,545, often cut by 35%) are shown once, at the current amount.

## Usage

`docs/` is a static site with no server, no account and no requests to third parties. Searches run in the browser.

```bash
python -m http.server 8765 --directory docs
```

Then open `http://127.0.0.1:8765/`. The page supports these links:

| Fragment | Shows |
| --- | --- |
| `#ccn=015019` | One facility: fines, payment denials, dropped penalties, inspection counts |
| `#state=IL` | A state's totals with its denominator, and its largest fine totals |
| `#q=merry wood` | A name search (a CCN works too) |

## Facility pages

```bash
python tools/facility_pages.py --all        # every inspected home with a dropped fine
python tools/facility_pages.py              # the 30 with the most in dropped fines
python tools/facility_pages.py --ccn 105407 # or named homes
```

`--all` is what the live site carries since 2026-09-28: 12,373 pages, one per
home CMS inspects today with at least one fine its current file no longer
shows, a page per state, and `docs/sitemap.xml` and `docs/robots.txt` so search
engines can find them. Since 2026-10-24 `sitemap.xml` is an index of parts
split by kind (`sitemap-pages.xml`, then `sitemap-homes-N.xml` of 4,000 each),
so Search Console counts indexing per kind, and pages link clean URLs, never
the `.html` form Cloudflare redirects. It removes pages for homes that have left the set. A
page names the edition it was built through, not the day, so rebuilding
without a new edition changes nothing.

**Since 2026-09-28 the weekly task keeps them current.** After a new capture it
reruns `backfill_cms.py`, which now reads the weekly captures as editions beside
CMS's archive (CMS archives an edition only once the next is out, and a
capture's file is byte-identical to the archived one, so the pair counts once),
then rebuilds the pages and commits both. It does this only when the local
archive cache in `data/cms-archive/` exists: filling an empty one fetches about
350 MB from CMS, which is run once by hand, never by the task.

**Star ratings over time, since 2026-09-28.** Each page also carries the home's
overall, inspection, staffing and quality-measure stars from every monthly
edition since January 2019, one row per stretch of the same overall rating,
which Care Compare does not show. `tools/ratings_history.py` reads the
ProviderInfo member of the same archive ZIPs (about 250 MB fetched once, 5 MB
cached in `data/cms-ratings/`) and writes `snapshots/cms-ratings/`. Stars move
when CMS recalculates as well as when a home changes: in most editions about
5% of rated homes change overall rating, in CMS's quarterly refreshes 24-28%,
and in April 2019 53%. Each page says so, marks only editions beyond 40%, and
never says why a rating changed. Checked against a hand count: of the homes
rated in both January 2019 and August 2026, 10,048 have a different overall
rating, the same count found by reading the two raw files.

*"Not shown since" was wrong on 18,000 rows until 2026-09-28.* It named the next
archive, and 13 archives are not editions: year-end ZIPs with no penalties file
(14,882 rows) and re-archived copies of the edition before (3,050 rows, which
still listed the penalty the page said was gone). It now names only distinct
editions with a penalties file.

One static page per home under `docs/facilities/`, listing every penalty in
CMS's archive since 2019, including those the current file no longer shows.
Each row gives the amount as first and as last published (CMS revises
amounts while a penalty is listed: Siesta Key's $799,880 fine was first
published as $125,970), the name the home used at the time, the first and
last archived editions that listed it, each linked to CMS's own ZIP, and the
edition it was gone from. A penalty that left before the usual three years
is flagged, with the file's silence on why stated rather than filled in.

Built 2026-09-27 as a demand test: whether people, and the lawyers who sue
nursing homes, find and use a complete history. A free site already shows
some old penalties; compared on Siesta Key it missed the two largest fines
and showed the $799,880 one at its first amount. See `IDEAS.md` Round 10 in
the workstation for the incumbent check.

## Where the data comes from

`docs/data/` is generated, never edited by hand. The archive and the code that reads it are in this repository, in `snapshots/` and `tools/` — see [`tools/README.md`](tools/README.md) for what each module does and the traps in CMS's own files that it handles. *(This sentence said they "live in the private `ai-workstation` repository" until 2026-09-20, which the paragraph directly below it had already contradicted since the 19th. A correction added beneath a claim does not correct the claim.)*

| Step | Command (from this repository's root) |
| --- | --- |
| Capture a CMS edition | `python tools/snapshot_cms.py` |
| Rebuild history since 2019-01 from CMS's own archive | `python tools/backfill_cms.py` |
| Rebuild this page's data | `python tools/cms_export.py --out docs/data` |
| Every figure a written piece quotes | `python tools/findings.py` |
| Both, unattended | Windows task *CMS nursing-home capture*, weekly, runs `tools/cms_scheduled.py` |

**The unattended row was broken until 2026-10-17**: the task ran the Microsoft
Store `python` placeholder, which exits 9009 (the 2026-10-16 run failed that way).
Since 2026-10-17 it runs
`C:\Users\Jhane\AppData\Local\Programs\Python\Launcher\py.exe` with the same
argument and working directory, and a run that day returned 0 (CMS had published
no edition since 2026-10-09). Read the task's last result and
`snapshots/cms/.last_run.log` before trusting a quiet week.

**These commands moved into this repository on 2026-09-19, and until then they
were not here.** `cms_ledger.py`, `backfill_cms.py`, `cms_export.py`,
`snapshot_cms.py` and `cms_scheduled.py` lived in a private workstation
repository, with the 69 engine tests covering them, while this repository held only
the page and its exported data. So this table named commands a reader could
not run, and the project's central claim — that the history survives here
after CMS drops it — rested on code nobody reading this could see. The archive
itself (`snapshots/`) came with them.

Python 3, **standard library only** for the engine. Only the 8 page tests need
anything installed.

The exporter computes everything through `tools/cms_ledger.py`, the command-line reader, so the page can't disagree with it. The page doesn't word its own refusals either; it prints the reader's sentences from `meta.json`.

## What it refuses to say

| Claim it won't make | Why |
| --- | --- |
| A facility with no penalty is clean | No penalty in the window means CMS published none, and that is not a finding of good care. The page says this in full every time instead of printing a zero |
| One penalty total per facility | Fines are dollars and payment denials are days. They're shown separately and never added together |
| "Nothing was dropped" before 2016 | The earliest archived edition (2019-01) reaches back to January 2016. A facility with no dropped penalty has none in that range; older history is outside every edition, not absent |
| Which rule a facility broke | The citation files are 158 MB and 66 MB a month and are not archived. The page shows deficiency counts only |
| An unknown CCN has a clean record | A number missing from CMS's files is a different fact from a facility with no penalties |

## Tests

```bash
python -m unittest discover -s tests     # 161 tests
```

**169 tests: 74 over the engine, 4 over the article's figures, 9 driving the page, 16 over the unattended run, 23 over the facility pages, 14 over the star-rating history, 6 over the chain count, 7 over the download page, 16 over the chain pages and owner dates.** *(This line said 143 until 2026-10-17 (then 168 for an hour), when its own parts added to 161. This line said 88 until 2026-09-28; the facility pages' tests and three for the unattended run had landed without it. It said 130 until 2026-10-13: the 404 page's test had landed without it, and three were added that day for CMS renaming its archive number.)*
All 84 are in this repository as of 2026-09-19; 76 of them used to be in the
workstation, which meant a clone could run 8.

`discover`, not a loop over `tests/test_*.py` — a file that calls
`unittest.main()` above its last class runs green while skipping it and prints
a total that looks right, which hid three tests in a sibling project here.

The 8 page tests drive the rendered page in headless Chromium and check it
against `docs/data/meta.json`, so they stay valid as the captures move the
numbers. They need Playwright (`pip install playwright`, then
`python -m playwright install chromium`) and **skip without it** — which is a
real hazard rather than a convenience, because a green `OK (skipped=8)` looks
exactly like a suite that tested the page. CI installs chromium on purpose and
fails the run if anything reports as skipped. The 71 engine tests need nothing.


## The whole file, to download and cite (built 2026-10-13, live at `/data`)

`python tools/data_page.py` writes `docs/data.html` and `docs/download/`: both
history files whole, a definition of every column, each file's SHA-256, a line
to cite and what the data is not. The page's counts are read from the files,
a column with no definition stops the build, and a test fails if the committed
page or downloads differ from what the histories give now. The weekly task
rebuilds it with the home pages. The front page and the sitemap link it.

*(Status corrected 2026-10-18: this was built on the branch `data-download`
because a push to `main` is a deploy. The branch has since been merged; it
holds nothing `main` lacks, and `docs/data.html` is on `origin/main`, so the
page is live at `penalty-ledger.pages.dev/data`.)*

**Found while writing the column definitions:** CMS's edition of 2019-10-09
stores 101 home numbers as numbers (`14E169` as `1.40E+170`, a spreadsheet's
doing). The ratings history therefore held 101 homes that never existed, each
for one edition, and a one-edition hole in 101 real homes' histories.
`ratings_history.repair` puts a number back where exactly one home it could
be is known from the other editions and missing from that one: 101 of 101,
none left, counted in the manifest. 44 home pages change by one row each.
The same branch carries it.

## Who runs a home: measured 2026-10-13, chain pages live 2026-10-17

A home's page says what that home was fined. It does not say who runs it or
how their other homes have done. `python tools/chains.py` reads CMS's Provider
Information file (processed 2026-09-01), which names a chain for each home
that has one, against the penalty history:

- 10,184 of 14,690 homes (69%) are in one of 611 chains, and every chain id
  carries one name.
- Homes in a chain average $119,194 in fines since 2016 and homes outside one
  $88,330. Not adjusted for size or state, so it is a count, not a finding.
- 86 homes changed owner in the last twelve months.

**The limit that decides how a page would have to read:** the chain is
today's. A 2019 fine is counted under whoever has the home now, and the
provider file does not say when they got it. A chain page would have to say
that on the page, and the per-chain totals in the tool's output are
unpublished for the same reason.

**Chain pages, built 2026-10-13 on the branch `chain-pages`; merged and live 2026-10-17** (merge `e7ab590f`, at `penalty-ledger.pages.dev/chains/`).
`python tools/chain_pages.py` writes `docs/chains/`: 611 pages and an index.
Each opens with the limit above, before any figure; lists its homes with
each one's fines, total, payment denials and earliest penalty; links a home
that has a page; marks a home that changed owner in the last year; and says
its figures are counts, not rates. The index is alphabetical and carries no
dollar totals, so it cannot be read as a ranking. A test fails on any page
that says a chain "was fined".

What was held back at first, until the 2026-10-17 merge did all three (the
front page links the index, the sitemap lists every page, the weekly task
rebuilds them with fresh provider and owner files, and the review below was
done): the pages were linked from nowhere and were not in the sitemap; the weekly task does not fetch the provider file or rebuild
them, so they would go stale monthly; and they have had no `publish-legal`
review, which they need, since each one is a page about a named business.

**The limit can probably be removed, and that was missed (found 2026-10-13).**
"CMS does not say when a home joined a chain" is true of the Provider
Information file and not of CMS. CMS publishes *Skilled Nursing Facility
Change of Ownership* (data.cms.gov, quarterly): buyer, seller, kind of change
and **effective date**, for changes since 2016-01-01, with a companion file
of owners and the date each became associated with a home. With it a fine
could be set against whoever had the home on the day, which is the page a
reader actually wants and the one that would be fair to a chain. Not read
yet: whether its keys join to the certification number used here was not
confirmed. These pages should not go out before that is tried.

**Tried 2026-10-17: it joins, and the pages now carry it.** `python
tools/ownership.py` fetches the newest edition (found by title in
`data.cms.gov/data.json`, since each edition has its own dataset id) and keeps
each home's latest effective date. The 2026-06-01 edition has 5,227 changes
effective 2016-01-01 to 2026-02-01; `CCN - BUYER` is the certification number
used here, and 5,171 of 5,225 homes join the provider file. All 86 homes the
provider file marks "changed owner in the last 12 months" are in it. **27% of
the fine dollars at chained homes ($325M of $1.21B) are dated before the
home's latest change of owner**, and at 97 of the 611 chains more than half
are. Journey Healthcare is the plainest case: $6.66M of its 33 homes' $7.06M
predates its 2024 purchases. Each chain page now gives every home's
current-owner date and counts earlier penalties apart, and says the split can
be off both ways: a change inside one chain counts as a change, and a change
the file does not hold (several Journey homes have none) is not counted. The
file is Windows-1252, not UTF-8. `publish-legal` run the same day (Publish reviews below). Still not
done: a link from anywhere, the sitemap, and the quarterly refresh.

## Status

**The page is live at `penalty-ledger.pages.dev`**, built by Cloudflare Pages
from this repository's `docs/` on every push (since 2026-09-27; it was first
a direct upload to `cms-penalty-ledger.pages.dev` on 2026-09-19). This repository is self-contained: everything
needed to capture an edition, rebuild the history from `data.cms.gov` and
regenerate the page is here, and its own suite runs against it. The figures a
written piece quotes are printed by `tools/findings.py`.

**Checked against existing tools on 2026-09-19, and re-checked on the same
day.** Every consumer tool found — ProPublica's Nursing Home Inspect,
LTCCC/NursingHome411, The Care Ratings, Care Compare, and an Apify CMS penalty
scraper — shows about three years. LTCCC's own alert page says "the past three
years" in as many words. Multi-year penalty history is a real gap, and the
correction at the top is what makes it fillable.

**The name was searched.** No product was found using "Nursing Home Penalty
Ledger", and a trademark search returns only unrelated marks (Legal Ledger, the
Ledger hardware wallet). Renamed from Docket on 2026-09-19: no nursing-home
tool used that name either, but legal software crowds it — Docket Alarm,
Clarivate Docket, Docket for in-house counsel — so a search for it would never
have found this page.

Not tagged for production. Making this repository public would run through
`PRE-PUBLIC-CHECKLIST.md` in the workstation repository first.

## Publish reviews

**2026-10-03, `publish-legal` and `publish-security`.**

| Check | Finding | Severity | Done |
|---|---|---|---|
| Statements about named homes | Every penalty links the CMS edition that published it; amounts are as CMS published them; early removals are marked with appeals and settlements named as possible; each page says it makes no finding about care | - | Checked, no change |
| Corrections | No way to report an error on a site that names businesses | fix | Added to all 12,373 facility pages and the main page: open an issue, corrected against the cited edition (`418f797`) |
| Rendering | Archive text reaches the page through `esc()` | - | Checked |
| Headers | No content security policy | low | Fixed (`6fb9118`): `_headers` allows the one inline script by hash, pinned by a test; preview checked in a browser (archive loads, search answers, console clean), then live |
| Leak audit | 313 hits for "Huntsville", all facility addresses in the national data, public since 2026-09-27 | note | Accepted: data, not a personal leak |

This review is not legal advice.

**2026-10-17, `publish-legal`, the chain pages (on the branch `chain-pages` before the merge that put them live the same day).**

| Check | Finding | Severity | Done |
|---|---|---|---|
| Data | Provider Information, the archive and Change of Ownership are all CMS public-domain works (the last marked usa.gov government works); no owner names or addresses from the CHOW owner file are read | - | Checked |
| Statements about named chains | Pages put today's chain against fines from before it owned the home: 27% of chained fine dollars, 94% at Journey Healthcare | stop | Fixed: current-owner date per home and earlier penalties counted apart (`de4c7bfe`) |
| Same | The split can be off both ways (a change within one chain; a change the file lacks, as at several Journey homes), and "no change since 2016" overclaimed | fix | Said on every page; label is now "none in CMS's file" |
| Same | No source links, no corrections route, no "no finding about care" line, all of which the facility pages carry | fix | Added to all 612 pages, links checked live (200), pinned by a test |
| Same | The full total still appears before the since-owner figure, one paragraph below the caveat | note | Accepted: the caveat and the split sit above the table |
| Advice | Read by families choosing a home: "counts, not rates" and no ranking already said | - | Checked |
| Staleness | The weekly task does not rebuild these, so chain membership ages monthly and owner dates quarterly | fix before deploy | Not done: each page states its editions, but the pages must be rebuilt by the task before they go live |
| Collecting, selling | Static pages; nothing collected or sold | - | Checked |
| Author | Pen name; no real name in any page; the issues link is the repository's existing account, as on the live facility pages | note | Accepted as before |

Not checked: whether every CMS chain name is the name the company uses, and the chain pages' security review (static, same template as the facility pages). This review is not legal advice.
