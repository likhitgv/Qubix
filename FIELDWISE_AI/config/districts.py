"""District and region configuration for KAIRO.

Coordinates are representative points for each district (district HQ area),
NOT claims that every farm in the district shares the same climate or soil.
"""

import csv
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

DISTRICTS = [
    {"name": "Ballari", "latitude": 15.1394, "longitude": 76.9214, "state": "Karnataka"},
    {"name": "Shivamogga", "latitude": 13.9326, "longitude": 75.5750, "state": "Karnataka"},
    {"name": "Vijayapura", "latitude": 16.8275, "longitude": 75.7253, "state": "Karnataka"},
    {"name": "Belagavi", "latitude": 15.8521, "longitude": 74.5045, "state": "Karnataka"},
    {"name": "Dharwad", "latitude": 15.4589, "longitude": 75.0078, "state": "Karnataka"},
]


def get_district(name: str) -> dict:
    """Return the district dict for a name (case-insensitive)."""
    for district in DISTRICTS:
        if district["name"].lower() == name.strip().lower():
            return district
    raise KeyError(
        f"Unknown district '{name}'. Available: {[d['name'] for d in DISTRICTS]}"
    )


def get_locations() -> Dict[str, Tuple[float, float]]:
    """Return {name: (latitude, longitude)} for use with fetch_for_locations()."""
    return {d["name"]: (d["latitude"], d["longitude"]) for d in DISTRICTS}


# ----------------------------------------------------------------------------
# All-India state -> district list (Census 2011 boundaries; see
# examples/build_india_districts.py). Centres are polygon centroids used only to
# look up the nearest NASA grid cell. The five districts above keep their own
# verified coordinates and are the only ones KAIRO's crop data was validated for.
# ----------------------------------------------------------------------------
INDIA_DISTRICTS_PATH = Path(__file__).resolve().parent / "india_districts.csv"


@lru_cache(maxsize=1)
def _load_india_districts() -> Tuple[dict, ...]:
    if not INDIA_DISTRICTS_PATH.is_file():
        # Degrade gracefully: only the five validated districts are available.
        return tuple(
            {"state": d["state"], "district": d["name"], "latitude": d["latitude"], "longitude": d["longitude"]}
            for d in DISTRICTS
        )
    with INDIA_DISTRICTS_PATH.open("r", encoding="utf-8", newline="") as handle:
        rows = [
            {
                "state": r["state"],
                "district": r["district"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
            }
            for r in csv.DictReader(handle)
        ]
    return tuple(rows)


def list_states() -> List[str]:
    """All states / union territories that have districts, alphabetically."""
    return sorted({r["state"] for r in _load_india_districts()})


def districts_in_state(state: str) -> List[dict]:
    """Districts of a state, alphabetically. Raises KeyError for an unknown state."""
    rows = sorted((r for r in _load_india_districts() if r["state"] == state), key=lambda r: r["district"])
    if not rows:
        raise KeyError(f"Unknown state '{state}'.")
    return [get_india_district(state, r["district"]) for r in rows]


def is_validated(state: str, district: str) -> bool:
    return any(d["state"] == state and d["name"] == district for d in DISTRICTS)


def get_india_district(state: str, district: str) -> dict:
    """One district with coordinates, a display label and whether it is validated.

    Validated districts use their verified coordinates, not the polygon centroid.
    """
    row = next(
        (r for r in _load_india_districts() if r["state"] == state and r["district"] == district), None
    )
    if row is None:
        raise KeyError(f"Unknown district '{district}' in '{state}'.")
    validated = is_validated(state, district)
    lat, lon = row["latitude"], row["longitude"]
    if validated:
        known = get_district(district)
        lat, lon = known["latitude"], known["longitude"]
    return {
        "state": state,
        "district": district,
        "latitude": lat,
        "longitude": lon,
        "validated": validated,
        "label": district if validated else f"{district}, {state}",
    }
