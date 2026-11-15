"""Phase 4 tests: map construction."""

import unittest

import pandas as pd

from config.districts import DISTRICTS
from dashboard.map_view import build_map


class MapTests(unittest.TestCase):
    def test_map_has_marker_for_every_district(self):
        html = build_map().get_root().render()
        for d in DISTRICTS:
            self.assertIn(d["name"], html)

    def test_farm_pin_and_link_line_added(self):
        html = build_map("Dharwad", (15.5, 75.1)).get_root().render()
        self.assertIn("Your field", html)
        self.assertIn("dash_array", html.replace("dashArray", "dash_array"))

    def test_popup_includes_seasonal_summary(self):
        summary = pd.DataFrame([{
            "location": "Ballari", "season": "kharif", "complete": True,
            "temperature_c": 26.0, "rainfall_mm": 580.0,
        }])
        html = build_map(summary=summary).get_root().render()
        self.assertIn("NASA POWER seasonal averages", html)

    def test_no_summary_still_renders(self):
        self.assertIn("leaflet", build_map().get_root().render().lower())

    def test_basemap_needs_no_api_key(self):
        html = build_map().get_root().render()
        self.assertIn("openstreetmap.org", html)
        self.assertNotIn("basemaps.cartocdn", html)

    def test_grid_layer_draws_every_point(self):
        pts = pd.DataFrame({"grid_id": ["1.000,2.000", "3.000,4.000"], "latitude": [1.0, 3.0], "longitude": [2.0, 4.0]})
        html = build_map(grid_points=pts, india_view=True).get_root().render()
        self.assertIn("NASA weather area 1.000,2.000", html)
        self.assertIn("NASA weather area 3.000,4.000", html)

    def test_grid_link_draws_ring_and_line(self):
        html = build_map(farm_point=(26.9, 75.8), grid_link=(27.0, 75.6)).get_root().render()
        self.assertIn("NASA weather area used for this field", html)

    def test_india_view_centres_on_india(self):
        html = build_map(india_view=True).get_root().render()
        self.assertIn("22.5", html)


if __name__ == "__main__":
    unittest.main()
