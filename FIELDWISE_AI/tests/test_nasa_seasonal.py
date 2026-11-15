import unittest

import pandas as pd

from modules.nasa_api import build_rotation_conditions, summarise_seasons


def _daily(location="Dharwad", start="2024-06-01", end="2025-03-31"):
    dates = pd.date_range(start, end)
    return pd.DataFrame({
        "date": dates,
        "location": location,
        "T2M": 25.0,
        "T2M_MAX": 30.0,
        "T2M_MIN": 20.0,
        "PRECTOTCORR": 2.0,
        "RH2M": 60.0,
        "ALLSKY_SFC_SW_DWN": 18.0,
    })


class TestSeasons(unittest.TestCase):
    def test_kharif_and_rabi_split_and_totals(self):
        s = summarise_seasons(_daily())
        kharif = s[(s.season == "kharif") & (s.season_year == 2024)].iloc[0]
        rabi = s[(s.season == "rabi") & (s.season_year == 2024)].iloc[0]

        self.assertEqual(kharif.days_expected, 153)  # Jun-Oct
        self.assertEqual(kharif.days_available, 153)
        self.assertTrue(kharif.complete)
        self.assertEqual(kharif.rainfall_mm, 153 * 2.0)  # sum, not mean
        self.assertEqual(kharif.temperature_c, 25.0)

        # Nov 2024 - Mar 2025 = 151 days; Jan-Mar belong to rabi 2024
        self.assertEqual(rabi.days_expected, 151)
        self.assertTrue(rabi.complete)
        self.assertEqual(rabi.start_date, "2024-11-01")
        self.assertEqual(rabi.end_date, "2025-03-31")

    def test_incomplete_season_is_flagged(self):
        s = summarise_seasons(_daily(end="2024-08-15"))
        kharif = s[s.season == "kharif"].iloc[0]
        self.assertFalse(kharif.complete)
        self.assertLess(kharif.days_available, kharif.days_expected)

    def test_conditions_for_rotation_engine(self):
        s = summarise_seasons(_daily())
        cond = build_rotation_conditions(s, "Dharwad", ["kharif", "rabi"])

        self.assertEqual([c["season"] for c in cond], ["kharif", "rabi"])
        env = cond[0]["environmental_data"]
        self.assertEqual(env["temperature_c"], 25.0)
        self.assertEqual(env["rainfall_mm"], 306.0)
        self.assertIn("NASA POWER", env["data_source"])

    def test_missing_location_or_season_raises(self):
        s = summarise_seasons(_daily())
        with self.assertRaises(ValueError):
            build_rotation_conditions(s, "Nowhere", ["kharif"])
        with self.assertRaises(ValueError):
            # summer season is absent from this dataset
            build_rotation_conditions(s, "Dharwad", ["kharif", "summer"])

    def test_incomplete_seasons_not_used_by_default(self):
        s = summarise_seasons(_daily(end="2024-08-15"))
        with self.assertRaises(ValueError):
            build_rotation_conditions(s, "Dharwad", ["kharif"])


if __name__ == "__main__":
    unittest.main()
