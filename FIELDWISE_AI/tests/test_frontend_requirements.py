"""Required KAIRO dependencies must be declared in requirements.txt.

Adapted from the teammate's test on feature/member-1-updates.
"""

import re
import unittest
from pathlib import Path


class RequirementsTests(unittest.TestCase):
    def test_dependencies_are_declared(self):
        path = Path(__file__).resolve().parents[1] / "requirements.txt"
        self.assertTrue(path.exists(), "requirements.txt is missing")
        declared = set()
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.lstrip().startswith("#"):
                continue
            m = re.match(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)", line)
            if m:
                declared.add(m.group(1).lower().replace("_", "-"))
        required = {"streamlit", "plotly", "folium", "streamlit-folium",
                    "requests", "pandas", "python-dotenv"}
        self.assertFalse(required - declared, f"Missing: {sorted(required - declared)}")

    def test_no_secrets_in_example_env(self):
        example = Path(__file__).resolve().parents[1] / ".env.example"
        for line in example.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                name, value = line.split("=", 1)
                if name.endswith(("KEY", "PASSWORD")):
                    self.assertEqual(value.strip().strip('"'), "", f"{name} must be blank in .env.example")


if __name__ == "__main__":
    unittest.main()
