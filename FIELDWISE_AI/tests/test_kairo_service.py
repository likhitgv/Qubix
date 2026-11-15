"""Phase 3 service-layer tests."""

import unittest
from unittest import mock

from modules import kairo_service as svc
from modules.nasa_api import NASAPowerError


class GeotagTests(unittest.TestCase):
    def test_exact_district_point(self):
        r = svc.nearest_district(15.4589, 75.0078)
        self.assertEqual(r["district"], "Dharwad")
        self.assertEqual(r["distance_km"], 0.0)
        self.assertTrue(r["within_coverage"])

    def test_nearby_point_picks_nearest(self):
        r = svc.nearest_district(15.2, 76.8)
        self.assertEqual(r["district"], "Ballari")

    def test_far_point_flagged_outside_coverage(self):
        r = svc.nearest_district(28.6, 77.2)  # Delhi
        self.assertFalse(r["within_coverage"])

    def test_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            svc.nearest_district(120, 10)


class PlanTests(unittest.TestCase):
    def test_plan_for_every_district(self):
        for name in ["Ballari", "Shivamogga", "Vijayapura", "Belagavi", "Dharwad"]:
            plan = svc.build_plan(
                {"district": name, "soil_type": "sandy-loam", "water_availability": "rainfed"}
            )
            self.assertEqual(plan["district"], name)
            self.assertEqual(len(plan["sustainability"]), len(plan["rotations"]))
            self.assertIn("decision support", plan["disclaimer"])
            self.assertIn("modelled", plan["data_nature"])

    def test_missing_soil_and_water_warn(self):
        plan = svc.build_plan({"district": "Ballari"})
        self.assertTrue(any("Soil" in w for w in plan["warnings"]))
        self.assertTrue(any("Water" in w for w in plan["warnings"]))

    def test_unknown_district_raises(self):
        with self.assertRaises(ValueError):
            svc.build_plan({"district": "Atlantis"})

    def test_missing_district_raises(self):
        with self.assertRaises(ValueError):
            svc.build_plan({})

    def test_live_fetch_error_propagates(self):
        with mock.patch.object(svc, "fetch_for_district", side_effect=NASAPowerError("down")):
            with self.assertRaises(NASAPowerError):
                svc.fetch_live_seasonal_summary("Ballari")


class ProvenanceTests(unittest.TestCase):
    def test_known_district_has_source_and_period(self):
        meta = svc.load_provenance("Ballari")
        self.assertEqual(meta["source"], "NASA POWER")
        self.assertIn("start_date", meta)

    def test_unknown_district_is_empty(self):
        self.assertEqual(svc.load_provenance("Atlantis"), {})


if __name__ == "__main__":
    unittest.main()
