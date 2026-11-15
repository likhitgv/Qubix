"""Phase 1 tests: soil/water vocabulary and irrigated-farm scoring."""

import unittest

from config.soils import (
    SOIL_TYPES,
    soil_id_from_label,
    water_availability_from_source,
)
from modules.crop_database import load_crop_database
from modules.crop_suitability_v2 import calculate_crop_suitability_v2, rank_crops_v2

ENV = {"temperature_c": 25.0, "rainfall_mm": 600.0}


class SoilVocabularyTests(unittest.TestCase):
    def test_every_crop_soil_is_selectable(self):
        """Each soil named in the crop database must be offered in the form."""
        offered = {soil_id for soil_id, _ in SOIL_TYPES}
        for crop in load_crop_database():
            for soil in crop["soil_types"]:
                self.assertIn(soil, offered, f"{crop['crop_id']}: {soil}")

    def test_label_and_id_resolve(self):
        self.assertEqual(soil_id_from_label("Red soil"), "red-soil")
        self.assertEqual(soil_id_from_label("sandy-loam"), "sandy-loam")
        self.assertEqual(soil_id_from_label("Black soil (regur)"), "black-soil")

    def test_unknown_soil_is_none(self):
        self.assertIsNone(soil_id_from_label("Not sure"))
        self.assertIsNone(soil_id_from_label(""))
        self.assertIsNone(soil_id_from_label(None))

    def test_water_mapping(self):
        self.assertEqual(water_availability_from_source("Rainfed"), "rainfed")
        self.assertEqual(water_availability_from_source("Borewell"), "irrigated")
        self.assertEqual(water_availability_from_source("Drip irrigation"), "irrigated")
        self.assertIsNone(water_availability_from_source(None))


class WaterScoringTests(unittest.TestCase):
    def setUp(self):
        self.crops = load_crop_database()
        self.ragi = next(c for c in self.crops if c["crop_id"] == "ragi")

    def _water(self, availability, crop):
        profile = {"soil_type": "red-soil", "water_availability": availability, "season": "kharif"}
        result = calculate_crop_suitability_v2(crop, ENV, profile)
        return result["component_scores"]["water"]

    def test_irrigated_farm_not_penalised_for_rainfed_crop(self):
        self.assertEqual(self._water("irrigated", self.ragi), 100.0)

    def test_rainfed_farm_penalised_for_irrigated_crop(self):
        thirsty = dict(self.ragi, water_requirement="irrigated")
        self.assertEqual(self._water("rainfed", thirsty), 0.0)

    def test_flagged_crops_carry_warnings(self):
        profile = {"soil_type": "sandy-loam", "water_availability": "rainfed", "season": "kharif"}
        ranked = rank_crops_v2(self.crops, ENV, profile)
        flagged = {r["crop_id"] for r in ranked if r.get("source_warnings")}
        self.assertTrue({"groundnut", "chickpea", "maize"} <= flagged)


if __name__ == "__main__":
    unittest.main()
