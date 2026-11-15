"""Plain-language advice wording: only built from computed scores."""

import unittest

from dashboard.advice import fit_reasons, join_phrases, main_caution, rotation_label, season_label


def crop(name, when, **components):
    return {
        "crop_name": name, "season": when,
        "suitability_details": {"component_scores": components},
    }


GOOD = dict(temperature=100, rainfall=100, soil=100, water=100, season=100)


class AdviceTests(unittest.TestCase):
    def test_join_phrases(self):
        self.assertEqual(join_phrases([]), "")
        self.assertEqual(join_phrases(["a"]), "a")
        self.assertEqual(join_phrases(["a", "b"]), "a and b")
        self.assertEqual(join_phrases(["a", "b", "c"]), "a, b and c")

    def test_labels(self):
        rot = {"crop_sequence": [crop("Pigeonpea", "kharif", **GOOD), crop("Maize", "rabi", **GOOD)]}
        self.assertEqual(rotation_label(rot), "Pigeonpea → Maize")
        self.assertEqual(season_label(rot), "Kharif, then Rabi")

    def test_reasons_name_only_strong_components(self):
        rot = {"crop_sequence": [crop("Maize", "rabi", temperature=100, rainfall=10, soil=100, water=100, season=100)]}
        text = fit_reasons(rot)[0]
        self.assertIn("the temperature", text)
        self.assertIn("your soil", text)
        self.assertNotIn("rainfall", text)

    def test_missing_component_is_not_claimed(self):
        rot = {"crop_sequence": [crop("Maize", "rabi", temperature=100, rainfall=100, soil=None, water=None)]}
        text = fit_reasons(rot)[0]
        self.assertNotIn("soil", text)
        self.assertNotIn("water", text)

    def test_partial_fit_when_nothing_is_strong(self):
        rot = {"crop_sequence": [crop("Maize", "rabi", temperature=40, rainfall=30, soil=0, water=50)]}
        self.assertIn("only a partial fit", fit_reasons(rot)[0])

    def test_legume_note_only_when_present(self):
        rot = {"crop_sequence": [crop("Pigeonpea", "kharif", **GOOD)]}
        self.assertEqual(len(fit_reasons(rot, {"available": True, "legume_count": 0})), 1)
        self.assertEqual(len(fit_reasons(rot, {"available": True, "legume_count": 1})), 2)
        self.assertEqual(len(fit_reasons(rot, None)), 1)

    def test_no_caution_when_everything_fits(self):
        rot = {"crop_sequence": [crop("Pigeonpea", "kharif", **GOOD)]}
        self.assertIsNone(main_caution(rot, {}))

    def test_caution_picks_weakest_component_with_numbers_from_weather(self):
        rot = {"crop_sequence": [
            crop("Pigeonpea", "kharif", **GOOD),
            crop("Maize", "rabi", temperature=100, rainfall=6, soil=100, water=100, season=100),
        ]}
        cond = {"rabi": {"temperature_c": 24.2, "rainfall_mm": 28.4}}
        text = main_caution(rot, cond)
        self.assertIn("Maize", text)
        self.assertIn("28 mm", text)

    def test_caution_for_soil_uses_the_farm_soil_name(self):
        rot = {"crop_sequence": [crop("Chickpea", "rabi", temperature=100, rainfall=100, soil=0, water=100)]}
        text = main_caution(rot, {}, {"soil_label": "Red soil"})
        self.assertIn("red soil", text)

    def test_caution_ignores_mild_scores(self):
        rot = {"crop_sequence": [crop("Maize", "rabi", temperature=70, rainfall=65, soil=100, water=100)]}
        self.assertIsNone(main_caution(rot, {}))

    def test_no_forbidden_claims(self):
        rot = {"crop_sequence": [crop("Maize", "rabi", temperature=100, rainfall=6, soil=0, water=0)]}
        text = " ".join(fit_reasons(rot) + [main_caution(rot, {"rabi": {"rainfall_mm": 28}}) or ""]).lower()
        for banned in ("yield", "profit", "guarantee", "will increase", "saves water"):
            self.assertNotIn(banned, text)


if __name__ == "__main__":
    unittest.main()
