"""The download page: built from the two history files, and unable to
disagree with them."""

import csv
import gzip
import hashlib
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

import data_page  # noqa: E402


class TheCommittedPage(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.facts = data_page.build(cls.tmp)
        with open(os.path.join(cls.tmp, "data.html"), encoding="utf-8") as handle:
            cls.html = handle.read()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_the_committed_page_and_downloads_are_what_the_files_give_now(self):
        """A history rebuilt without the page, or the reverse, fails here."""
        with open(os.path.join(HERE, "docs", "data.html"), encoding="utf-8") as handle:
            self.assertEqual(handle.read(), self.html, "run `python tools/data_page.py`")
        for spec in data_page.FILES:
            with open(spec["source"], "rb") as a, open(os.path.join(HERE, "docs", "download", spec["name"]), "rb") as b:
                self.assertEqual(hashlib.sha256(a.read()).hexdigest(), hashlib.sha256(b.read()).hexdigest(),
                                 spec["name"])

    def test_every_column_is_defined_and_every_definition_has_a_column(self):
        for spec in data_page.FILES:
            with gzip.open(spec["source"], "rt", encoding="utf-8", newline="") as handle:
                head = next(csv.reader(handle))
            self.assertEqual(head, list(spec["columns"]), spec["name"])
            for column in head:
                self.assertIn("<code>%s</code>" % column, self.html)

    def test_a_column_nobody_defined_stops_the_build(self):
        spec = dict(data_page.FILES[1], columns={"ccn": "x"})
        with self.assertRaises(ValueError):
            data_page.describe(spec)

    def test_the_counts_on_the_page_are_the_files_counts(self):
        p = self.facts["penalties"]
        with gzip.open(data_page.FILES[0]["source"], "rt", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(p["rows"], len(rows))
        self.assertEqual(p["dropped"], sum(r["in_latest"] == "no" for r in rows))
        for figure in (p["rows"], p["dropped"], p["homes"], self.facts["ratings"]["rows"]):
            self.assertIn("{:,}".format(figure), self.html)
        self.assertIn(p["sha256"], self.html)

    def test_the_page_says_how_to_cite_it_and_what_it_is_not(self):
        self.assertIn("How to cite it", self.html)
        self.assertIn(self.facts["penalties"]["through"], self.html)
        self.assertIn("was not withdrawn or overturned", self.html)
        self.assertIn("never added together", self.html)

    def test_no_home_number_in_the_ratings_download_is_a_mangled_one(self):
        with gzip.open(data_page.FILES[1]["source"], "rt", encoding="utf-8", newline="") as handle:
            odd = [r["ccn"] for r in csv.DictReader(handle) if not re.match(r"^[0-9A-Z]{6}$", r["ccn"])]
        self.assertEqual(odd, [])

    def test_the_page_runs_no_script_and_loads_nothing_from_elsewhere(self):
        self.assertNotIn("<script", self.html)
        self.assertEqual(re.findall(r'(?:src|href)="(https?://[^"]+)"', self.html.replace(
            'rel="canonical" href="%s/data"' % data_page.SITE, "")),
            ["%s/issues" % data_page.REPOSITORY])


if __name__ == "__main__":
    unittest.main()
