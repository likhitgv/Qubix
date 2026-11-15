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




class GridCoverageTests(unittest.TestCase):
    def test_grid_files_cover_india(self):
        pts = svc.load_grid_points()
        self.assertGreater(len(pts), 800)
        self.assertTrue(pts["latitude"].between(6, 36).all())

    def test_nearest_grid_point_in_india(self):
        g = svc.nearest_grid_point(26.91, 75.79)  # Jaipur
        self.assertTrue(g["within_coverage"])
        self.assertLess(g["distance_km"], 45)

    def test_nearest_grid_point_far_from_india(self):
        g = svc.nearest_grid_point(15.0, 66.0)  # Arabian Sea
        self.assertFalse(g["within_coverage"])

    def test_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            svc.nearest_grid_point(95, 10)

    def test_grid_matches_district_files_for_the_same_season(self):
        """The nationwide grid and the district POWER files read the same NASA cell.

        Compared season by season; the two files cover different year ranges, so the
        plan averages differ, but a shared season must agree.
        """
        grid = svc.load_grid_summary()
        districts = svc.load_seasonal_summary()
        from config.districts import DISTRICTS
        for d in DISTRICTS:
            gid = svc.nearest_grid_point(d["latitude"], d["longitude"])["grid_id"]
            a = districts[(districts.location == d["name"]) & (districts.season == "kharif") & (districts.season_year == 2024)].iloc[0]
            b = grid[(grid.location == gid) & (grid.season == "kharif") & (grid.season_year == 2024)].iloc[0]
            self.assertAlmostEqual(a.rainfall_mm, b.rainfall_mm, delta=5, msg=d["name"])
            self.assertAlmostEqual(a.temperature_c, b.temperature_c, delta=0.3, msg=d["name"])

    def test_grid_plan_averages_more_seasons_than_district_file(self):
        g = svc.nearest_grid_point(15.4589, 75.0078)
        plan = svc.build_plan({"district": "Dharwad", "grid_id": g["grid_id"]})
        years = plan["conditions"][0]["environmental_data"]["season_years_used"]
        self.assertGreaterEqual(len(years), 5)

    def test_outside_karnataka_pin_adds_caution(self):
        g = svc.nearest_grid_point(26.91, 75.79)
        plan = svc.build_plan({"district": "Pin", "grid_id": g["grid_id"], "latitude": 26.91, "longitude": 75.79})
        self.assertIn(svc.OUTSIDE_KARNATAKA_NOTE, plan["warnings"])

    def test_pin_inside_karnataka_has_no_caution(self):
        g = svc.nearest_grid_point(15.46, 75.01)
        plan = svc.build_plan({"district": "Dharwad", "grid_id": g["grid_id"], "latitude": 15.46, "longitude": 75.01})
        self.assertNotIn(svc.OUTSIDE_KARNATAKA_NOTE, plan["warnings"])

    def test_unknown_grid_id_raises(self):
        with self.assertRaises(ValueError):
            svc.build_plan({"district": "x", "grid_id": "0.000,0.000"})


if __name__ == "__main__":
    unittest.main()
