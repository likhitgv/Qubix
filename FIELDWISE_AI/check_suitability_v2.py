
"""FIELDWISE AI - M5 Crop Suitability Engine V2.

Transparent prototype scoring with gradual range penalties,
input validation, data coverage and explainable results.

This is a decision-support screening tool, not an agronomic model.
"""

from __future__ import annotations

import math
from typing import Any


WEIGHTS = {
    "temperature": 25,
    "rainfall": 25,
    "soil": 20,
    "water": 15,
    "season": 15,
}


def _normalise(value: Any) -> str:
    """Normalize spelling and whitespace, without fuzzy matching."""
    return " ".join(
        str(value).strip().lower().replace("_", "-").split()
    )


def _number(value: Any, field_name: str) -> float:
    """Convert a value into a finite number."""
    if value is None or isinstance(value, bool):
        raise ValueError(f"{field_name} must be a valid number.")

    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{field_name} must be numeric."
        ) from error

    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite.")

    return number


def _range_score(
    value: Any,
    minimum: Any,
    maximum: Any,
    field_name: str,
) -> tuple[float, str]:
    """Score range compatibility using a gradual outside-range penalty.

    Inside the reference range: 100.
    Outside: score decreases linearly with distance.
    One full reference-range width outside: 0.

    This formula is an illustrative prototype heuristic.
    It is not a validated crop-response function.
    """

    number = _number(value, field_name)
    lower = _number(minimum, f"{field_name} minimum")
    upper = _number(maximum, f"{field_name} maximum")

    if lower > upper:
        raise ValueError(
            f"{field_name} minimum cannot exceed maximum."
        )

    if lower <= number <= upper:
        return 100.0, (
            f"{number} is within the reference range "
            f"({lower} to {upper})."
        )

    distance = lower - number if number < lower else number - upper
    reference_width = upper - lower

    if reference_width == 0:
        score = 0.0
    else:
        score = max(
            0.0,
            100.0 * (1.0 - distance / reference_width),
        )

    return round(score, 2), (
        f"{number} is outside the reference range "
        f"({lower} to {upper}); distance-based prototype "
        f"score is {round(score, 2)}."
    )


def calculate_crop_suitability_v2(
    crop: dict[str, Any],
    environmental_data: dict[str, Any],
    farm_profile: dict[str, Any],
    minimum_data_coverage: float = 60,
) -> dict[str, Any]:
    """Calculate crop suitability using V2 scoring."""

    threshold = _number(
        minimum_data_coverage,
        "minimum_data_coverage",
    )

    if not 0 <= threshold <= 100:
        raise ValueError(
            "minimum_data_coverage must be between 0 and 100."
        )

    component_scores: dict[str, float] = {}
    explanations: dict[str, str] = {}
    missing_data: list[str] = []

    # 1. Temperature
    temperature = environmental_data.get("temperature_c")

    if temperature is not None:
        score, reason = _range_score(
            temperature,
            crop["min_temperature_c"],
            crop["max_temperature_c"],
            "temperature_c",
        )
        component_scores["temperature"] = score
        explanations["temperature"] = reason
    else:
        missing_data.append("temperature_c")

    # 2. Rainfall
    rainfall = environmental_data.get("rainfall_mm")

    if rainfall is not None:
        score, reason = _range_score(
            rainfall,
            crop["min_rainfall_mm"],
            crop["max_rainfall_mm"],
            "rainfall_mm",
        )
        component_scores["rainfall"] = score
        explanations["rainfall"] = reason
    else:
        missing_data.append("rainfall_mm")

    # 3. Soil: normalized exact reference match only
    soil_type = farm_profile.get("soil_type")

    if soil_type:
        accepted_soils = {
            _normalise(item)
            for item in crop["soil_types"]
        }

        selected_soil = _normalise(soil_type)

        soil_score = (
            100.0 if selected_soil in accepted_soils else 0.0
        )

        component_scores["soil"] = soil_score

        explanations["soil"] = (
            "Exact normalized soil-category match."
            if soil_score == 100
            else (
                "Soil category is not listed in the crop "
                "reference data. Compatibility is unverified."
            )
        )
    else:
        missing_data.append("soil_type")

    # 4. Water: exact category comparison
    water_availability = farm_profile.get("water_availability")

    if water_availability:
        crop_water = _normalise(crop["water_requirement"])
        farm_water = _normalise(water_availability)

        water_score = (
            100.0 if crop_water == farm_water else 0.0
        )

        component_scores["water"] = water_score

        explanations["water"] = (
            "Water categories match."
            if water_score == 100
            else (
                "Water categories do not match. "
                "Actual water compatibility requires agronomic review."
            )
        )
    else:
        missing_data.append("water_availability")

    # 5. Season
    season = farm_profile.get("season")

    if season:
        accepted_seasons = {
            _normalise(item)
            for item in crop["suitable_seasons"]
        }

        selected_season = _normalise(season)

        season_score = (
            100.0 if selected_season in accepted_seasons else 0.0
        )

        component_scores["season"] = season_score

        explanations["season"] = (
            "Season matches the crop reference."
            if season_score == 100
            else "Season is not listed in the crop reference."
        )
    else:
        missing_data.append("season")

    # Weighted score using only available components
    available_weight = sum(
        WEIGHTS[name] for name in component_scores
    )

    if available_weight:
        weighted_total = sum(
            component_scores[name] * WEIGHTS[name]
            for name in component_scores
        )

        overall_score = round(
            weighted_total / available_weight, 2
        )
    else:
        overall_score = None

    coverage = available_weight

    sufficient_data = coverage >= threshold and overall_score is not None

    return {
        "crop_id": crop["crop_id"],
        "crop_name": crop["crop_name"],
        "overall_score": overall_score,
        "data_coverage_percent": coverage,
        "component_scores": component_scores,
        "explanations": explanations,
        "missing_data": missing_data,
        "eligible_for_ranking": sufficient_data,
        "assessment_status": (
            "screening_result_requires_local_validation"
            if sufficient_data
            else "insufficient_data"
        ),
        "score_type": "rule_based_prototype_v2",
        "limitations": [
            "Weights are prototype choices, not scientifically calibrated.",
            "Outside-range penalties are illustrative heuristics.",
            "Soil compatibility uses exact reference matching.",
            "Water compatibility requires local verification.",
            "A high score does not guarantee crop success or yield.",
        ],
    }


def rank_crops_v2(
    crops: list[dict[str, Any]],
    environmental_data: dict[str, Any],
    farm_profile: dict[str, Any],
    minimum_data_coverage: float = 60,
) -> list[dict[str, Any]]:
    """Rank crops, placing sufficiently covered assessments first."""

    results = [
        calculate_crop_suitability_v2(
            crop,
            environmental_data,
            farm_profile,
            minimum_data_coverage,
        )
        for crop in crops
    ]

    return sorted(
        results,
        key=lambda item: (
            item["eligible_for_ranking"],
            item["overall_score"] or 0,
        ),
        reverse=True,
    )
