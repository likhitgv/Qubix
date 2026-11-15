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
        self.assertIn("Your farm", html)
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


if __name__ == "__main__":
    unittest.main()
