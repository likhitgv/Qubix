"""Headless UI tests using Streamlit AppTest (new KAIRO pill/segmented UI)."""

import os
import unittest
from pathlib import Path
from unittest import mock

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGES = ["Home", "Farm", "Recommendations", "Climate", "Map", "Sustainability", "Advisor", "About"]


def fresh():
    at = AppTest.from_file(APP, default_timeout=90)
    at.run()
    return at


def go(at, page):
    at.session_state["page"] = page
    at.run()


def widget(collection, label):
    return [w for w in collection if w.label == label][0]


def generate(at, soil="Sandy loam"):
    go(at, "Farm")
    widget(at.pills, "Soil type").set_value(soil)
    at.run()
    widget(at.button, "Generate recommendations").click()
    at.run()


def page_text(at):
    return " ".join(str(m.value) for m in at.markdown)


class NavigationTests(unittest.TestCase):
    def test_home_renders(self):
        at = fresh()
        self.assertFalse(at.exception, at.exception)
        self.assertIn("evidence", page_text(at))

    def test_every_page_renders_without_a_farm(self):
        at = fresh()
        for page in PAGES:
            go(at, page)
            self.assertFalse(at.exception, f"{page}: {at.exception}")

    def test_pages_needing_a_farm_show_empty_state(self):
        at = fresh()
        for page in ["Recommendations", "Sustainability", "Advisor"]:
            go(at, page)
            self.assertIn("No farm saved yet", page_text(at), page)

    def test_deselecting_nav_keeps_current_page(self):
        at = fresh()
        go(at, "Climate")
        at.session_state["page"] = None
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["page"], "Climate")


class FarmFlowTests(unittest.TestCase):
    def test_full_flow_generates_recommendations(self):
        at = fresh()
        generate(at)
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["page"], "Recommendations")
        plan = at.session_state["plan"]
        self.assertTrue(plan["rotations"])
        self.assertEqual(at.session_state["profile"]["soil_type"], "sandy-loam")

    def test_every_page_renders_with_a_farm(self):
        at = fresh()
        generate(at)
        for page in PAGES:
            go(at, page)
            self.assertFalse(at.exception, f"{page}: {at.exception}")

    def test_not_sure_soil_is_excluded_from_scoring(self):
        at = fresh()
        generate(at, soil="Not sure")
        self.assertIsNone(at.session_state["profile"]["soil_type"])
        self.assertTrue(any("Soil type not given" in b for b in page_text(at).split("</span>") if b) or
                        "Soil type not given" in page_text(at))

    def test_irrigated_farm_flows_through(self):
        at = fresh()
        go(at, "Farm")
        widget(at.segmented_control, "Water source").set_value("Borewell")
        at.run()
        widget(at.button, "Generate recommendations").click()
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["profile"]["water_availability"], "irrigated")

    def test_previous_crops_reach_the_plan(self):
        at = fresh()
        go(at, "Farm")
        widget(at.pills, "What did you grow recently? (optional)").set_value(["Maize", "Finger millet"])
        at.run()
        widget(at.button, "Generate recommendations").click()
        at.run()
        self.assertEqual(at.session_state["profile"]["previous_crops"], "Maize, Finger millet")

    def test_flagged_crops_show_verification_badge(self):
        at = fresh()
        generate(at)
        self.assertIn("Needs verification", page_text(at))


class GeotagTests(unittest.TestCase):
    def _pin_mode(self, at):
        go(at, "Farm")
        widget(at.segmented_control, "Method").set_value("Pin on map")
        at.run()

    def test_coordinates_outside_coverage_warn(self):
        at = fresh()
        self._pin_mode(at)
        widget(at.number_input, "Latitude").set_value(28.6)
        widget(at.number_input, "Longitude").set_value(77.2)
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertIn("only has data", page_text(at))

    def test_map_click_sets_coordinates_and_nearest_district(self):
        at = fresh()
        self._pin_mode(at)
        at.session_state["_map_click"] = (16.80, 75.70)  # near Vijayapura
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertAlmostEqual(widget(at.number_input, "Latitude").value, 16.80, places=2)
        self.assertIn("Vijayapura", page_text(at))

    def test_pin_inside_coverage_builds_plan_for_nearest_district(self):
        at = fresh()
        self._pin_mode(at)
        at.session_state["_map_click"] = (15.46, 75.01)  # Dharwad
        at.run()
        widget(at.button, "Generate recommendations").click()
        at.run()
        self.assertFalse(at.exception, at.exception)
        self.assertEqual(at.session_state["plan"]["district"], "Dharwad")


class AdvisorTests(unittest.TestCase):
    def _no_key_env(self):
        env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
        return mock.patch.dict(os.environ, env, clear=True), mock.patch("dotenv.load_dotenv")

    def test_advisor_without_key_shows_summary_and_off_notice(self):
        env, dot = self._no_key_env()
        with env, dot:
            at = fresh()
            generate(at)
            go(at, "Advisor")
        self.assertFalse(at.exception, at.exception)
        text = page_text(at)
        self.assertIn("AI explanations are off", text)
        self.assertIn("agronomist", text)


if __name__ == "__main__":
    unittest.main()
