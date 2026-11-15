"""Tests for required FIELDWISE AI frontend dependencies."""

import re
import unittest
from pathlib import Path


class FrontendRequirementsTests(unittest.TestCase):

    def test_frontend_dependencies_are_declared(self):
        requirements_file = (
            Path(__file__).resolve().parents[1] / "requirements.txt"
        )

        self.assertTrue(
            requirements_file.exists(),
            "requirements.txt is missing"
        )

        content = requirements_file.read_text(encoding="utf-8")

        declared = {
            match.group(1).lower().replace("_", "-")
            for line in content.splitlines()
            if (match := re.match(
                r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)",
                line
            )) and not line.lstrip().startswith("#")
        }

        required = {
            "streamlit",
            "plotly",
            "folium",
            "streamlit-folium",
        }

        missing = required - declared

        self.assertFalse(
            missing,
            f"Missing frontend dependencies: {sorted(missing)}"
        )


if __name__ == "__main__":
    unittest.main()
