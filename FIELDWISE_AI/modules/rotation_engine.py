
"""
FIELDWISE AI - Crop Rotation Engine

Member 3: Crop Intelligence & Rotation Developer

Features:
    1. Crop suitability evaluation using V2.
    2. Strict seasonal eligibility.
    3. Multi-season rotation generation.
    4. Crop family diversity penalty.
    5. Legume-to-non-legume rotation bonus.
    6. Rotation scoring and ranking.
    7. Crop suitability details and source provenance.
    8. Source verification warnings.

Important:
    This is a transparent, rule-based prototype.
    Rotation scores are heuristic, not scientifically
    validated agronomic predictions.
"""

from __future__ import annotations

from itertools import product
from typing import Any

from modules.crop_suitability_v2 import (
    calculate_crop_suitability_v2,
)


# ---------------------------------------------------------
# 1. ROTATION SETTINGS
# ---------------------------------------------------------

REPEATED_FAMILY_PENALTY = 10
LEGUME_ROTATION_BONUS = 5


# ---------------------------------------------------------
# 2. HELPER FUNCTIONS
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


def _to_list(value: Any) -> list[str]:
    """Convert pipe-separated strings or collections into lists."""

    if value is None:
        return []

    if isinstance(value, str):
        values = value.split("|")
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [value]

    return [
        _normalise(item)
        for item in values
        if _normalise(item)
    ]


def _is_legume(value: Any) -> bool:
    """Convert common CSV boolean values into a boolean."""

    if isinstance(value, bool):
        return value

    return _normalise(value) in {
        "true",
        "1",
        "yes",
        "y",
    }


def _get_crop_family(crop: dict) -> str:
    """Return normalized crop family."""

    return _normalise(crop.get("crop_family"))


# ---------------------------------------------------------
# 3. GET SUITABLE CROPS FOR EACH SEASON
# ---------------------------------------------------------

def _get_season_candidates(
    crops: list[dict],
    seasonal_condition: dict,
    farm_profile: dict,
    minimum_data_coverage: float,
) -> list[dict]:
    """
    Evaluate crops for a particular season.

    A crop must explicitly support the requested season
    before its suitability is calculated.

    Crops with insufficient data coverage or zero
    suitability are excluded.
    """

    season = seasonal_condition.get("season")

    if not season:
        raise ValueError(
            "Each seasonal condition must contain a season."
        )

    requested_season = _normalise(season)

    environmental_data = seasonal_condition.get(
        "environmental_data",
        {},
    )

    if not isinstance(environmental_data, dict):
        raise TypeError(
            "environmental_data must be a dictionary."
        )

    season_farm_profile = dict(farm_profile)
    season_farm_profile["season"] = requested_season

    candidates = []

    for crop in crops:

        # Strict seasonal eligibility check.
        crop_seasons = _to_list(
            crop.get("suitable_seasons")
        )

        if requested_season not in crop_seasons:
            continue

        # Calculate suitability only for season-compatible crops.
        result = calculate_crop_suitability_v2(
            crop=crop,
            environmental_data=environmental_data,
            farm_profile=season_farm_profile,
            minimum_data_coverage=minimum_data_coverage,
        )

        if (
            result["eligible_for_ranking"]
            and result["overall_score"] is not None
            and result["overall_score"] > 0
        ):
            candidates.append({
                "crop": crop,
                "suitability": result,
            })

    candidates.sort(
        key=lambda item: item["suitability"]["overall_score"],
        reverse=True,
    )

    return candidates


# ---------------------------------------------------------
# 4. CALCULATE ROTATION SCORE
# ---------------------------------------------------------

