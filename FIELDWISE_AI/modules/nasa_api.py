"""
NASA POWER Daily API integration for FIELDWISE AI (Module M2).

Retrieves daily meteorological and solar data for Karnataka locations.
API documentation:
https://power.larc.nasa.gov/docs/services/api/temporal/daily/

Public functions
----------------
fetch_power_daily(lat, lon, start, end)  -> dict (records + metadata)
fetch_for_locations({name: (lat, lon)}, start, end) -> {name: dict}
fetch_for_district(name, start, end)     -> dict (uses config/districts.py)
to_climate_dataframe(result, location)   -> wide DataFrame (Member 2 input)
to_long_dataframe(result, location)      -> long DataFrame (date, variable,
                                            value, unit, source, ...)
load_sample_data()                       -> labelled SAMPLE fallback data
"""

from datetime import date, datetime, timezone
from typing import Dict, List, Tuple, Optional

import pandas as pd
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
DEFAULT_RETRIES = 2

# -999 is NASA POWER's missing-data indicator.
MISSING_VALUE = -999

# Fallback (description, unit) used only if the API response omits them.
PARAMETER_INFO = {
    "T2M": ("Temperature at 2 Meters", "C"),
    "T2M_MAX": ("Temperature at 2 Meters Maximum", "C"),
    "T2M_MIN": ("Temperature at 2 Meters Minimum", "C"),
    "PRECTOTCORR": ("Precipitation Corrected", "mm/day"),
    "RH2M": ("Relative Humidity at 2 Meters", "%"),
    "ALLSKY_SFC_SW_DWN": (
        "All Sky Surface Shortwave Downward Irradiance",
        "MJ/m^2/day",
    ),
}

DATA_NATURE = (
    "NASA POWER is a gridded product derived from satellite observations "
    "and reanalysis models (e.g. MERRA-2). Values describe a grid cell; "
    "they are not direct field or weather-station measurements."
)


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


