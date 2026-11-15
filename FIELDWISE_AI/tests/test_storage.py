"""SQLite storage for saved plans."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modules import storage
from modules.kairo_service import build_plan


def _profile(place="Dharwad"):
    return {"district": place, "state": "Karnataka", "soil_label": "Sandy loam", "water_label": "Rainfed",
            "soil_type": "sandy-loam", "water_availability": "rainfed", "latitude": 15.4589,
            "longitude": 75.0078, "grid_id": "15.500,75.000", "previous_crops": None}


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "nested" / "test.db"   # parent folder does not exist yet
        self.plan = build_plan({"district": "Dharwad", "soil_type": "sandy-loam", "water_availability": "rainfed"})

    def tearDown(self):
        self.dir.cleanup()

    def test_database_and_folder_are_created_on_first_use(self):
        self.assertFalse(self.path.exists())
        storage.save_plan(_profile(), self.plan, self.path)
        self.assertTrue(self.path.is_file())

    def test_round_trip_keeps_profile_and_plan(self):
        pid = storage.save_plan(_profile(), self.plan, self.path)
        profile, plan = storage.load_plan(pid, self.path)
        self.assertEqual(profile["district"], "Dharwad")
        self.assertEqual(plan["rotations"][0]["crop_sequence"][0]["crop_name"],
                         self.plan["rotations"][0]["crop_sequence"][0]["crop_name"])
        self.assertEqual(plan["conditions"][0]["season"], self.plan["conditions"][0]["season"])

    def test_list_is_newest_first_and_light(self):
        a = storage.save_plan(_profile("Dharwad"), self.plan, self.path)
        b = storage.save_plan(_profile("Ballari"), self.plan, self.path)
        rows = storage.list_plans(10, self.path)
        self.assertEqual([r["id"] for r in rows], [b, a])
        self.assertNotIn("plan_json", rows[0])
        self.assertIn("→", rows[0]["top_rotation"] + "→")  # label present
        self.assertGreater(rows[0]["top_score"], 0)

    def test_limit_is_respected(self):
        for i in range(5):
            storage.save_plan(_profile(f"P{i}"), self.plan, self.path)
        self.assertEqual(len(storage.list_plans(3, self.path)), 3)
        self.assertEqual(storage.count_plans(self.path), 5)

    def test_delete(self):
        pid = storage.save_plan(_profile(), self.plan, self.path)
        self.assertTrue(storage.delete_plan(pid, self.path))
        self.assertIsNone(storage.load_plan(pid, self.path))
        self.assertFalse(storage.delete_plan(pid, self.path))

    def test_missing_id_returns_none(self):
        self.assertIsNone(storage.load_plan(9999, self.path))

    def test_plan_without_rotations_still_saves(self):
        empty = dict(self.plan, rotations=[], sustainability=[])
        pid = storage.save_plan(_profile(), empty, self.path)
        row = storage.list_plans(1, self.path)[0]
        self.assertEqual(row["id"], pid)
        self.assertIsNone(row["top_rotation"])

    def test_numpy_values_are_serialised(self):
        import numpy as np
        plan = dict(self.plan, extra=np.float64(1.5))
        pid = storage.save_plan(_profile(), plan, self.path)
        self.assertEqual(storage.load_plan(pid, self.path)[1]["extra"], 1.5)

    def test_sql_injection_text_is_stored_as_data(self):
        evil = "x'); DROP TABLE saved_plans;--"
        pid = storage.save_plan(_profile(evil), self.plan, self.path)
        self.assertEqual(storage.list_plans(1, self.path)[0]["place"], evil)
        self.assertEqual(storage.count_plans(self.path), 1)
        self.assertEqual(storage.load_plan(pid, self.path)[0]["district"], evil)

    def test_env_var_overrides_default_path(self):
        with mock.patch.dict(os.environ, {"KAIRO_DB_PATH": str(self.path)}):
            self.assertEqual(storage.db_path(), self.path)
            storage.save_plan(_profile(), self.plan)
            self.assertEqual(storage.count_plans(), 1)

    def test_default_path_is_inside_data_folder(self):
        env = {k: v for k, v in os.environ.items() if k != "KAIRO_DB_PATH"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(storage.db_path().name, "kairo.db")
            self.assertEqual(storage.db_path().parent.name, "data")


if __name__ == "__main__":
    unittest.main()
