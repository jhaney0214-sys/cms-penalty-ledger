"""Chain pages, on rows small enough to add up by hand. No network, and no
use of the provider file's local cache."""

import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

import chain_pages  # noqa: E402
import ownership  # noqa: E402


def home(ccn, name, state, chain_id, chain, changed="N"):
    return {"ccn": ccn, "name": name, "state": state, "ownership_type": "For profit", "chain_name": chain,
            "chain_id": chain_id, "changed_owner": changed, "processed": "2026-09-01"}


def penalty(ccn, kind, amount, date, latest="no"):
    return {"ccn": ccn, "kind": kind, "amount": amount, "date": date, "in_latest": latest}


HOMES = [home("015009", "ALPHA HOME", "AL", "7", "NORTH GROUP"),
         home("15010", "BETA HOME", "TX", "7", "NORTH GROUP", changed="Y"),
         home("015011", "GAMMA HOME", "AL", "", ""),
         home("015012", "DELTA HOME", "AL", "9", "SOUTH <CARE> & CO")]
HISTORY = [penalty("015009", "Fine", "1000", "2019-03-01"), penalty("015009", "Payment Denial", "", "2021-05-01"),
           penalty("015010", "Fine", "500", "2024-02-01", latest="yes"), penalty("015011", "Fine", "300", "2020-01-01")]


class Gathering(unittest.TestCase):

    def setUp(self):
        self.found = chain_pages.gather(HOMES, HISTORY)

    def test_a_home_with_no_chain_is_on_no_chain_page(self):
        self.assertEqual(sorted(self.found), ["7", "9"])
        self.assertNotIn("015011", [h["ccn"] for c in self.found.values() for h in c["homes"]])

    def test_the_totals_add_up_and_fines_and_denials_stay_apart(self):
        t = chain_pages.totals(self.found["7"])
        self.assertEqual((t["homes"], t["penalised"], t["fines"], t["dollars"], t["denials"]), (2, 2, 2, 1500.0, 1))
        self.assertEqual((t["dropped"], t["changed"], t["states"]), (2, 1, 2))
        self.assertEqual(chain_pages.totals(self.found["9"])["penalised"], 0)


