"""Kyro service layer: one place that turns a farm profile into a plan.

The UI calls these functions and only displays what they return. All data
comes from NASA POWER files (or a live NASA POWER fetch); nothing is invented.
"""

from __future__ import annotations

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
SEASONS = ["kharif", "rabi"]

DATA_NATURE = (
    "NASA POWER is a gridded, modelled product (satellite + reanalysis, ~50 km "
    "cells), not a field or weather-station measurement."
)
DISCLAIMER = (
    "Kyro is decision support, not agronomic advice. Confirm choices with a "
    "local agronomist and a soil test."
)

# Farm points farther than this from every district centre are outside the
# five Karnataka districts Kyro has data for.
MAX_DISTRICT_DISTANCE_KM = 150.0


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


def load_seasonal_summary(path: Optional[Path] = None) -> pd.DataFrame:
    path = Path(path) if path else DATA_DIR / "seasonal_summary.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Seasonal summary not found: {path}")
    return pd.read_csv(path)


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

    profile keys: district, soil_type (db id or None), water_availability
    ("rainfed"/"irrigated"/None), previous_crops (free text, optional).
    """
    district = profile.get("district")
    if not district:
        raise ValueError("A district is required.")
    summary = seasonal_summary if seasonal_summary is not None else load_seasonal_summary()

    try:
        conditions = build_rotation_conditions(summary, district, SEASONS)
    except ValueError as error:
        raise ValueError(f"No complete NASA season data for {district}: {error}") from error

    crops = load_crop_database()
    farm = {
        "soil_type": profile.get("soil_type"),
        "water_availability": profile.get("water_availability"),
    }
    rotations = generate_crop_rotations(crops, conditions, farm, top_n=top_n)
    sustainability = compare_rotations(rotations, crops, profile.get("previous_crops"))

    return {
        "district": district,
        "conditions": conditions,
        "rotations": rotations,
        "sustainability": sustainability,
        "profile_used": farm,
        "data_nature": DATA_NATURE,
        "disclaimer": DISCLAIMER,
        "warnings": _plan_warnings(farm, rotations),
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
