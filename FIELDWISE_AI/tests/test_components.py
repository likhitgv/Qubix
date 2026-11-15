"""UI building-block tests: escaping, structure, wording."""

import unittest

from dashboard import components as ui


class ComponentTests(unittest.TestCase):
    def test_no_blank_lines_or_indented_lines(self):
        """Blank lines or 4-space indents would turn Markdown HTML into code blocks."""
        samples = [
            ui.page_header("Title", "Sub"),
            ui.step(1, "Where is your field?", "hint"),
            ui.brand(),
            ui.field_note(None),
            ui.source_line("x"),
            ui.note_html("hello", "caution"),
            ui.reco_card("Best option", "Ragi", "Kharif", "Fit 90", ["a", "b"], "careful", "Check."),
            ui.alt_card("Option 2", "Maize", "meta", "caution"),
            ui.facts([("k", "v", "s")]),
            ui.score_bars({"temperature": 100, "rainfall": 40}),
            ui.grid([ui.alt_card("a", "b", "c")]),
        ]
        for html in samples:
            self.assertNotIn("\n\n", html)
            self.assertFalse(any(line.startswith("    ") for line in html.splitlines()))

    def test_dynamic_text_is_escaped(self):
        evil = '<script>alert("x")</script>'
        for html in (ui.page_header(evil, evil), ui.step(1, evil, evil), ui.source_line(evil),
                     ui.reco_card(evil, evil, evil, evil, [evil], evil, evil), ui.alt_card(evil, evil, evil, evil),
                     ui.facts([(evil, evil, evil)]), ui.score_bars({evil: 50}),
                     ui.field_note({"district": evil, "soil_label": evil, "water_label": evil})):
            self.assertNotIn("<script>", html)

    def test_step_number_and_text(self):
        html = ui.step(3, "How is this field irrigated?", "Rainfed means rain only.")
        self.assertIn(">3<", html)
        self.assertIn("How is this field irrigated?", html)

    def test_reco_card_structure(self):
        html = ui.reco_card("Best option", "Pigeonpea → Maize", "Kharif, then Rabi", "Fit score 93 out of 100",
                            ["Pigeonpea suits the temperature."], "Maize rain is low.", "Check with a local agronomist before planting.")
        for expected in ("Best option", "Why this may fit your field", "Keep in mind", "agronomist"):
            self.assertIn(expected, html)

    def test_reco_card_omits_empty_sections(self):
        html = ui.reco_card("Best option", "Ragi", "Kharif", "Fit 90", [], None, "Check.")
        self.assertNotIn("Why this may fit", html)
        self.assertNotIn("Keep in mind", html)

    def test_score_bars_skip_missing_and_color_by_level(self):
        html = ui.score_bars({"soil": None, "water": 20, "season": 60, "temperature": 95})
        self.assertNotIn("soil", html)
        self.assertIn('class="low"', html)
        self.assertIn('class="mid"', html)

    def test_field_note_shows_profile_or_empty(self):
        self.assertIn("No field added yet", ui.field_note(None))
        note = ui.field_note({"district": "Dharwad", "soil_label": "Loam", "water_label": "Rainfed"})
        self.assertIn("Dharwad", note)

    def test_banner_tone_mapping(self):
        self.assertIn("caution", ui.note_html("x", "caution"))
        self.assertIn("good", ui.note_html("x", "good"))

    def test_grid_columns(self):
        self.assertIn("g3", ui.grid(["a"], cols=3))
        self.assertIn("g2", ui.grid(["a"], cols=2))


if __name__ == "__main__":
    unittest.main()
