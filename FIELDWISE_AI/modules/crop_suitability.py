"""KAIRO - M5 Crop Suitability Engine.

Uses transparent rule-based scoring against the crop reference database.
Environmental values and farmer inputs must be supplied by the caller.
"""

from __future__ import annotations

from typing import Any


# Component weights. These are prototype design choices, not
# scientifically calibrated agronomic weights.
WEIGHTS = {
    "temperature": 25,
    "rainfall": 25,
    "soil": 20,
    "water": 15,
    "season": 15,
}


def _normalise(value: Any) -> str:
    """Normalize categorical values for comparison."""
    return str(value).strip().lower().replace("_", "-")


def _range_score(
    value: Any,
    minimum: Any,
    maximum: Any,
) -> tuple[int, str]:
    """Score a numeric value against an inclusive reference range.

    This first prototype uses binary range matching:
    100 when inside the range, 0 when outside.
    """
    if value is None:
        raise ValueError("A range value cannot be missing.")

    number = float(value)
    lower = float(minimum)
    upper = float(maximum)

    if lower > upper:
        raise ValueError("Minimum cannot exceed maximum.")

    if lower <= number <= upper:
        return 100, f"{number} is within the reference range ({lower}-{upper})."

    return 0, f"{number} is outside the reference range ({lower}-{upper})."


def calculate_crop_suitability(
    crop: dict[str, Any],
    environmental_data: dict[str, Any],
    farm_profile: dict[str, Any],
) -> dict[str, Any]:
    """Calculate a transparent suitability score for one crop.

    Expected environmental_data:
        temperature_c: average temperature in Celsius
        rainfall_mm: rainfall in mm for the relevant period

    Expected farm_profile:
        soil_type: farmer-reported soil type
        water_availability: water category
        season: growing season

    Missing components are excluded and remaining weights are
    normalized. The data coverage percentage shows how much of
    the original scoring weight was actually evaluated.
    """

    component_scores: dict[str, int] = {}
    explanations: dict[str, str] = {}
    missing_data: list[str] = []

    # 1. Temperature compatibility
    temperature = environmental_data.get("temperature_c")

    if temperature is not None:
        score, reason = _range_score(
            temperature,
            crop["min_temperature_c"],
            crop["max_temperature_c"],
        )
        component_scores["temperature"] = score
        explanations["temperature"] = reason
    else:
        missing_data.append("temperature_c")

    # 2. Rainfall compatibility
    rainfall = environmental_data.get("rainfall_mm")

    if rainfall is not None:
        score, reason = _range_score(
            rainfall,
            crop["min_rainfall_mm"],
            crop["max_rainfall_mm"],
        )
        component_scores["rainfall"] = score
        explanations["rainfall"] = reason
    else:
        missing_data.append("rainfall_mm")

    # 3. Soil compatibility
    soil_type = farm_profile.get("soil_type")

    if soil_type:
        accepted_soils = {
            _normalise(item) for item in crop["soil_types"]
        }
        selected_soil = _normalise(soil_type)

        soil_score = 100 if selected_soil in accepted_soils else 0

        component_scores["soil"] = soil_score
        explanations["soil"] = (
            f"{soil_type} matches the crop reference soil types."
            if soil_score == 100
            else f"{soil_type} is not listed in the crop reference soil types."
        )
    else:
        missing_data.append("soil_type")

    # 4. Water compatibility
    water_availability = farm_profile.get("water_availability")

    if water_availability:
        crop_water = _normalise(crop["water_requirement"])
        farm_water = _normalise(water_availability)

        water_score = 100 if crop_water == farm_water else 0

        component_scores["water"] = water_score
        explanations["water"] = (
            "Water categories match exactly."
            if water_score == 100
            else (
                f"Crop reference says '{crop_water}', while the "
                f"farm profile says '{farm_water}'. Compatibility "
                "requires further agronomic verification."
            )
        )
    else:
        missing_data.append("water_availability")

    # 5. Season compatibility
    season = farm_profile.get("season")

    if season:
        accepted_seasons = {
            _normalise(item) for item in crop["suitable_seasons"]
        }
        selected_season = _normalise(season)

        season_score = 100 if selected_season in accepted_seasons else 0

        component_scores["season"] = season_score
        explanations["season"] = (
            f"{season} is listed as a suitable reference season."
            if season_score == 100
            else f"{season} is not listed in the crop reference seasons."
        )
    else:
        missing_data.append("season")

    # Calculate weighted score using available components only.
    available_weight = sum(
        WEIGHTS[name] for name in component_scores
    )

    if available_weight:
        weighted_total = sum(
            component_scores[name] * WEIGHTS[name]
            for name in component_scores
        )

        overall_score = round(weighted_total / available_weight, 2)
    else:
        overall_score = None

    coverage = sum(
        WEIGHTS[name] for name in component_scores
    )

    return {
        "crop_id": crop["crop_id"],
        "crop_name": crop["crop_name"],
        "overall_score": overall_score,
        "data_coverage_percent": coverage,
        "component_scores": component_scores,
        "explanations": explanations,
        "missing_data": missing_data,
        "score_type": "rule_based_prototype",
        "limitations": [
            "Scores use prototype weights, not calibrated agronomic models.",
            "Range compatibility uses binary scoring.",
            "Soil and water compatibility require local verification.",
            "Missing components are excluded from the overall score.",
        ],
    }


def rank_crops(
    crops: list[dict[str, Any]],
    environmental_data: dict[str, Any],
    farm_profile: dict[str, Any],
) -> list[dict[str, Any]]:
    """Calculate and rank all crops from highest to lowest score."""

    results = [
        calculate_crop_suitability(
            crop,
            environmental_data,
            farm_profile,
        )
        for crop in crops
    ]

    return sorted(
        results,
        key=lambda result: (
            result["overall_score"] is not None,
            result["overall_score"] or 0,
        ),
        reverse=True,
    )
