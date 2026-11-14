
import unittest

from modules.rotation_engine import (
    generate_crop_rotations,
)


class RotationEngineTests(unittest.TestCase):

    def setUp(self):

        # Independent test data.
        # These are illustrative fixtures, not real crop recommendations.

        self.crops = [
            {
                "crop_id": "ragi",
                "crop_name": "Finger millet",
                "crop_family": "Poaceae",
                "suitable_seasons": ["kharif", "rabi"],
                "soil_types": ["loamy"],
                "min_temperature_c": 20,
                "max_temperature_c": 35,
                "min_rainfall_mm": 100,
                "max_rainfall_mm": 1000,
                "water_requirement": "rainfed",
                "legume": False,
            },
            {
                "crop_id": "pigeonpea",
                "crop_name": "Pigeonpea",
                "crop_family": "Fabaceae",
                "suitable_seasons": ["kharif", "rabi"],
                "soil_types": ["loamy"],
                "min_temperature_c": 20,
                "max_temperature_c": 40,
                "min_rainfall_mm": 100,
                "max_rainfall_mm": 1200,
                "water_requirement": "rainfed",
                "legume": True,
            },
            {
                "crop_id": "sorghum",
                "crop_name": "Sorghum",
                "crop_family": "Poaceae",
                "suitable_seasons": ["kharif", "rabi"],
                "soil_types": ["loamy"],
                "min_temperature_c": 20,
                "max_temperature_c": 35,
                "min_rainfall_mm": 100,
                "max_rainfall_mm": 1000,
                "water_requirement": "rainfed",
                "legume": False,
            },
            {
                "crop_id": "chickpea",
                "crop_name": "Chickpea",
                "crop_family": "Fabaceae",
                "suitable_seasons": ["rabi"],
                "soil_types": ["loamy"],
                "min_temperature_c": 15,
                "max_temperature_c": 32,
                "min_rainfall_mm": 100,
                "max_rainfall_mm": 1000,
                "water_requirement": "rainfed",
                "legume": True,
            },
        ]

        self.seasonal_conditions = [
            {
                "season": "kharif",
                "environmental_data": {
                    "temperature_c": 28,
                    "rainfall_mm": 500,
                },
            },
            {
                "season": "rabi",
                "environmental_data": {
                    "temperature_c": 25,
                    "rainfall_mm": 400,
                },
            },
        ]

        self.farm_profile = {
            "soil_type": "loamy",
            "water_availability": "rainfed",
        }

    def generate(self, **kwargs):
        top_n = kwargs.pop("top_n", 100)

        return generate_crop_rotations(
            crops=self.crops,
            seasonal_conditions=self.seasonal_conditions,
            farm_profile=self.farm_profile,
            top_n=top_n,
            **kwargs,
        )

    def test_rotation_generation_returns_results(self):
        results = self.generate()

        self.assertGreater(len(results), 0)

    def test_rotations_contain_all_requested_seasons(self):
        results = self.generate()

        for rotation in results:
            self.assertEqual(
                rotation["seasons"],
                ["kharif", "rabi"],
            )

    def test_same_crop_is_not_planted_consecutively(self):
        results = self.generate()

        for rotation in results:
            crop_ids = [
                item["crop_id"]
                for item in rotation["crop_sequence"]
            ]

            self.assertNotEqual(
                crop_ids[0],
                crop_ids[1],
            )

    def test_repeated_family_receives_penalty(self):
        results = self.generate()

        repeated_family_rotation = next(
            (
                rotation
                for rotation in results
                if rotation["family_penalty"] > 0
            ),
            None,
        )

        self.assertIsNotNone(repeated_family_rotation)

    def test_legume_followed_by_non_legume_receives_bonus(self):
        results = self.generate()

        legume_rotation = next(
            (
                rotation
                for rotation in results
                if rotation["legume_bonus"] > 0
            ),
            None,
        )

        self.assertIsNotNone(legume_rotation)

    def test_rotations_are_ranked_descending(self):
        results = self.generate()

        scores = [
            rotation["overall_rotation_score"]
            for rotation in results
        ]

        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_missing_season_candidates_return_empty_list(self):
        conditions = [
            {
                "season": "unknown_season",
                "environmental_data": {
                    "temperature_c": 28,
                    "rainfall_mm": 500,
                },
            },
            {
                "season": "rabi",
                "environmental_data": {
                    "temperature_c": 25,
                    "rainfall_mm": 400,
                },
            },
        ]

        results = generate_crop_rotations(
            crops=self.crops,
            seasonal_conditions=conditions,
            farm_profile=self.farm_profile,
        )

        self.assertEqual(results, [])

    def test_invalid_top_n_is_rejected(self):
        with self.assertRaises(ValueError):
            self.generate(top_n=0)

    def test_source_metadata_is_preserved_in_crop_sequence(self):
        self.crops[0].update({
            "source_name": "Test Agriculture Reference",
            "source_urls": ["https://example.com/crop-reference"],
            "source_accessed_date": "2026-11-14",
            "source_notes": "Illustrative test reference.",
        })

        results = self.generate()

        rotation = next(
            (
                item for item in results
                if any(
                    crop["crop_id"] == "ragi"
                    for crop in item["crop_sequence"]
                )
            ),
            None,
        )

        self.assertIsNotNone(rotation)

        ragi = next(
            crop for crop in rotation["crop_sequence"]
            if crop["crop_id"] == "ragi"
        )

        self.assertEqual(
            ragi["source_name"],
            "Test Agriculture Reference",
        )
        self.assertEqual(
            ragi["source_urls"],
            ["https://example.com/crop-reference"],
        )
        self.assertEqual(
            ragi["source_accessed_date"],
            "2026-11-14",
        )
        self.assertIn("suitability_details", ragi)

    def test_source_warnings_are_propagated_to_rotation(self):
        self.crops[0].update({
            "source_name": "Test Agriculture Reference",
            "source_notes": (
                "NEEDS VERIFICATION: illustrative test warning."
            ),
        })

        results = self.generate()

        rotation = next(
            (
                item for item in results
                if any(
                    crop["crop_id"] == "ragi"
                    for crop in item["crop_sequence"]
                )
            ),
            None,
        )

        self.assertIsNotNone(rotation)

        self.assertTrue(rotation["source_warnings"])

        self.assertTrue(
            any(
                "Finger millet" in warning
                for warning in rotation["source_warnings"]
            )
        )

        ragi = next(
            crop for crop in rotation["crop_sequence"]
            if crop["crop_id"] == "ragi"
        )

        self.assertEqual(
            ragi["source_verification"],
            "needs_verification",
        )


if __name__ == "__main__":
    unittest.main()
