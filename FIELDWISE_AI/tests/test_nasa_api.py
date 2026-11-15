import unittest
from unittest.mock import patch, Mock

import requests

from modules.nasa_api import (
    NASAPowerError,
    fetch_power_daily,
    fetch_for_locations,
    to_climate_dataframe,
    to_long_dataframe,
    load_sample_data,
    _validate_inputs,
)


def _ok_response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


PAYLOAD = {
    "properties": {
        "parameter": {
            "T2M": {"20250101": 25.5, "20250102": -999},
            "PRECTOTCORR": {"20250101": 0.0, "20250102": 3.2},
        }
    },
    "parameters": {
        "T2M": {"units": "C", "longname": "Temperature at 2 Meters"},
        "PRECTOTCORR": {"units": "mm/day", "longname": "Precipitation Corrected"},
    },
}


def _fetch(**kwargs):
    return fetch_power_daily(
        latitude=15.4589,
        longitude=75.0078,
        start_date="2025-01-01",
        end_date="2025-01-02",
        parameters=["T2M", "PRECTOTCORR"],
        **kwargs,
    )


class TestValidation(unittest.TestCase):
    def test_invalid_latitude(self):
        with self.assertRaises(ValueError):
            _validate_inputs(100, 75, "2025-01-01", "2025-01-31", ["T2M"])

    def test_invalid_longitude(self):
        with self.assertRaises(ValueError):
            _validate_inputs(15, 200, "2025-01-01", "2025-01-31", ["T2M"])

    def test_invalid_date_order(self):
        with self.assertRaises(ValueError):
            _validate_inputs(15, 75, "2025-02-01", "2025-01-01", ["T2M"])

    def test_invalid_date_format(self):
        with self.assertRaises(ValueError):
            _validate_inputs(15, 75, "01-01-2025", "2025-01-31", ["T2M"])

    def test_too_many_parameters(self):
        with self.assertRaises(ValueError):
            _validate_inputs(15, 75, "2025-01-01", "2025-01-02", ["P"] * 21)


class TestFetch(unittest.TestCase):
    @patch("modules.nasa_api.requests.get")
    def test_success_and_missing_value(self, mock_get):
        mock_get.return_value = _ok_response(PAYLOAD)
        result = _fetch()

        self.assertEqual(len(result["records"]), 2)
        self.assertEqual(result["records"][0]["T2M"], 25.5)
        self.assertIsNone(result["records"][1]["T2M"])

    @patch("modules.nasa_api.requests.get")
    def test_metadata_has_units_and_provenance(self, mock_get):
        mock_get.return_value = _ok_response(PAYLOAD)
        meta = _fetch()["metadata"]

        self.assertEqual(meta["units"]["PRECTOTCORR"], "mm/day")
        self.assertEqual(meta["missing_counts"]["T2M"], 1)
        self.assertFalse(meta["is_sample_data"])
        self.assertIn("retrieved_at", meta)
        self.assertTrue(meta["processing_steps"])

    @patch("modules.nasa_api.requests.get")
    def test_timeout_raises_after_retries(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        with self.assertRaises(NASAPowerError):
            _fetch(retries=2)
        self.assertEqual(mock_get.call_count, 3)

    @patch("modules.nasa_api.requests.get")
    def test_network_unavailable(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("offline")
        with self.assertRaises(NASAPowerError):
            _fetch(retries=0)

    @patch("modules.nasa_api.requests.get")
    def test_client_error_not_retried(self, mock_get):
        response = Mock()
        response.status_code = 422
        response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "422", response=response
        )
        mock_get.return_value = response
        with self.assertRaises(NASAPowerError):
            _fetch(retries=2)
        self.assertEqual(mock_get.call_count, 1)

    @patch("modules.nasa_api.requests.get")
    def test_invalid_json(self, mock_get):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("bad json")
        mock_get.return_value = response
        with self.assertRaises(NASAPowerError):
            _fetch(retries=0)

    @patch("modules.nasa_api.requests.get")
    def test_empty_response(self, mock_get):
        mock_get.return_value = _ok_response({"properties": {"parameter": {}}})
        with self.assertRaises(NASAPowerError):
            _fetch()

    @patch("modules.nasa_api.requests.get")
    def test_missing_properties(self, mock_get):
        mock_get.return_value = _ok_response({"unexpected": 1})
        with self.assertRaises(NASAPowerError):
            _fetch()

    @patch("modules.nasa_api.requests.get")
    def test_api_message_raises(self, mock_get):
        mock_get.return_value = _ok_response({"messages": ["bad request"]})
        with self.assertRaises(NASAPowerError):
            _fetch()

    @patch("modules.nasa_api.requests.get")
    def test_fetch_for_locations_sets_names(self, mock_get):
        mock_get.return_value = _ok_response(PAYLOAD)
        results = fetch_for_locations(
            {"Dharwad": (15.4589, 75.0078)},
            "2025-01-01",
            "2025-01-02",
            ["T2M", "PRECTOTCORR"],
        )
        self.assertEqual(results["Dharwad"]["location"], "Dharwad")


class TestDataFrames(unittest.TestCase):
    @patch("modules.nasa_api.requests.get")
    def test_climate_dataframe_columns(self, mock_get):
        mock_get.return_value = _ok_response(PAYLOAD)
        df = to_climate_dataframe(_fetch(), "Dharwad")

        for column in ["date", "location", "latitude", "longitude",
                       "temperature_c", "rainfall_mm", "source"]:
            self.assertIn(column, df.columns)
        self.assertEqual(df["location"].iloc[0], "Dharwad")
        self.assertEqual(df["rainfall_mm"].iloc[1], 3.2)
        self.assertTrue(df["temperature_c"].isna().iloc[1])

    @patch("modules.nasa_api.requests.get")
    def test_long_dataframe(self, mock_get):
        mock_get.return_value = _ok_response(PAYLOAD)
        df = to_long_dataframe(_fetch(), "Dharwad")

        self.assertEqual(len(df), 4)  # 2 days x 2 variables
        self.assertEqual(
            set(df["unit"]), {"C", "mm/day"}
        )

    def test_sample_data_is_labelled(self):
        df = load_sample_data()
        self.assertEqual(set(df["source"]), {"SAMPLE"})


if __name__ == "__main__":
    unittest.main()