class ThePage(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.facilities = os.path.join(self.tmp, "facilities")
        os.makedirs(self.facilities)
        open(os.path.join(self.facilities, "015009-alpha-home.html"), "w").close()
        self.out = os.path.join(self.tmp, "chains")
        chain_pages.build(self.out, HOMES, HISTORY, self.facilities, since={})
        self.page = open(os.path.join(self.out, "7-north-group.html"), encoding="utf-8").read()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_the_caveat_comes_before_any_figure(self):
        """The chain is today's. A page that gave the total first would be
        read as the chain's record."""
        self.assertIn("These are the homes CMS lists under this chain today", self.page)
        self.assertLess(self.page.index("lists under this chain today"), self.page.index("$1,500"))
        self.assertIn("not a penalty against this chain's management", self.page)
        self.assertIn("counts, not rates", self.page)

    def test_every_page_carries_its_sources_and_a_way_to_report_an_error(self):
        for name in os.listdir(self.out):
            text = open(os.path.join(self.out, name), encoding="utf-8").read()
            self.assertIn("cms-penalty-ledger/issues", text, name)
            self.assertIn("makes no finding about the care", text, name)
            self.assertIn("skilled-nursing-facility-change-of-ownership", text, name)

    def test_no_page_says_a_chain_was_fined(self):
        for name in os.listdir(self.out):
            text = open(os.path.join(self.out, name), encoding="utf-8").read().lower()
            for phrase in ("was fined", "were fined", "worst", "ranked by", "most fined"):
                self.assertNotIn(phrase, text, name)

    def test_only_a_home_with_a_page_is_linked_and_a_change_of_owner_is_marked(self):
        self.assertIn('<a href="../facilities/015009-alpha-home">Alpha Home</a>', self.page)
        self.assertNotIn("015010", self.page)
        self.assertIn("Beta Home", self.page)
        self.assertIn("changed owner in the last 12 months", self.page)

    def test_the_index_is_alphabetical_and_shows_no_dollar_total(self):
        index = open(os.path.join(self.out, "index.html"), encoding="utf-8").read()
        self.assertLess(index.index("North Group"), index.index("South"))
        self.assertNotIn("$", index)
        self.assertIn("not ranked", index)

    def test_a_chain_name_is_escaped(self):
        page = open(os.path.join(self.out, chain_pages.page_name("9", "SOUTH <CARE> & CO")), encoding="utf-8").read()
        self.assertNotIn("<CARE>", page)
        self.assertNotIn("<care>", page.lower().replace("&lt;care&gt;", ""))

    def test_a_chain_that_has_gone_loses_its_page(self):
        chain_pages.build(self.out, HOMES[:3], HISTORY, self.facilities, since={})
        self.assertEqual(sorted(os.listdir(self.out)), ["7-north-group.html", "index.html"])


class OwnerDates(unittest.TestCase):
    """Alpha Home's current owner took over in 2020: its 2019 fine and 2021
    denial straddle the date. Beta Home has no change in the file."""

    SINCE = {"015009": "2020-06-01"}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.out = os.path.join(self.tmp, "chains")
        chain_pages.build(self.out, HOMES, HISTORY, os.path.join(self.tmp, "none"), since=self.SINCE,
                          edition="2026-06-01")
        self.page = open(os.path.join(self.out, "7-north-group.html"), encoding="utf-8").read()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_a_penalty_before_the_owner_took_over_is_counted_apart(self):
        t = chain_pages.totals(chain_pages.gather(HOMES, HISTORY, self.SINCE)["7"])
        self.assertEqual((t["earlier"], t["earlier_dollars"], t["dated"]), (1, 1000.0, 1))
        self.assertEqual(t["dollars"], 1500.0)

    def test_the_page_says_so_before_any_figure_and_names_the_edition(self):
        self.assertLess(self.page.index("counted apart"), self.page.index("$1,500"))
        self.assertIn("edition 2026-06-01", self.page)
        self.assertIn("which leaves $500 in fines since", self.page)
        self.assertIn("<td>2020-06-01</td>", self.page)
        self.assertIn("1 ($1,000)", self.page)
        self.assertIn("none in CMS's file", self.page)
        self.assertIn("effective by 2020-06-01", self.page)

    def test_still_no_page_says_a_chain_was_fined(self):
        for name in os.listdir(self.out):
            text = open(os.path.join(self.out, name), encoding="utf-8").read().lower()
            self.assertNotIn("was fined", text, name)
            self.assertIn("not a penalty against", text, name)


class WeeklyRefresh(unittest.TestCase):
    """What the weekly task runs. A failure here must never reach the
    facility pages, which are rebuilt in the same step."""

    def test_a_fetch_that_fails_falls_back_to_the_cache_and_still_builds(self):
        said = []

        def down():
            raise OSError("CMS did not answer")
        built = chain_pages.refresh(fetch_chains=down, fetch_owners=down,
                                    build_pages=lambda: {"7": {}, "9": {}}, log=said.append)
        self.assertEqual(built, 2)
        self.assertEqual(len(said), 2)
        self.assertIn("using the cache", said[0])

    def test_a_build_that_fails_is_logged_not_raised(self):
        said = []

        def broken():
            raise FileNotFoundError("no provider file cached")
        self.assertEqual(chain_pages.refresh(fetch_chains=lambda: None, fetch_owners=lambda: None,
                                             build_pages=broken, log=said.append), 0)
        self.assertIn("NOT rebuilt", said[0])

    def test_the_task_commits_the_chain_pages_and_the_sitemap_lists_them(self):
        import cms_scheduled
        import facility_pages
        self.assertIn("docs/chains", cms_scheduled.HISTORY_PATHS)
        xml = facility_pages.sitemap([""], "2026-10-01", ["index.html", "7-north-group.html"])
        self.assertIn("/chains/</loc>", xml)
        self.assertIn("/chains/7-north-group</loc>", xml)
        self.assertNotIn(".html</loc>", xml)


class OwnershipFile(unittest.TestCase):

    RAW = ('"ENROLLMENT ID - BUYER","CCN - BUYER","EFFECTIVE DATE","ORGANIZATION NAME - SELLER"\n'
           'O1,15009,12/29/2020,A\nO2,015009,3/1/2023,B\nO3,055656,10/11/2023,C\xa0D\nO4,,1/1/2024,E\n')

    def test_the_latest_change_per_home_is_kept_and_numbers_are_padded(self):
        self.assertEqual(ownership.latest(self.RAW), {"015009": "2023-03-01", "055656": "2023-10-11"})

    def test_a_missing_column_is_an_error(self):
        with self.assertRaises(ValueError):
            ownership.latest('"CCN","EFFECTIVE DATE"\n015009,1/1/2020\n')

    def test_the_newest_edition_is_found_by_title_and_the_owner_file_is_not(self):
        def ds(title, url):
            return {"title": title, "distribution": [{"format": "API", "accessURL": "x"},
                                                     {"downloadURL": url}]}
        cat = {"dataset": [ds("Skilled Nursing Facility Change of Ownership : 2026-03-01", "a.csv"),
                           ds("Skilled Nursing Facility Change of Ownership : 2026-06-01", "b.csv"),
                           ds("Skilled Nursing Facility Change of Ownership - Owner Information : 2026-09-01",
                              "c.csv")]}
        self.assertEqual(ownership.newest(cat), ("2026-06-01", "b.csv"))

    def test_no_cache_means_no_dates(self):
        self.assertEqual(ownership.cached(os.path.join(tempfile.gettempdir(), "no-such-file.csv.gz")), ({}, None))


if __name__ == "__main__":
    unittest.main()
