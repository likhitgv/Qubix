"""UI building-block tests: escaping, structure, clamping."""

import unittest

from dashboard import components as ui


class ComponentTests(unittest.TestCase):
    def test_no_blank_lines_or_indented_lines(self):
        """Blank lines or 4-space indents would turn Markdown HTML into code blocks."""
        samples = [
            ui.stat("🌱", "Label", "5", "sub"),
            ui.step_card(1, "T", "text"),
            ui.info_card("📍", "T", "text"),
            ui.ring(88.2),
            ui.score_bars({"temperature": 100, "rainfall": 40}),
            ui.sequence([{"season": "kharif", "crop_name": "Ragi", "suitability_score": 90.0}]),
            ui.grid([ui.stat("x", "a", "b", "c")]),
            ui.topbar_brand(),
            ui.farm_chip(None),
        ]
        for html in samples:
            self.assertNotIn("\n\n", html)
            self.assertFalse(any(line.startswith("    ") for line in html.splitlines()))

    def test_dynamic_text_is_escaped(self):
        evil = '<script>alert("x")</script>'
        for html in (ui.stat("i", evil, evil, evil), ui.tag(evil), ui.info_card("i", evil, evil),
                     ui.sequence([{"season": evil, "crop_name": evil, "suitability_score": 1.0}])):
            self.assertNotIn("<script>", html)

    def test_ring_clamps_and_handles_none(self):
        self.assertIn("--v:100.0", ui.ring(250))
        self.assertIn("--v:0.0", ui.ring(-5))
        self.assertIn("n/a", ui.ring(None))

    def test_score_bars_skip_missing_and_color_by_level(self):
        html = ui.score_bars({"soil": None, "water": 20, "season": 60, "temperature": 95})
        self.assertNotIn("soil", html)
        self.assertIn('class="low"', html)
        self.assertIn('class="mid"', html)

    def test_sequence_marks_unverified_crops(self):
        seq = [
            {"season": "kharif", "crop_name": "Maize", "suitability_score": 80, "source_warnings": ["x"]},
            {"season": "rabi", "crop_name": "Ragi", "suitability_score": 70},
        ]
        html = ui.sequence(seq)
        self.assertEqual(html.count("⚠"), 1)
        self.assertEqual(html.count("arrow"), 1)

    def test_score_color_thresholds(self):
        self.assertEqual(ui.score_color(90), "#34d399")
        self.assertEqual(ui.score_color(65), "#22d3ee")
        self.assertEqual(ui.score_color(45), "#fbbf24")
        self.assertEqual(ui.score_color(10), "#f87171")

    def test_farm_chip_shows_profile(self):
        chip = ui.farm_chip({"district": "Dharwad", "soil_label": "Loam", "water_label": "Rainfed"})
        self.assertIn("Dharwad", chip)


if __name__ == "__main__":
    unittest.main()
