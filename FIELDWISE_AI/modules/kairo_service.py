"""KAIRO service layer: one place that turns a farm profile into a plan.

The UI calls these functions and only displays what they return. All data
comes from NASA POWER files (or a live NASA POWER fetch); nothing is invented.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from config.districts import DISTRICTS
from modules.crop_database import load_crop_database
from modules.nasa_api import (
    NASAPowerError,
    build_rotation_conditions,
    fetch_for_district,
    summarise_seasons,
    to_climate_dataframe,
)
from modules.rotation_engine import generate_crop_rotations
from modules.sustainability import compare_rotations

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "nasa_power"
GRID_POINTS_PATH = Path(__file__).resolve().parents[1] / "data" / "india_grid_points.csv"
GRID_SUMMARY_PATH = Path(__file__).resolve().parents[1] / "data" / "india_grid_seasonal_summary.csv"
SEASONS = ["kharif", "rabi"]

DATA_NATURE = (
    "NASA POWER is a gridded, modelled product (satellite + reanalysis, ~50 km "
    "cells), not a field or weather-station measurement."
)
DISCLAIMER = (
    "KAIRO is decision support, not agronomic advice. Confirm choices with a "
    "local agronomist and a soil test."
)

# Farm points farther than this from every district centre are outside the
# five Karnataka districts KAIRO has data for.
MAX_DISTRICT_DISTANCE_KM = 150.0

# The nationwide NASA grid is ~56 km apart, so a point inside India is at most ~40 km
# from a grid point. Farther than this and the location is outside the downloaded area.
MAX_GRID_DISTANCE_KM = 80.0

OUTSIDE_KARNATAKA_NOTE = (
    "This location is outside the five Karnataka districts KAIRO's crop reference data was "
    "assembled for. Treat the crop ranking as indicative and confirm with local experts."
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_district(latitude: float, longitude: float) -> dict[str, Any]:
    """Find the closest supported district to a geotagged farm location."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Latitude must be -90..90 and longitude -180..180.")
    best = min(
        DISTRICTS,
        key=lambda d: haversine_km(latitude, longitude, d["latitude"], d["longitude"]),
    )
    distance = haversine_km(latitude, longitude, best["latitude"], best["longitude"])
    return {
        "district": best["name"],
        "distance_km": round(distance, 1),
        "within_coverage": distance <= MAX_DISTRICT_DISTANCE_KM,
        "note": (
            "Climate values come from the nearest district centre, not from "
            "the exact farm point."
        ),
    }


def load_provenance(district: str) -> dict[str, Any]:
    """Return recorded source/coverage details for a district's stored NASA data.

    Reads provenance_seasonal.json (written when the data was fetched). Missing
    file or district yields an empty dict so the UI can say "not recorded".
    """
    path = DATA_DIR / "provenance_seasonal.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get(district, {})


def load_seasonal_summary(path: Optional[Path] = None) -> pd.DataFrame:
    path = Path(path) if path else DATA_DIR / "seasonal_summary.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Seasonal summary not found: {path}")
    return pd.read_csv(path)


def load_grid_points(path: Optional[Path] = None) -> pd.DataFrame:
    path = Path(path) if path else GRID_POINTS_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"Grid points not found: {path}. Build them with: py -3.11 -m examples.build_india_seasonal_summary"
        )
    return pd.read_csv(path)


def load_grid_summary(path: Optional[Path] = None) -> pd.DataFrame:
    path = Path(path) if path else GRID_SUMMARY_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"Grid seasonal summary not found: {path}. Build it with: py -3.11 -m examples.build_india_seasonal_summary"
        )
    return pd.read_csv(path)


def nearest_grid_point(
    latitude: float, longitude: float, points: Optional[pd.DataFrame] = None
) -> dict[str, Any]:
    """Find the closest downloaded NASA grid point (all-India coverage) to a location."""
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Latitude must be -90..90 and longitude -180..180.")
    pts = points if points is not None else load_grid_points()
    distances = pts.apply(
        lambda r: haversine_km(latitude, longitude, float(r["latitude"]), float(r["longitude"])), axis=1
    )
    idx = distances.idxmin()
    row = pts.loc[idx]
    km = float(distances.loc[idx])
    return {
        "grid_id": str(row["grid_id"]),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "distance_km": round(km, 1),
        "within_coverage": km <= MAX_GRID_DISTANCE_KM,
        "note": (
            "Climate values come from the nearest NASA grid cell (about 56 km across), "
            "not from the exact farm point."
        ),
    }


def fetch_live_seasonal_summary(
    district: str, start: str = "2024-01-01", end: str = "2025-12-31"
) -> pd.DataFrame:
    """Fetch NASA POWER daily data for a district and summarise by season.

    Raises ``NASAPowerError`` if NASA cannot be reached.
    """
    result = fetch_for_district(district, start, end)
    daily = to_climate_dataframe(result, district)
    return summarise_seasons(daily)


def build_plan(
    profile: dict[str, Any],
    seasonal_summary: Optional[pd.DataFrame] = None,
    top_n: int = 3,
) -> dict[str, Any]:
    """Build seasonal conditions, ranked rotations and sustainability output.

    profile keys: district (display label) and/or grid_id (all-India NASA grid cell), soil_type (db id or None), water_availability
    ("rainfed"/"irrigated"/None), previous_crops (free text, optional).
    """
    grid_id = profile.get("grid_id")
    district = profile.get("district")
    if not district and not grid_id:
        raise ValueError("A district or a grid location is required.")
    label = district or grid_id
    location_key = grid_id or district
    if seasonal_summary is not None:
        summary = seasonal_summary
    else:
        summary = load_grid_summary() if grid_id else load_seasonal_summary()

    try:
        conditions = build_rotation_conditions(summary, location_key, SEASONS)
    except ValueError as error:
        raise ValueError(f"No complete NASA season data for {label}: {error}") from error

    crops = load_crop_database()
    farm = {
        "soil_type": profile.get("soil_type"),
        "water_availability": profile.get("water_availability"),
    }
    rotations = generate_crop_rotations(crops, conditions, farm, top_n=top_n)
    sustainability = compare_rotations(rotations, crops, profile.get("previous_crops"))

    warnings = _plan_warnings(farm, rotations)
    lat, lon = profile.get("latitude"), profile.get("longitude")
    if grid_id and lat is not None and lon is not None and not nearest_district(lat, lon)["within_coverage"]:
        warnings.append(OUTSIDE_KARNATAKA_NOTE)

    return {
        "district": label,
        "grid_id": grid_id,
        "conditions": conditions,
        "rotations": rotations,
        "sustainability": sustainability,
        "profile_used": farm,
        "data_nature": DATA_NATURE,
        "disclaimer": DISCLAIMER,
        "warnings": warnings,
    }


def _plan_warnings(farm: dict, rotations: list[dict]) -> list[str]:
    notes = []
    if not farm.get("soil_type"):
        notes.append("Soil type not given: soil was excluded from scoring.")
    if not farm.get("water_availability"):
        notes.append("Water source not given: water was excluded from scoring.")
    if not rotations:
        notes.append("No rotation met the minimum data and suitability requirements.")
    return notes