def _request_json(request_parameters: Dict, timeout: int, retries: int):
    """GET the API with retries on transient failures; return parsed JSON."""

    last_error: Optional[NASAPowerError] = None

    for _attempt in range(max(0, retries) + 1):
        try:
            response = requests.get(
                BASE_URL,
                params=request_parameters,
                timeout=timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout as exc:
            last_error = NASAPowerError("NASA POWER request timed out.")
            last_error.__cause__ = exc

        except requests.exceptions.HTTPError as exc:
            last_error = NASAPowerError(f"NASA POWER request failed: {exc}")
            last_error.__cause__ = exc
            status = getattr(exc.response, "status_code", None)
            # Client errors (bad parameters etc.) will not fix themselves.
            if status is not None and 400 <= status < 500 and status != 429:
                break

        except requests.exceptions.RequestException as exc:
            last_error = NASAPowerError(f"NASA POWER request failed: {exc}")
            last_error.__cause__ = exc

        except ValueError as exc:
            last_error = NASAPowerError("NASA POWER returned invalid JSON.")
            last_error.__cause__ = exc
            break

    raise last_error


def fetch_power_daily(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    parameters: Optional[List[str]] = None,
    community: str = DEFAULT_COMMUNITY,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = DEFAULT_RETRIES,
) -> Dict:
    """
    Fetch daily NASA POWER data for one geographic point.

    Returns:
        Dictionary with keys: source, latitude, longitude, community,
        time_standard, requested_parameters, metadata, records.
        `records` is a list of {"date": "YYYYMMDD", <parameter>: float|None}.
        Missing measurements are represented as None.
        `metadata` holds units, retrieval time, period and processing steps.
    """

    parameters = parameters or DEFAULT_PARAMETERS

    _validate_inputs(latitude, longitude, start_date, end_date, parameters)

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

    payload = _request_json(request_parameters, timeout, retries)

    if not isinstance(payload, dict):
        raise NASAPowerError("Unexpected NASA POWER response format.")

    if payload.get("messages"):
        raise NASAPowerError(
            f"NASA POWER API message: {payload['messages']}"
        )

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

    records = [records_by_date[day] for day in sorted(records_by_date)]

    # Units/descriptions: prefer the API's own "parameters" block.
    api_parameters = payload.get("parameters") or {}
    units = {}
    descriptions = {}
    for name in parameter_data:
        api_info = api_parameters.get(name) or {}
        fallback = PARAMETER_INFO.get(name, (name, "unknown"))
        units[name] = api_info.get("units") or fallback[1]
        descriptions[name] = api_info.get("longname") or fallback[0]

    missing_counts = {
        name: sum(1 for r in records if r.get(name) is None)
        for name in parameter_data
    }

    metadata = {
        "source": "NASA POWER",
        "api_endpoint": BASE_URL,
        "data_nature": DATA_NATURE,
        "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "start_date": start_date,
        "end_date": end_date,
        "units": units,
        "descriptions": descriptions,
        "missing_counts": missing_counts,
        "is_sample_data": False,
        "processing_steps": [
            "Requested daily point data from NASA POWER API (JSON, UTC).",
            "Merged per-parameter series by date.",
            f"Converted fill value {MISSING_VALUE} and null to None (missing).",
        ],
    }

    return {
        "source": "NASA POWER",
        "latitude": latitude,
        "longitude": longitude,
        "community": community,
        "time_standard": "UTC",
        "requested_parameters": parameters,
        "metadata": metadata,
        "records": records,
    }


def to_long_dataframe(result: Dict, location: Optional[str] = None) -> pd.DataFrame:
    """
    Long format: one row per (date, variable).

    Columns: date, location, latitude, longitude, variable, value, unit,
    source, retrieved_at, is_sample_data.
    """

    meta = result["metadata"]
    rows = []
    for record in result["records"]:
        for variable, unit in meta["units"].items():
            rows.append({
                "date": pd.to_datetime(record["date"], format="%Y%m%d"),
                "location": location,
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "variable": variable,
                "value": record.get(variable),
                "unit": unit,
                "source": result["source"],
                "retrieved_at": meta["retrieved_at"],
                "is_sample_data": meta["is_sample_data"],
            })
    return pd.DataFrame(rows)


def to_climate_dataframe(result: Dict, location: Optional[str] = None) -> pd.DataFrame:
    """
    Wide DataFrame accepted directly by
    modules.data_analysis.clean_climate_data().

    Columns: date, location, latitude, longitude, <NASA variables>,
    temperature_c (= T2M, deg C), rainfall_mm (= PRECTOTCORR, mm/day),
    source ("NASA POWER").
    """

    location = location or result.get("location")
    df = pd.DataFrame(result["records"])
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df.insert(1, "location", location)
    df.insert(2, "latitude", result["latitude"])
    df.insert(3, "longitude", result["longitude"])
    df["temperature_c"] = df["T2M"] if "T2M" in df else None
    df["rainfall_mm"] = df["PRECTOTCORR"] if "PRECTOTCORR" in df else None
    df["source"] = result["source"]
    return df


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

    for location_name, (latitude, longitude) in locations.items():
        result = fetch_power_daily(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
        )
        result["location"] = location_name
        results[location_name] = result

    return results


def fetch_for_district(
    district: str,
    start_date: str,
    end_date: str,
    parameters: Optional[List[str]] = None,
) -> Dict:
    """Fetch data for a configured district name (see config/districts.py)."""

    from config.districts import get_district

    info = get_district(district)
    result = fetch_power_daily(
        info["latitude"], info["longitude"], start_date, end_date, parameters
    )
    result["location"] = info["name"]
    return result


def load_sample_data(path: str = "data/sample_climate_data.csv") -> pd.DataFrame:
    """
    Offline fallback when the API is unreachable. Rows carry
    source == "SAMPLE"; the UI must disclose this as demo data, never as
    live NASA data.
    """

    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Seasonal summaries (daily data -> kharif / rabi / summer)
# ---------------------------------------------------------------------------

# (first month, last month). Rabi runs Nov of year Y to Mar of year Y+1 and
# is labelled with the year it starts in. Season windows are the common
# Karnataka agricultural calendar and are an assumption, not an official one.
SEASON_MONTHS = {
    "kharif": (6, 10),
    "rabi": (11, 3),
    "summer": (4, 5),
}

_SEASON_COLUMNS = {
    "temperature_c": ("T2M", "mean"),
    "temp_max_c": ("T2M_MAX", "mean"),
    "temp_min_c": ("T2M_MIN", "mean"),
    "rainfall_mm": ("PRECTOTCORR", "sum"),
    "rh_percent": ("RH2M", "mean"),
    "solar_mj_m2_day": ("ALLSKY_SFC_SW_DWN", "mean"),
}


def _season_window(season: str, season_year: int) -> Tuple[pd.Timestamp, pd.Timestamp]:
    first_month, last_month = SEASON_MONTHS[season]
    start = pd.Timestamp(season_year, first_month, 1)
    end_year = season_year + 1 if last_month < first_month else season_year
    end = pd.Timestamp(end_year, last_month, 1) + pd.offsets.MonthEnd(0)
    return start, end


def _season_label(date_value: pd.Timestamp) -> Tuple[Optional[str], int]:
    """Return (season, season_year) for a date; season is None if uncovered."""

    month = date_value.month
    for season, (first, last) in SEASON_MONTHS.items():
        in_season = (
            first <= month <= last if first <= last
            else month >= first or month <= last
        )
        if in_season:
            year = date_value.year - 1 if (first > last and month <= last) else date_value.year
            return season, year
    return None, date_value.year


def summarise_seasons(daily: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate daily NASA POWER data into per-location seasonal summaries.

    Input columns: date, location, T2M, T2M_MAX, T2M_MIN, PRECTOTCORR,
    RH2M, ALLSKY_SFC_SW_DWN.

    Output: one row per location/season/season_year with
    start_date, end_date (full season window), days_available,
    days_expected, complete, temperature_c, temp_max_c, temp_min_c (means),
    rainfall_mm (seasonal TOTAL, not mean), rh_percent, solar_mj_m2_day.
    Seasons with no data are omitted; partial seasons have complete=False.
    """

    required = {"date", "location"} | {v[0] for v in _SEASON_COLUMNS.values()}
    missing = required - set(daily.columns)
    if missing:
        raise ValueError(f"Missing columns for seasonal summary: {sorted(missing)}")

    data = daily.copy()
    data["date"] = pd.to_datetime(data["date"])
    labels = data["date"].apply(_season_label)
    data["season"] = [label[0] for label in labels]
    data["season_year"] = [label[1] for label in labels]
    data = data[data["season"].notna()]

    rows = []
    for (location, season, season_year), group in data.groupby(
        ["location", "season", "season_year"], sort=True
    ):
        start, end = _season_window(season, int(season_year))
        expected = (end - start).days + 1
        available = group["date"].nunique()

        row = {
            "location": location,
            "season": season,
            "season_year": int(season_year),
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "days_available": int(available),
            "days_expected": int(expected),
            "complete": bool(available == expected),
        }
        for column, (source, how) in _SEASON_COLUMNS.items():
            series = group[source]
            value = series.sum(min_count=1) if how == "sum" else series.mean()
            row[column] = None if pd.isna(value) else round(float(value), 2)
        rows.append(row)

    return pd.DataFrame(rows)


def build_rotation_conditions(
    seasonal_summary: pd.DataFrame,
    location: str,
    seasons: List[str],
    season_year: Optional[int] = None,
    require_complete: bool = True,
) -> List[Dict]:
    """
    Build the `seasonal_conditions` list that
    modules.rotation_engine.generate_crop_rotations() expects.

    For each requested season the values are averaged over the available
    seasons for that location (complete ones only when require_complete is
    True). Pass season_year to use one specific year instead.
    Raises ValueError if the location or a season has no usable data.
    """

    location_rows = seasonal_summary[seasonal_summary["location"] == location]
    if location_rows.empty:
        raise ValueError(f"No seasonal data for location '{location}'.")

    conditions = []
    for season in seasons:
        rows = location_rows[location_rows["season"] == season]
        if season_year is not None:
            rows = rows[rows["season_year"] == season_year]
        if require_complete:
            rows = rows[rows["complete"]]
        if rows.empty:
            raise ValueError(
                f"No {'complete ' if require_complete else ''}data for "
                f"{location} / {season}"
                + (f" / {season_year}" if season_year is not None else "")
                + "."
            )

        years = [int(y) for y in rows["season_year"]]
        conditions.append({
            "season": season,
            "environmental_data": {
                "temperature_c": round(float(rows["temperature_c"].mean()), 2),
                "rainfall_mm": round(float(rows["rainfall_mm"].mean()), 2),
                "data_source": "NASA POWER daily data (seasonal aggregate)",
                "season_years_used": years,
                "rainfall_basis": "seasonal total (mm), not daily",
                "includes_incomplete_seasons": bool(not rows["complete"].all()),
            },
        })

    return conditions
