"""Tests for the Member 3 crop-reference database contract."""

import csv
import tempfile
import unittest
from pathlib import Path

from modules.crop_database import (
    CropDatabaseValidationError,
    REQUIRED_COLUMNS,
    crop_database_handoff,
    validate_crop_database,
)


class CropDatabaseTests(unittest.TestCase):
    def test_starter_database_has_a_valid_schema_and_reference_records(self) -> None:
        report = validate_crop_database()

        self.assertTrue(report["valid"])
        self.assertGreaterEqual(report["record_count"], 3)
        self.assertEqual(report["columns"], list(REQUIRED_COLUMNS))

    def test_handoff_is_dashboard_safe_with_reference_records(self) -> None:
        handoff = crop_database_handoff()

        self.assertEqual(len(handoff["records"]), handoff["metadata"]["record_count"])
        self.assertTrue(all("source_urls" in record for record in handoff["records"]))

    def test_missing_required_column_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "incomplete.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(REQUIRED_COLUMNS[:-1])

            with self.assertRaises(CropDatabaseValidationError):
                validate_crop_database(path)


if __name__ == "__main__":
    unittest.main()