def _score_rotation(
    rotation: list[dict],
) -> dict:
    """
    Calculate the overall rotation score.

    Base score:
        Average crop suitability.

    Adjustments:
        Repeated consecutive crop family: penalty.
        Legume followed by non-legume: bonus.

    Scores are heuristic and require local validation.
    """

    if not rotation:
        raise ValueError(
            "Cannot score an empty rotation."
        )

    # Suitability score is stored directly in each rotation item.
    suitability_scores = [
        item["suitability_score"]
        for item in rotation
    ]

    average_suitability = (
        sum(suitability_scores) / len(suitability_scores)
    )

    family_penalty = 0
    legume_bonus = 0
    explanations = []

    for index in range(1, len(rotation)):

        previous_crop = rotation[index - 1]["crop"]
        current_crop = rotation[index]["crop"]

        previous_family = _get_crop_family(previous_crop)
        current_family = _get_crop_family(current_crop)

        # Penalize consecutive planting from the same family.
        if (
            previous_family
            and current_family
            and previous_family == current_family
        ):
            family_penalty += REPEATED_FAMILY_PENALTY

            explanations.append(
                f"Repeated crop family: "
                f"{previous_crop.get('crop_name')} followed by "
                f"{current_crop.get('crop_name')}."
            )

        # Reward a legume followed by a non-legume.
        if (
            _is_legume(previous_crop.get("legume"))
            and not _is_legume(current_crop.get("legume"))
        ):
            legume_bonus += LEGUME_ROTATION_BONUS

            explanations.append(
                f"Legume-to-non-legume sequence: "
                f"{previous_crop.get('crop_name')} followed by "
                f"{current_crop.get('crop_name')}."
            )

    final_score = (
        average_suitability
        - family_penalty
        + legume_bonus
    )

    final_score = round(
        max(0, min(100, final_score)),
        2,
    )

    if not explanations:
        explanations.append(
            "No family repetition or legume transition "
            "adjustments were identified."
        )

    return {
        "average_crop_suitability": round(
            average_suitability,
            2,
        ),
        "family_penalty": family_penalty,
        "legume_bonus": legume_bonus,
        "overall_rotation_score": final_score,
        "explanations": explanations,
    }


# ---------------------------------------------------------
# 5. SOURCE WARNING COLLECTION
# ---------------------------------------------------------

def _collect_source_warnings(rotation: list[dict]) -> list[str]:
    """
    Collect source verification warnings for crops
    included in a rotation.
    """

    warnings = []

    for item in rotation:

        crop_name = item["crop_name"]

        crop_warnings = item["suitability_details"].get(
            "source_warnings",
            [],
        )

        for warning in crop_warnings:
            warnings.append(
                f"{crop_name}: {warning}"
            )

    return warnings


# ---------------------------------------------------------
# 6. BUILD DASHBOARD-SAFE CROP SEQUENCE
# ---------------------------------------------------------

def _build_crop_sequence_item(item: dict) -> dict:
    """
    Build a complete crop recommendation object.

    Includes suitability details and source provenance
    for downstream dashboard and Member 4 integration.
    """

    crop = item["crop"]
    suitability = item["suitability_details"]

    return {
        "season": item["season"],

        "crop_id": item["crop_id"],
        "crop_name": item["crop_name"],

        "suitability_score": item["suitability_score"],

        # Full suitability assessment
        "suitability_details": suitability,

        # Source provenance
        "source_name": crop.get("source_name"),
        "source_urls": crop.get("source_urls"),
        "source_accessed_date": crop.get(
            "source_accessed_date"
        ),
        "source_notes": crop.get("source_notes"),

        # Verification status
        "source_verification": suitability.get(
            "source_verification",
            "no_explicit_flag",
        ),

        "source_warnings": suitability.get(
            "source_warnings",
            [],
        ),
    }


# ---------------------------------------------------------
# 7. GENERATE AND RANK CROP ROTATIONS
# ---------------------------------------------------------

