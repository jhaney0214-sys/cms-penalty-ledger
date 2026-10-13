"""chains.py's counting, on rows small enough to add up by hand. No network."""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "tools"))

import chains  # noqa: E402

HEAD = ("CMS Certification Number (CCN),Provider Name,State,Ownership Type,Chain Name,Chain ID,"
        "Provider Changed Ownership in Last 12 Months,Processing Date,Overall Rating")
FILE = "\n".join([
    HEAD,
    "015009,ALPHA HOME,AL,For profit,NORTH GROUP,7,N,2026-09-01,3",
    "15010,BETA HOME,AL,For profit,NORTH GROUP,7,Y,2026-09-01,2",
    "015011,GAMMA HOME,AL,Non profit,,,N,2026-09-01,5",
]) + "\n"


def penalty(ccn, amount):
    return {"ccn": ccn, "amount": amount}


class Reading(unittest.TestCase):

    def test_only_the_named_columns_are_kept(self):
        rows = chains.slim(FILE)
        self.assertEqual(len(rows), 3)
        self.assertEqual(sorted(rows[0]), sorted(chains.KEEP))
        self.assertEqual(rows[2]["chain_id"], "")

    def test_a_file_without_the_chain_column_is_refused(self):
        with self.assertRaises(ValueError):
            chains.slim(FILE.replace("Chain ID", "Group"))


class Counting(unittest.TestCase):

    def setUp(self):
        self.f = chains.figures(chains.slim(FILE), [
            penalty("015009", "1000"), penalty("015009", ""),      # a fine and a payment denial
            penalty("015010", "500"), penalty("015011", "300"),
            penalty("999999", "9000"),                              # a home no longer in the file
        ])

    def test_homes_chains_and_owner_changes(self):
        self.assertEqual((self.f["homes"], self.f["in_chain"], self.f["chains"]), (3, 2, 1))
        self.assertEqual(self.f["changed_owner"], 1)

    def test_a_ccn_without_its_leading_zero_is_the_same_home(self):
        chain = self.f["table"][0]
        self.assertEqual((chain["name"], chain["homes"], chain["fined_homes"]), ("NORTH GROUP", 2, 2))
        self.assertEqual((chain["penalties"], chain["fines"]), (3, 1500.0))

    def test_a_penalty_for_a_home_not_in_the_file_is_counted_apart(self):
        self.assertEqual(self.f["history_unmatched"], 1)
        self.assertAlmostEqual(self.f["share_of_fines_chain"], 1500.0 / 1800.0)
        self.assertEqual((self.f["fines_per_home_chain"], self.f["fines_per_home_alone"]), (750.0, 300.0))

    def test_the_report_names_the_chain_and_the_month(self):
        text = chains.text(self.f)
        self.assertIn("NORTH GROUP", text)
        self.assertIn("2026-09-01", text)


if __name__ == "__main__":
    unittest.main()
