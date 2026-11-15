"""Headless UI tests using Streamlit AppTest."""

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def fresh():
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


class AppUITests(unittest.TestCase):
    def test_home_renders_without_exception(self):
        at = fresh()
        self.assertFalse(at.exception, at.exception)

    def test_every_page_renders(self):
        at = fresh()
        for page in ["Home", "Farm", "Recommendations", "Climate", "Sustainability", "About"]:
            at.session_state["page"] = page
            at.run()
            self.assertFalse(at.exception, f"{page}: {at.exception}")

    def test_empty_state_prompts_for_farm(self):
        at = fresh()
        at.session_state["page"] = "Recommendations"
        at.run()
        self.assertTrue(any("Save your farm" in i.value for i in at.info))

    def test_full_flow_generates_recommendations(self):
        at = fresh()
        at.session_state["page"] = "Farm"
        at.run()
        # soil + water selectboxes are inside the form (after the district one)
        soil = [s for s in at.selectbox if s.label == "Soil type"][0]
        soil.select("Sandy loam")
        form_btn = [b for b in at.button if b.label == "Generate recommendations"][0]
        form_btn.click()
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertIsNotNone(at.session_state["plan"])
        self.assertEqual(at.session_state["page"], "Recommendations")
        self.assertTrue(at.session_state["plan"]["rotations"])

    def test_coordinates_outside_coverage_warn(self):
        at = fresh()
        at.session_state["page"] = "Farm"
        at.run()
        [r for r in at.radio if r.label == "Location"][0].set_value("Use coordinates")
        at.run()
        [n for n in at.number_input if n.label == "Latitude"][0].set_value(28.6)
        [n for n in at.number_input if n.label == "Longitude"][0].set_value(77.2)
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertTrue(any("only has data" in m.value for m in at.markdown))


if __name__ == "__main__":
    unittest.main()