def generate_crop_rotations(
    crops: list[dict],
    seasonal_conditions: list[dict],
    farm_profile: dict,
    top_n: int = 5,
    minimum_data_coverage: float = 60,
    max_candidates_per_season: int = 5,
) -> list[dict]:
    """
    Generate and rank multi-season crop rotations.

    Parameters
    ----------
    crops:
        Crop records loaded from the crop database.

    seasonal_conditions:
        List containing one environmental condition
        dictionary for each requested season.

        Example:

        [
            {
                "season": "kharif",
                "environmental_data": {
                    "temperature_c": 28,
                    "rainfall_mm": 480
                }
            },
            {
                "season": "rabi",
                "environmental_data": {
                    "temperature_c": 25,
                    "rainfall_mm": 300
                }
            }
        ]

    farm_profile:
        Example:

        {
            "soil_type": "loamy",
            "water_availability": "rainfed"
        }

    top_n:
        Maximum number of rotations to return.

    minimum_data_coverage:
        Minimum required suitability data coverage.

    max_candidates_per_season:
        Maximum number of candidate crops considered
        for each season.

    Returns
    -------
    list[dict]
        Ranked crop rotation recommendations, including
        suitability details and source verification warnings.
    """

    # -----------------------------------------------------
    # INPUT VALIDATION
    # -----------------------------------------------------

    if not isinstance(crops, list) or not crops:
        raise ValueError(
            "crops must be a non-empty list."
        )

    if not isinstance(seasonal_conditions, list):
        raise TypeError(
            "seasonal_conditions must be a list."
        )

    if len(seasonal_conditions) < 2:
        raise ValueError(
            "At least two seasons are required."
        )

    if not isinstance(farm_profile, dict):
        raise TypeError(
            "farm_profile must be a dictionary."
        )

    if not isinstance(top_n, int) or isinstance(top_n, bool):
        raise ValueError(
            "top_n must be a positive integer."
        )

    if top_n < 1:
        raise ValueError(
            "top_n must be at least 1."
        )

    if (
        not isinstance(max_candidates_per_season, int)
        or isinstance(max_candidates_per_season, bool)
        or max_candidates_per_season < 1
    ):
        raise ValueError(
            "max_candidates_per_season must be a positive integer."
        )

    if (
        not isinstance(minimum_data_coverage, (int, float))
        or isinstance(minimum_data_coverage, bool)
        or not 0 <= minimum_data_coverage <= 100
    ):
        raise ValueError(
            "minimum_data_coverage must be between 0 and 100."
        )

    # -----------------------------------------------------
    # EVALUATE CROPS FOR EVERY SEASON
    # -----------------------------------------------------

    season_candidates = []

    for seasonal_condition in seasonal_conditions:

        if not isinstance(seasonal_condition, dict):
            raise TypeError(
                "Each seasonal condition must be a dictionary."
            )

        candidates = _get_season_candidates(
            crops=crops,
            seasonal_condition=seasonal_condition,
            farm_profile=farm_profile,
            minimum_data_coverage=minimum_data_coverage,
        )

        # No valid crops for a season means no valid rotation.
        if not candidates:
            return []

        season_candidates.append(
            candidates[:max_candidates_per_season]
        )

    # -----------------------------------------------------
    # GENERATE POSSIBLE CROP COMBINATIONS
    # -----------------------------------------------------

    rotations = []

    for combination in product(*season_candidates):

        rotation = []

        for index, candidate in enumerate(combination):

            suitability = candidate["suitability"]
            crop = candidate["crop"]

            rotation.append({
                "season": seasonal_conditions[index]["season"],
                "crop_id": suitability["crop_id"],
                "crop_name": suitability["crop_name"],
                "suitability_score": suitability["overall_score"],
                "crop": crop,
                "suitability_details": suitability,
            })

        # Avoid planting the exact same crop consecutively.
        crop_ids = [
            item["crop_id"]
            for item in rotation
        ]

        if any(
            crop_ids[index] == crop_ids[index - 1]
            for index in range(1, len(crop_ids))
        ):
            continue

        # Calculate the rotation score.
        score_details = _score_rotation(rotation)

        # Collect warnings for crops in this rotation only.
        source_warnings = _collect_source_warnings(rotation)

        # Build complete crop sequence for Member 4.
        crop_sequence = [
            _build_crop_sequence_item(item)
            for item in rotation
        ]

        rotations.append({
            "rotation_length": len(rotation),

            "seasons": [
                item["season"]
                for item in rotation
            ],

            "crop_sequence": crop_sequence,

            **score_details,

            "score_type": "heuristic_rule_based",

            "source_warnings": source_warnings,

            "limitations": [
                "Rotation bonuses and penalties are heuristic.",
                "Crop family alone does not capture all rotation risks.",
                "Soil nutrient changes are not dynamically modelled.",
                "Pest, disease and local agronomic constraints "
                "require additional validation.",
                "Crop suitability depends on the quality of "
                "the environmental and crop reference data.",
                "Crop reference records marked for verification "
                "should not be treated as fully validated.",
            ],
        })

    # -----------------------------------------------------
    # RANK ROTATIONS
    # -----------------------------------------------------

    rotations.sort(
        key=lambda item: item["overall_rotation_score"],
        reverse=True,
    )

    ranked_rotations = rotations[:top_n]

    for index, rotation in enumerate(
        ranked_rotations,
        start=1,
    ):
        rotation["rank"] = index

    return ranked_rotations
