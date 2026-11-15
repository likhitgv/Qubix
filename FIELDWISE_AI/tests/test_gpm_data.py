
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "gpm" / "gpm_rainfall_january_2025.csv"

EXPECTED_LOCATIONS = {
    "Ballari",
    "Shivamogga",
    "Vijayapura",
    "Belagavi",
    "Dharwad",
}

EXPECTED_COLUMNS = [
    "date",
    "location",
    "latitude",
    "longitude",
    "rainfall_mm",
    "source",
]


class TestGPMRainfallData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not CSV_PATH.exists():
            raise FileNotFoundError(f"GPM CSV not found: {CSV_PATH}")

        cls.df = pd.read_csv(CSV_PATH)

    def test_required_columns_exist(self):
        self.assertEqual(list(self.df.columns), EXPECTED_COLUMNS)

    def test_total_record_count(self):
        self.assertEqual(len(self.df), 155)

    def test_all_five_locations_exist(self):
        self.assertEqual(set(self.df["location"]), EXPECTED_LOCATIONS)

    def test_each_location_has_31_records(self):
        counts = self.df.groupby("location").size()

        self.assertEqual(len(counts), 5)
        for count in counts:
            self.assertEqual(count, 31)

    def test_date_coverage(self):
        dates = pd.to_datetime(self.df["date"], errors="raise")

        self.assertEqual(dates.min(), pd.Timestamp("2025-01-01"))
        self.assertEqual(dates.max(), pd.Timestamp("2025-01-31"))
        self.assertEqual(dates.nunique(), 31)

    def test_no_duplicate_location_dates(self):
        duplicates = self.df.duplicated(
            subset=["date", "location"]
        )

        self.assertFalse(duplicates.any())

    def test_no_missing_values(self):
        self.assertFalse(self.df.isnull().any().any())

    def test_rainfall_is_non_negative(self):
        self.assertTrue((self.df["rainfall_mm"] >= 0).all())

    def test_rainfall_values_are_numeric(self):
        rainfall = pd.to_numeric(
            self.df["rainfall_mm"], errors="coerce"
        )

        self.assertFalse(rainfall.isnull().any())

    def test_source_is_gpm_v07b(self):
        self.assertTrue(
            self.df["source"]
            .str.contains("NASA GPM IMERG Final V07B")
            .all()
        )

    def test_coordinates_are_valid(self):
        self.assertTrue(self.df["latitude"].between(-90, 90).all())
        self.assertTrue(self.df["longitude"].between(-180, 180).all())


if __name__ == "__main__":
    unittest.main()
