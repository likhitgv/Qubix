"""Rule-based sustainability indicators for KAIRO crop rotations.

Everything here is derived only from fields in the crop database (crop family,
legume flag, water requirement) and from the rotation the engine produced.
No yield, water-saving or soil-restoration numbers are computed or claimed:
the output is a transparent *indicator* for comparing options, not a
measurement of real-world outcomes.
"""

from __future__ import annotations

from typing import Any

INDICATOR_NOTE = (
    "Indicators are rule-based and describe the rotation's structure only. "
    "They are not measured or modelled results for any field."
)

# Prototype points. Design choices, not calibrated agronomic weights.
_POINTS = {"legume": 40, "no_family_repeat": 30, "diversity": 30}


def _index_crops(crops: list[dict]) -> dict[str, dict]:
    return {str(crop["crop_id"]): crop for crop in crops}


def _previous_crop_ids(previous_text: str | None, crops: list[dict]) -> list[str]:
    """Match free-text previous crops against known crop names/ids."""
    if not previous_text:
        return []
    text = previous_text.lower()
    found = []
    for crop in crops:
        names = {str(crop["crop_id"]).lower(), str(crop["crop_name"]).lower()}
        if any(name and name in text for name in names):
            found.append(str(crop["crop_id"]))
    return found


def evaluate_rotation_sustainability(
    rotation: dict[str, Any],
    crops: list[dict],
    previous_crops_text: str | None = None,
) -> dict[str, Any]:
    """Return structural sustainability indicators for one rotation."""

    by_id = _index_crops(crops)
    sequence = rotation.get("crop_sequence", [])
    members = [by_id[item["crop_id"]] for item in sequence if item["crop_id"] in by_id]

    if not members:
        return {
            "rotation_rank": rotation.get("rank"),
            "available": False,
            "reason": "No crop records found for this rotation.",
            "note": INDICATOR_NOTE,
        }

    families = [str(c["crop_family"]) for c in members]
    legume_count = sum(1 for c in members if c.get("legume"))
    distinct_crops = len({c["crop_id"] for c in members})
    distinct_families = len(set(families))
    consecutive_repeat = any(a == b for a, b in zip(families, families[1:]))
    rainfed_count = sum(
        1 for c in members if str(c["water_requirement"]).lower() == "rainfed"
    )

    previous_ids = _previous_crop_ids(previous_crops_text, crops)
    previous_families = {str(by_id[i]["crop_family"]) for i in previous_ids}
    first_family = families[0]
    follows_same_family = first_family in previous_families

    points = 0
    indicators = []

    has_legume = legume_count > 0
    points += _POINTS["legume"] if has_legume else 0
    indicators.append({
        "name": "Legume inclusion",
        "status": "good" if has_legume else "none",
        "detail": (
            f"{legume_count} of {len(members)} crops are legumes."
            if has_legume else "No legume in this rotation."
        ),
    })

    points += 0 if consecutive_repeat else _POINTS["no_family_repeat"]
    indicators.append({
        "name": "Family rotation",
        "status": "warning" if consecutive_repeat else "good",
        "detail": (
            "The same crop family appears in back-to-back seasons."
            if consecutive_repeat
            else "No crop family repeats in consecutive seasons."
        ),
    })

    diversity_ratio = distinct_families / len(members)
    points += round(_POINTS["diversity"] * diversity_ratio)
    indicators.append({
        "name": "Crop diversity",
        "status": "good" if diversity_ratio == 1 else "moderate",
        "detail": f"{distinct_crops} distinct crops from {distinct_families} families.",
    })

    indicators.append({
        "name": "Water source",
        "status": "info",
        "detail": (
            f"{rainfed_count} of {len(members)} crops are listed as rainfed in "
            "the reference database. Actual water use is not estimated."
        ),
    })

    if previous_ids:
        indicators.append({
            "name": "Previous crops",
            "status": "warning" if follows_same_family else "good",
            "detail": (
                f"First crop is in the same family ({first_family}) as a previous crop."
                if follows_same_family
                else "First crop is in a different family from your previous crops."
            ),
        })

    return {
        "rotation_rank": rotation.get("rank"),
        "available": True,
        "indicator_score": min(points, 100),
        "legume_count": legume_count,
        "distinct_crops": distinct_crops,
        "distinct_families": distinct_families,
        "consecutive_family_repeat": consecutive_repeat,
        "follows_previous_family": follows_same_family,
        "indicators": indicators,
        "note": INDICATOR_NOTE,
    }


def compare_rotations(
    rotations: list[dict[str, Any]],
    crops: list[dict],
    previous_crops_text: str | None = None,
) -> list[dict[str, Any]]:
    """Evaluate each rotation; keep the input order."""
    return [
        evaluate_rotation_sustainability(r, crops, previous_crops_text)
        for r in rotations
    ]
