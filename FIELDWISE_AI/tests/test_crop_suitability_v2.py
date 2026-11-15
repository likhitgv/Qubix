
"""Automated tests for Kyro M5 Suitability Engine V2."""

import unittest

from modules.crop_database import load_crop_database
from modules.crop_suitability_v2 import (
    calculate_crop_suitability_v2,
    rank_crops_v2,
)


class CropSuitabilityV2Tests(unittest.TestCase):

    def setUp(self):
        self.crops = load_crop_database()

        # Illustrative test data, NOT live NASA measurements.
        self.environment = {
            "temperature_c": 28,
            "rainfall_mm": 480,
        }

        self.farm = {
            "soil_type": "loamy",
            "water_availability": "rainfed",
            "season": "kharif",
        }

        self.ragi = next(
            crop for crop in self.crops
            if crop["crop_id"] == "ragi"
        )

    def test_matching_conditions_score_100(self):
        result = calculate_crop_suitability_v2(
            self.ragi,
            self.environment,
            self.farm,
        )

        self.assertEqual(result["overall_score"], 100)
        self.assertEqual(result["data_coverage_percent"], 100)
        self.assertTrue(result["eligible_for_ranking"])

    def test_temperature_outside_range_gets_gradual_penalty(self):
        environment = {
            "temperature_c": 25,
            "rainfall_mm": 480,
        }

        result = calculate_crop_suitability_v2(
            self.ragi,
            environment,
            self.farm,
        )

        # Ragi reference temperature range: 26 to 30.
        # One degree outside a four-degree range gives 75.
        self.assertEqual(
            result["component_scores"]["temperature"],
            75,
        )

        self.assertLess(result["overall_score"], 100)

    def test_soil_normalization_handles_whitespace(self):
        farm = {
            **self.farm,
            "soil_type": " LOAMY ",
        }

        result = calculate_crop_suitability_v2(
            self.ragi,
            self.environment,
            farm,
        )

        self.assertEqual(
            result["component_scores"]["soil"],
            100,
        )

    def test_missing_data_is_reported(self):
        result = calculate_crop_suitability_v2(
            self.ragi,
            {},
            {},
        )

        self.assertIsNone(result["overall_score"])
        self.assertEqual(result["data_coverage_percent"], 0)
        self.assertFalse(result["eligible_for_ranking"])
        self.assertGreater(len(result["missing_data"]), 0)

    def test_insufficient_coverage_blocks_ranking(self):
        environment = {
            "temperature_c": 28,
            "rainfall_mm": 480,
        }

        result = calculate_crop_suitability_v2(
            self.ragi,
            environment,
            {},
            minimum_data_coverage=60,
        )

        # Only temperature and rainfall are available: 50%.
        self.assertEqual(result["data_coverage_percent"], 50)
        self.assertFalse(result["eligible_for_ranking"])

    def test_invalid_environment_value_is_rejected(self):
        environment = {
            "temperature_c": float("nan"),
            "rainfall_mm": 480,
        }

        with self.assertRaises(ValueError):
            calculate_crop_suitability_v2(
                self.ragi,
                environment,
                self.farm,
            )

    def test_invalid_coverage_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_crop_suitability_v2(
                self.ragi,
                self.environment,
                self.farm,
                minimum_data_coverage=150,
            )

    def test_ranking_places_eligible_crops_first(self):
        results = rank_crops_v2(
            self.crops,
            self.environment,
            self.farm,
        )

        self.assertEqual(len(results), len(self.crops))

        scores = [
            item["overall_score"]
            for item in results
            if item["eligible_for_ranking"]
        ]

        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_no_data_results_are_not_eligible(self):
        results = rank_crops_v2(
            self.crops,
            {},
            {},
        )

        self.assertTrue(
            all(not item["eligible_for_ranking"] for item in results)
        )


if __name__ == "__main__":
    unittest.main()
