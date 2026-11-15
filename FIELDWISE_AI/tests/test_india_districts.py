"""State -> district data and helpers."""

import unittest

from config.districts import (
    DISTRICTS,
    districts_in_state,
    get_india_district,
    is_validated,
    list_states,
)


class IndiaDistrictsTests(unittest.TestCase):
    def test_states_cover_india(self):
        states = list_states()
        self.assertGreaterEqual(len(states), 30)
        for expected in ("Karnataka", "Maharashtra", "Tamil Nadu", "Rajasthan", "Delhi", "Arunachal Pradesh"):
            self.assertIn(expected, states)

    def test_state_names_are_clean(self):
        states = list_states()
        for old in ("Arunanchal Pradesh", "NCT of Delhi", "Dadara & Nagar Havelli", "Andaman & Nicobar Island"):
            self.assertNotIn(old, states)

    def test_every_state_has_districts_with_valid_coordinates(self):
        for state in list_states():
            rows = districts_in_state(state)
            self.assertTrue(rows, state)
            for r in rows:
                self.assertTrue(6 <= r["latitude"] <= 38 and 68 <= r["longitude"] <= 98, (state, r["district"]))

    def test_districts_sorted_and_unique(self):
        names = [d["district"] for d in districts_in_state("Maharashtra")]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), len(set(names)))

    def test_five_validated_districts_are_present_and_keep_verified_coordinates(self):
        for d in DISTRICTS:
            self.assertTrue(is_validated("Karnataka", d["name"]))
            rec = get_india_district("Karnataka", d["name"])
            self.assertTrue(rec["validated"])
            self.assertEqual((rec["latitude"], rec["longitude"]), (d["latitude"], d["longitude"]))
            self.assertEqual(rec["label"], d["name"])

    def test_other_districts_are_labelled_with_state_and_not_validated(self):
        rec = get_india_district("Maharashtra", "Pune")
        self.assertFalse(rec["validated"])
        self.assertEqual(rec["label"], "Pune, Maharashtra")

    def test_same_district_name_in_different_states_is_distinguished(self):
        """Aurangabad exists in Maharashtra and Bihar."""
        a = get_india_district("Maharashtra", "Aurangabad")
        b = get_india_district("Bihar", "Aurangabad")
        self.assertNotEqual((a["latitude"], a["longitude"]), (b["latitude"], b["longitude"]))

    def test_unknown_inputs_raise(self):
        with self.assertRaises(KeyError):
            districts_in_state("Atlantis")
        with self.assertRaises(KeyError):
            get_india_district("Karnataka", "Atlantis")


if __name__ == "__main__":
    unittest.main()
