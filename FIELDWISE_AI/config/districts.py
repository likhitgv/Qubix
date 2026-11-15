"""District and region configuration for KAIRO.

Coordinates are representative points for each district (district HQ area),
NOT claims that every farm in the district shares the same climate or soil.
"""

from typing import Dict, Tuple

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
