
"""
Kyro - Crop Suitability Engine V2

Member 3: Crop Intelligence & Rotation Developer

Purpose:
    Evaluate crop suitability using environmental conditions
    and farm-level information.

Important:
    This is a transparent, rule-based prototype.
    Scores are heuristic and are not validated agronomic predictions.
"""

from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------
# 1. SCORING WEIGHTS
# ---------------------------------------------------------

WEIGHTS = {
    "temperature": 25,
    "rainfall": 25,
    "soil": 20,
    "water": 15,
    "season": 15,
}


# ---------------------------------------------------------
# 2. INPUT VALIDATION AND NORMALIZATION
# ---------------------------------------------------------

def _normalise(value: Any) -> str:
    """Normalize text for consistent comparisons."""

    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
        .replace("_", "-")
    )


def _number(value: Any, field_name: str) -> float | None:
    """Convert a value into a finite number."""

    if value is None or isinstance(value, bool):
        return None

    if str(value).strip() == "":
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid numeric value for {field_name}: {value}"
        )

    if not math.isfinite(number):
        raise ValueError(
            f"{field_name} must be a finite number."
        )

    return number


def _to_list(value: Any) -> list[str]:
    """Convert CSV-style pipe-separated values into a list."""

    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [
            _normalise(item)
            for item in value
            if _normalise(item)
        ]

    return [
        _normalise(item)
        for item in str(value).split("|")
        if _normalise(item)
    ]


# ---------------------------------------------------------
# 3. TEMPERATURE AND RAINFALL SCORING
# ---------------------------------------------------------

def _range_score(
    value: Any,
    minimum: Any,
    maximum: Any,
    field_name: str,
) -> float | None:
    """
    Score a value against an acceptable range.

    100 = inside the range.
    Below 100 = outside the range.

    Outside-range scoring is an illustrative heuristic,
    not a validated crop response model.
    """

    actual = _number(value, field_name)
    lower = _number(minimum, f"{field_name} minimum")
    upper = _number(maximum, f"{field_name} maximum")

    if actual is None or lower is None or upper is None:
        return None

    if lower > upper:
        raise ValueError(
            f"Minimum cannot exceed maximum for {field_name}."
        )

    if lower <= actual <= upper:
        return 100.0

    distance = (
        lower - actual
        if actual < lower
        else actual - upper
    )

    reference_width = upper - lower

    if reference_width == 0:
        return 0.0

    score = 100 * (
        1 - distance / reference_width
    )

    return round(max(0.0, min(100.0, score)), 2)


# ---------------------------------------------------------
# 4. INDIVIDUAL COMPONENT SCORING
# ---------------------------------------------------------

def _soil_score(
    farm_soil: Any,
    crop_soils: Any,
) -> float | None:
    """Check whether the farm soil matches crop soil preferences."""

    if not farm_soil:
        return None

    suitable_soils = _to_list(crop_soils)

    if not suitable_soils:
        return None

    return (
        100.0
        if _normalise(farm_soil) in suitable_soils
        else 0.0
    )


def _water_score(
    water_availability: Any,
    crop_water_requirement: Any,
) -> float | None:
    """Compare farm water availability with crop requirements."""

    if not water_availability or not crop_water_requirement:
        return None

    farm = _normalise(water_availability)
    crop_need = _normalise(crop_water_requirement)

    if farm == crop_need:
        return 100.0

    # A farm with irrigation can still grow a crop that only needs rain.
    # The reverse (rainfed farm, crop that needs irrigation) is a mismatch.
    if farm == "irrigated" and crop_need == "rainfed":
        return 100.0

    return 0.0


def _season_score(
    farm_season: Any,
    suitable_seasons: Any,
) -> float | None:
    """Check whether the crop is suitable for the selected season."""

    if not farm_season:
        return None

    seasons = _to_list(suitable_seasons)

    if not seasons:
        return None

    return (
        100.0
        if _normalise(farm_season) in seasons
        else 0.0
    )


# ---------------------------------------------------------
# 5. MAIN CROP SUITABILITY ENGINE
# ---------------------------------------------------------

