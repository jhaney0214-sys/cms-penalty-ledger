"""Star-rating history, offline: three header eras, re-archived editions,
runs of unchanged ratings, and the share of homes that moved in an edition."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import ratings_history as rh  # noqa: E402

H2019 = "PROVNUM,PROVNAME,OVERALL_RATING,OVERALL_RATING_FN,SURVEY_RATING,QUALITY_RATING,STAFFING_RATING,FILEDATE\n"
H2020 = ("Federal Provider Number,Provider Name,Overall Rating,Overall Rating Footnote,"
         "Health Inspection Rating,QM Rating,Long-Stay QM Rating,Staffing Rating,Processing Date\n")
HNOW = ('"CMS Certification Number (CCN)","Provider Name","Chain Average Overall 5-star Rating",'
        '"Overall Rating","Health Inspection Rating","QM Rating","Staffing Rating","Processing Date"\n')


def entry(date):
    return {"date": date, "url": "/x/%s.zip" % date, "id": date}


class Reading(unittest.TestCase):

    def test_all_three_eras_read_to_one_shape(self):
        a = rh.reduce((H2019 + "15009,A,5,,5,4,3,2019-01-01\n").encode())
        b = rh.reduce((H2020 + "015009,A,5,,5,4,4,3,2020-09-01\n").encode())
        c = rh.reduce((HNOW + '"015009","A","3.2","2","2","4","4",2026-08-01\n').encode())
        self.assertEqual(a, ("2019-01-01", [("015009", "5", "5", "4", "3")]))
        self.assertEqual(b, ("2020-09-01", [("015009", "5", "5", "4", "3")]))
        self.assertEqual(c, ("2026-08-01", [("015009", "2", "2", "4", "4")]))

    def test_the_chain_average_is_not_the_home_rating(self):
        processed, rows = rh.reduce((HNOW + '"1","A","4.5","","3","","",2026-08-01\n').encode())
        self.assertEqual(rows, [("000001", "", "3", "", "")])

    def test_mixed_case_2019_names_are_read(self):
        head = ("PROVNUM,Overall_Rating,SURVEY_RATING,Quality_Rating,LS_Quality_Rating,"
                "Staffing_Rating,RN_staffing_rating,FILEDATE\n")
        self.assertEqual(rh.reduce((head + "15009,5,4,3,3,2,1,2019-04-01\n").encode())[1],
                         [("015009", "5", "4", "3", "2")])

    def test_the_header_is_checked_before_the_member_is_fetched(self):
        import zipfile
        from test_backfill_cms import fake_fetch, zip_bytes
        body = (H2020 + "015009,A,5,,5,4,4,3,2020-09-01\n" * 4000).encode()
        blob = zip_bytes({"x/NH_ProviderInfo_Sep2020.csv": body}, zipfile.ZIP_DEFLATED)
        calls = []
        fetch = fake_fetch({"u": blob}, calls)
        import backfill_cms as bf
        m = rh.provider_member(bf.zip_directory("u", fetch))
        calls.clear()
        self.assertIn("Overall Rating", rh.peek_header("u", m, fetch, size=512))
        self.assertLessEqual(sum(calls), 30 + 512)

    def test_an_unknown_header_is_refused(self):
        with self.assertRaises(ValueError):
            rh.reduce(b"ccn,stars\n1,5\n")

    def test_a_star_outside_one_to_five_is_refused(self):
        with self.assertRaises(ValueError):
            rh.reduce((H2020 + "015009,A,7,,5,4,4,3,2020-09-01\n").encode())

    def test_macos_forks_are_not_the_member(self):
        members = [{"name": "__MACOSX/x/._NH_ProviderInfo_Mar2022.csv"},
                   {"name": "x/NH_ProviderInfo_Mar2022.csv"}, {"name": "x/NH_Penalties_Mar2022.csv"}]
        self.assertEqual(rh.provider_member(members)["name"], "x/NH_ProviderInfo_Mar2022.csv")


class History(unittest.TestCase):

    def fetched(self, *editions):
        return [(entry(d), "cache", ("p", sha, "m", rows)) for d, sha, rows in editions]

    def test_a_re_archived_edition_is_counted_once(self):
        rows = [("1", "3", "3", "3", "3")]
        manifest, editions = rh.build(self.fetched(("2020-11-21", "s", rows), ("2020-12-21", "s", rows)))
        self.assertEqual(len(editions), 1)
        self.assertEqual(manifest[1]["duplicate_of"], "2020-11-21")

    def test_unchanged_ratings_are_one_run_and_a_change_starts_another(self):
        _, eds = rh.build(self.fetched(
            ("2020-01", "a", [("1", "4", "4", "4", "4")]),
            ("2020-02", "b", [("1", "4", "4", "4", "4")]),
            ("2020-03", "c", [("1", "2", "1", "4", "4")])))
        done = rh.runs(eds)
        self.assertEqual([(r["from"], r["to"], r["n"], r["stars"][0], r["in_latest"]) for r in done],
                         [("2020-01", "2020-02", 2, "4", False), ("2020-03", "2020-03", 1, "2", True)])

    def test_leaving_the_file_ends_a_run(self):
        _, eds = rh.build(self.fetched(
            ("2020-01", "a", [("1", "4", "4", "4", "4")]),
            ("2020-02", "b", [("2", "1", "1", "1", "1")]),
            ("2020-03", "c", [("1", "4", "4", "4", "4"), ("2", "1", "1", "1", "1")])))
        ones = [r for r in rh.runs(eds) if r["ccn"] == "1"]
        self.assertEqual([(r["from"], r["to"]) for r in ones], [("2020-01", "2020-01"), ("2020-03", "2020-03")])

    def test_moved_counts_only_homes_rated_in_both(self):
        _, eds = rh.build(self.fetched(
            ("2020-01", "a", [("1", "4", "", "", ""), ("2", "3", "", "", ""), ("3", "", "", "", "")]),
            ("2020-02", "b", [("1", "2", "", "", ""), ("2", "3", "", "", ""), ("3", "5", "", "", "")])))
        self.assertEqual(rh.moved(eds), {"2020-02": (2, 1)})



class MangledHomeNumbers(unittest.TestCase):
    """CMS's 2019-10-09 edition carries 101 home numbers a spreadsheet read
    as numbers: 14E169 arrived as 1.40E+170, so that home's history had a
    hole and a home that never existed had one edition."""

    def test_the_numbers_a_mangled_one_could_have_been(self):
        self.assertEqual(rh.unmangle("1.40E+170"), ["14E169"])
        self.assertEqual(rh.unmangle("9.00E+20"), ["90E019", "09E020"])
        self.assertEqual(rh.unmangle("015009"), [])
        self.assertEqual(rh.unmangle("14E169"), [])
        self.assertEqual(rh.unmangle("1.45E+170"), [])      # no two-digit state gives this

    def test_one_known_home_missing_from_the_edition_gets_it_back(self):
        stars = ("5", "4", "5", "2")
        editions = [("2019-09-09", {"14E169": stars, "015009": stars}),
                    ("2019-10-09", {"1.40E+170": stars, "015009": stars}),
                    ("2019-12-17", {"14E169": stars, "015009": stars})]
        fixed, counts = rh.repair(editions)
        self.assertEqual(sorted(fixed[1][1]), ["015009", "14E169"])
        self.assertEqual(counts, {"2019-10-09": (1, 0)})
        runs = [r for r in rh.runs(fixed) if r["ccn"] == "14E169"]
        self.assertEqual(len(runs), 1)                       # one unbroken run, not three
        self.assertEqual(runs[0]["n"], 3)

    def test_a_number_that_fits_two_homes_or_none_is_left_and_counted(self):
        stars = ("3", "3", "3", "3")
        two = [("a", {"90E019": stars, "09E020": stars}), ("b", {"9.00E+20": stars})]
        fixed, counts = rh.repair(two)
        self.assertIn("9.00E+20", fixed[1][1])
        self.assertEqual(counts, {"b": (0, 1)})
        none = [("a", {"015009": stars}), ("b", {"1.40E+170": stars})]
        self.assertEqual(rh.repair(none)[1], {"b": (0, 1)})
        # The home is already in the edition under its own number: not overwritten.
        both = [("a", {"14E169": stars}), ("b", {"14E169": stars, "1.40E+170": ("1", "1", "1", "1")})]
        fixed, counts = rh.repair(both)
        self.assertEqual(fixed[1][1]["14E169"], stars)
        self.assertEqual(counts, {"b": (0, 1)})


if __name__ == "__main__":
    unittest.main()
