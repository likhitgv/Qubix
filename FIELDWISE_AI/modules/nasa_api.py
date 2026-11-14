
"""
NASA POWER Daily API integration for FIELDWISE AI.

Retrieves daily meteorological and solar data for Karnataka locations.
API documentation:
https://power.larc.nasa.gov/docs/services/api/temporal/daily/
"""

from datetime import date
from typing import Dict, List, Tuple, Optional

import requests


BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

DEFAULT_PARAMETERS = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
]

DEFAULT_COMMUNITY = "AG"
DEFAULT_TIMEOUT = 30

# -999 is NASA POWER's missing-data indicator.
MISSING_VALUE = -999


class NASAPowerError(Exception):
    """Raised when NASA POWER data cannot be retrieved or parsed."""


def _validate_inputs(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    parameters: List[str],
) -> None:
    """Validate coordinates, dates, and requested parameters."""

    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD format.") from exc

    if start > end:
        raise ValueError("Start date cannot be after end date.")

    if not parameters:
        raise ValueError("At least one parameter must be requested.")

    if len(parameters) > 20:
        raise ValueError("A maximum of 20 parameters can be requested.")


def fetch_power_daily(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    parameters: Optional[List[str]] = None,
    community: str = DEFAULT_COMMUNITY,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict:
    """
    Fetch daily NASA POWER data for one geographic point.

    Returns:
        Dictionary containing location, metadata, and daily records.
        Missing measurements are represented as None.
    """

    parameters = parameters or DEFAULT_PARAMETERS

    _validate_inputs(
        latitude, longitude, start_date, end_date, parameters
    )

    request_parameters = {
        "parameters": ",".join(parameters),
        "community": community,
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date.replace("-", ""),
        "end": end_date.replace("-", ""),
        "format": "JSON",
        "time-standard": "UTC",
    }

    try:
        response = requests.get(
            BASE_URL,
            params=request_parameters,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()

    except requests.exceptions.Timeout as exc:
        raise NASAPowerError("NASA POWER request timed out.") from exc

    except requests.exceptions.RequestException as exc:
        raise NASAPowerError(
            f"NASA POWER request failed: {exc}"
        ) from exc

    except ValueError as exc:
        raise NASAPowerError(
            "NASA POWER returned invalid JSON."
        ) from exc

    if not isinstance(payload, dict):
        raise NASAPowerError("Unexpected NASA POWER response format.")

    if payload.get("messages"):
        messages = payload["messages"]
        raise NASAPowerError(f"NASA POWER API message: {messages}")

    try:
        properties = payload["properties"]
        parameter_data = properties["parameter"]
    except (KeyError, TypeError) as exc:
        raise NASAPowerError(
            "NASA POWER response is missing parameter data."
        ) from exc

    if not parameter_data:
        raise NASAPowerError("NASA POWER returned no parameter data.")

    # Combine individual parameter time series by date.
    records_by_date = {}

    for parameter_name, daily_values in parameter_data.items():
        for day, value in daily_values.items():
            if day not in records_by_date:
                records_by_date[day] = {"date": day}

            if value is None or value == MISSING_VALUE:
                records_by_date[day][parameter_name] = None
            else:
                records_by_date[day][parameter_name] = float(value)

    records = [
        records_by_date[day]
        for day in sorted(records_by_date)
    ]

    return {
        "source": "NASA POWER",
        "latitude": latitude,
        "longitude": longitude,
        "community": community,
        "time_standard": "UTC",
        "requested_parameters": parameters,
        "metadata": properties.get("parameter", {}),
        "records": records,
    }


def fetch_for_locations(
    locations: Dict[str, Tuple[float, float]],
    start_date: str,
    end_date: str,
    parameters: Optional[List[str]] = None,
) -> Dict[str, Dict]:
    """
    Fetch NASA POWER data for multiple named locations.

    locations format:
        {"Dharwad": (latitude, longitude)}
    """

    results = {}

    for location_name, coordinates in locations.items():
        latitude, longitude = coordinates

        results[location_name] = fetch_power_daily(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
        )

    return results
