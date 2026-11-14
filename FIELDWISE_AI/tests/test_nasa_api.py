
import unittest
from unittest.mock import patch, Mock

from modules.nasa_api import (
    fetch_power_daily,
    _validate_inputs,
)


class TestNASAPower(unittest.TestCase):

    def test_invalid_latitude(self):
        with self.assertRaises(ValueError):
            _validate_inputs(
                100, 75, "2025-01-01", "2025-01-31", ["T2M"]
            )

    def test_invalid_date_order(self):
        with self.assertRaises(ValueError):
            _validate_inputs(
                15, 75, "2025-02-01", "2025-01-01", ["T2M"]
            )

    @patch("modules.nasa_api.requests.get")
    def test_successful_api_response(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "properties": {
                "parameter": {
                    "T2M": {
                        "20250101": 25.5,
                        "20250102": -999
                    }
                }
            }
        }

        mock_get.return_value = mock_response

        result = fetch_power_daily(
            latitude=15.4589,
            longitude=75.0078,
            start_date="2025-01-01",
            end_date="2025-01-02",
            parameters=["T2M"],
        )

        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["records"][0]["T2M"], 25.5)
        self.assertIsNone(result["records"][1]["T2M"])


if __name__ == "__main__":
    unittest.main()
