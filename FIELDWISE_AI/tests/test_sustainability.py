"""Phase 2 tests: sustainability indicators."""

import unittest

from modules.crop_database import load_crop_database
from modules.sustainability import compare_rotations, evaluate_rotation_sustainability


def _rotation(*crop_ids, rank=1):
    return {
        "rank": rank,
        "crop_sequence": [
            {"season": s, "crop_id": cid}
            for s, cid in zip(("kharif", "rabi", "summer"), crop_ids)
        ],
    }


class SustainabilityTests(unittest.TestCase):
    def setUp(self):
        self.crops = load_crop_database()

    def test_legume_rotation_scores_full(self):
        result = evaluate_rotation_sustainability(_rotation("ragi", "chickpea"), self.crops)
        self.assertTrue(result["available"])
        self.assertEqual(result["legume_count"], 1)
        self.assertFalse(result["consecutive_family_repeat"])
        self.assertEqual(result["indicator_score"], 100)

    def test_cereal_only_rotation_scores_lower(self):
        result = evaluate_rotation_sustainability(_rotation("ragi", "maize"), self.crops)
        self.assertEqual(result["legume_count"], 0)
        self.assertTrue(result["consecutive_family_repeat"])
        self.assertLess(result["indicator_score"], 50)

    def test_previous_crop_same_family_warns(self):
        result = evaluate_rotation_sustainability(
            _rotation("ragi", "chickpea"), self.crops, "Sorghum last year"
        )
        names = {i["name"]: i["status"] for i in result["indicators"]}
        self.assertEqual(names["Previous crops"], "warning")

    def test_unknown_crop_is_unavailable_not_crash(self):
        result = evaluate_rotation_sustainability(_rotation("nonexistent"), self.crops)
        self.assertFalse(result["available"])

    def test_note_always_present_and_no_savings_claims(self):
        result = evaluate_rotation_sustainability(_rotation("ragi", "chickpea"), self.crops)
        self.assertIn("not measured", result["note"])
        text = str(result).lower()
        for banned in ("water saved", "yield increase", "% less water"):
            self.assertNotIn(banned, text)

    def test_compare_keeps_order(self):
        out = compare_rotations(
            [_rotation("ragi", "chickpea", rank=1), _rotation("ragi", "maize", rank=2)],
            self.crops,
        )
        self.assertEqual([o["rotation_rank"] for o in out], [1, 2])


if __name__ == "__main__":
    unittest.main()
