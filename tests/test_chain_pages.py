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
        chain_pages.build(self.out, HOMES, HISTORY, self.facilities)
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
        chain_pages.build(self.out, HOMES[:3], HISTORY, self.facilities)
        self.assertEqual(sorted(os.listdir(self.out)), ["7-north-group.html", "index.html"])


if __name__ == "__main__":
    unittest.main()
