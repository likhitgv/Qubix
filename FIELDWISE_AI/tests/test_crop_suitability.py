
"""Tests for FIELDWISE AI Member 3 crop suitability engine."""

import unittest

from modules.crop_database import load_crop_database
from modules.crop_suitability import (
    calculate_crop_suitability,
    rank_crops,
)


class CropSuitabilityTests(unittest.TestCase):

    def setUp(self):
        self.crops = load_crop_database()

        # Clearly labelled demonstration inputs.
        # These are NOT live NASA measurements.
        self.environment = {
            "temperature_c": 28,
            "rainfall_mm": 480,
            "data_source": "ILLUSTRATIVE_TEST_DATA",
        }

        self.farm = {
            "soil_type": "loamy",
            "water_availability": "rainfed",
            "season": "kharif",
        }

    def test_suitability_returns_expected_structure(self):
        result = calculate_crop_suitability(
            self.crops[0],
            self.environment,
            self.farm,
        )

        self.assertEqual(result["crop_id"], "ragi")
        self.assertIsNotNone(result["overall_score"])
        self.assertIn("temperature", result["component_scores"])
        self.assertIn("explanations", result)
        self.assertIn("missing_data", result)

    def test_matching_crop_scores_100(self):
        ragi = next(
            crop for crop in self.crops
            if crop["crop_id"] == "ragi"
        )

        result = calculate_crop_suitability(
            ragi,
            self.environment,
            self.farm,
        )

        self.assertEqual(result["overall_score"], 100)
        self.assertEqual(result["data_coverage_percent"], 100)

    def test_missing_data_is_reported(self):
        result = calculate_crop_suitability(
            self.crops[0],
            {},
            {},
        )

        self.assertIsNone(result["overall_score"])
        self.assertEqual(result["data_coverage_percent"], 0)
        self.assertGreater(len(result["missing_data"]), 0)

    def test_rank_crops_returns_descending_scores(self):
        results = rank_crops(
            self.crops,
            self.environment,
            self.farm,
        )

        scores = [
            item["overall_score"]
            for item in results
        ]

        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(len(results), len(self.crops))


if __name__ == "__main__":
    unittest.main()