def calculate_crop_suitability_v2(
    crop: dict,
    environmental_data: dict,
    farm_profile: dict,
    minimum_data_coverage: float = 60,
) -> dict:
    """
    Calculate the suitability of one crop.

    Expected environmental_data:
        temperature_c
        rainfall_mm

    Expected farm_profile:
        soil_type
        water_availability
        season

    Crop fields come from data/crop_database.csv.
    """

    if not isinstance(crop, dict):
        raise TypeError("crop must be a dictionary.")

    if not isinstance(environmental_data, dict):
        raise TypeError(
            "environmental_data must be a dictionary."
        )

    if not isinstance(farm_profile, dict):
        raise TypeError(
            "farm_profile must be a dictionary."
        )

    if not 0 <= minimum_data_coverage <= 100:
        raise ValueError(
            "minimum_data_coverage must be between 0 and 100."
        )

    # Temperature score
    temperature_score = _range_score(
        environmental_data.get("temperature_c"),
        crop.get("min_temperature_c"),
        crop.get("max_temperature_c"),
        "temperature_c",
    )

    # Rainfall score
    rainfall_score = _range_score(
        environmental_data.get("rainfall_mm"),
        crop.get("min_rainfall_mm"),
        crop.get("max_rainfall_mm"),
        "rainfall_mm",
    )

    # Soil score
    soil_score = _soil_score(
        farm_profile.get("soil_type"),
        crop.get("soil_types"),
    )

    # Water score
    water_score = _water_score(
        farm_profile.get("water_availability"),
        crop.get("water_requirement"),
    )

    # Season score
    season_score = _season_score(
        farm_profile.get("season"),
        crop.get("suitable_seasons"),
    )

    component_scores = {
        "temperature": temperature_score,
        "rainfall": rainfall_score,
        "soil": soil_score,
        "water": water_score,
        "season": season_score,
    }

    # -----------------------------------------------------
    # 6. MISSING DATA AND DATA COVERAGE
    # -----------------------------------------------------

    missing_data = [
        component
        for component, score in component_scores.items()
        if score is None
    ]

    available_weight = sum(
        WEIGHTS[component]
        for component, score in component_scores.items()
        if score is not None
    )

    data_coverage = round(available_weight, 2)

    # -----------------------------------------------------
    # 7. WEIGHTED SUITABILITY SCORE
    # -----------------------------------------------------

    if available_weight == 0:
        overall_score = None
    else:
        weighted_total = sum(
            score * WEIGHTS[component]
            for component, score in component_scores.items()
            if score is not None
        )

        overall_score = round(
            weighted_total / available_weight,
            2,
        )

    eligible_for_ranking = (
        overall_score is not None
        and data_coverage >= minimum_data_coverage
    )

    # -----------------------------------------------------
    # 8. EXPLANATIONS
    # -----------------------------------------------------

    explanations = []

    for component, score in component_scores.items():

        if score is None:
            explanations.append(
                f"{component.title()} assessment unavailable "
                f"because required data is missing."
            )

        elif score == 100:
            explanations.append(
                f"{component.title()} conditions match "
                f"the crop requirements."
            )

        elif score == 0:
            explanations.append(
                f"{component.title()} conditions do not match "
                f"the crop requirements."
            )

        else:
            explanations.append(
                f"{component.title()} received a partial score "
                f"of {score}."
            )

    if not eligible_for_ranking:
        explanations.append(
            "Insufficient data coverage for reliable ranking."
        )

    # -----------------------------------------------------
    # 9. SOURCE VERIFICATION
    # -----------------------------------------------------

    source_notes = str(crop.get("source_notes") or "")

    needs_verification = (
        "FLAGGED" in source_notes.upper()
        or "NEEDS VERIFICATION" in source_notes.upper()
    )

    source_warnings = (
        [source_notes]
        if needs_verification
        else []
    )

    # -----------------------------------------------------
    # 10. FINAL RESULT
    # -----------------------------------------------------

    result = {
        "crop_id": crop.get("crop_id"),
        "crop_name": crop.get("crop_name"),

        # Source and provenance metadata
        "source_name": crop.get("source_name"),
        "source_urls": crop.get("source_urls"),
        "source_accessed_date": crop.get("source_accessed_date"),
        "source_notes": source_notes,

        "source_verification": (
            "needs_verification"
            if needs_verification
            else "no_explicit_flag"
        ),

        "source_warnings": source_warnings,

        # Suitability assessment
        "overall_score": overall_score,

        "data_coverage_percent": data_coverage,

        "component_scores": component_scores,

        "explanations": explanations,

        "missing_data": missing_data,

        "eligible_for_ranking": eligible_for_ranking,

        "assessment_status": (
            "completed"
            if eligible_for_ranking
            else "insufficient_data"
        ),

        "score_type": "heuristic_rule_based",

        "limitations": [
            "Scores are based on rule-based heuristics.",
            "Exact soil matching does not represent complete soil science.",
            "Water availability matching is simplified.",
            "Temperature and rainfall ranges require local validation.",
            "This score is not a guaranteed crop yield prediction.",
        ],
    }

    return result


# ---------------------------------------------------------
# 11. RANK MULTIPLE CROPS
# ---------------------------------------------------------

def rank_crops_v2(
    crops: list[dict],
    environmental_data: dict,
    farm_profile: dict,
    minimum_data_coverage: float = 60,
) -> list[dict]:
    """
    Evaluate multiple crops and rank them.

    Eligible crops appear first, sorted by score.
    Crops with insufficient data appear afterward.
    """

    results = []

    for crop in crops:

        result = calculate_crop_suitability_v2(
            crop=crop,
            environmental_data=environmental_data,
            farm_profile=farm_profile,
            minimum_data_coverage=minimum_data_coverage,
        )

        results.append(result)

    results.sort(
        key=lambda item: (
            item["eligible_for_ranking"],
            item["overall_score"]
            if item["overall_score"] is not None
            else -1,
        ),
        reverse=True,
    )

    return results
