"""Soil and water vocabulary shared by the KAIRO form and the scoring engines.

The soil ids match the ``soil_types`` column of ``data/crop_database.csv``
exactly, so a farmer's choice can always be matched against crop records.
"""

from __future__ import annotations

from typing import Optional

# (database id, farmer-facing label)
SOIL_TYPES = [
    ("red-soil", "Red soil"),
    ("black-soil", "Black soil (regur)"),
    ("alluvial", "Alluvial soil"),
    ("sandy", "Sandy soil"),
    ("sandy-loam", "Sandy loam"),
    ("loam", "Loam"),
    ("loamy", "Loamy soil"),
    ("clay-loam", "Clay loam"),
    ("silty-loam", "Silty loam"),
]

SOIL_LABELS = {soil_id: label for soil_id, label in SOIL_TYPES}
_LABEL_TO_ID = {label.lower(): soil_id for soil_id, label in SOIL_TYPES}

# Options a farmer can pick for water. Everything except rainfed means the
# farm has some irrigation source.
WATER_SOURCES = ["Rainfed", "Canal", "Borewell", "Drip irrigation", "Other irrigation"]


def soil_id_from_label(value: Optional[str]) -> Optional[str]:
    """Return the database soil id for a label or id, or None if unknown.

    ``None`` is returned for "Not sure" or anything unrecognised, so the
    scoring engine excludes the soil component instead of guessing.
    """
    if not value:
        return None
    text = str(value).strip().lower()
    if text in SOIL_LABELS:
        return text
    return _LABEL_TO_ID.get(text)


def water_availability_from_source(value: Optional[str]) -> Optional[str]:
    """Map a water-source choice to the database category.

    Returns ``"rainfed"`` or ``"irrigated"``; ``None`` if nothing was chosen.
    """
    if not value:
        return None
    return "rainfed" if str(value).strip().lower() == "rainfed" else "irrigated"
