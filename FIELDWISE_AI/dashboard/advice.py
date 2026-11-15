"""Plain-language wording for a recommendation, built only from computed results.

Presentation helpers: nothing here changes scores or rankings. Every sentence is derived
from the component scores and weather averages the modules already produced.
"""

from __future__ import annotations

from typing import Optional

GOOD_FIT = 85    # a component at or above this counts as a reason the crop fits
WEAK_FIT = 60    # a component below this is worth a "keep in mind"

_PHRASE = {
    "temperature": "the temperature",
    "rainfall": "the rainfall",
    "soil": "your soil",
    "water": "your water setup",
}


def join_phrases(items: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b and c'."""
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def rotation_label(rot: dict) -> str:
    return " → ".join(c["crop_name"] for c in rot["crop_sequence"])


def season_label(rot: dict) -> str:
    return ", then ".join(c["season"].title() for c in rot["crop_sequence"])


def fit_reasons(rot: dict, sus: Optional[dict] = None) -> list[str]:
    """Short reasons a plan may fit: one line per crop, plus a legume note if relevant."""
    reasons = []
    for crop in rot["crop_sequence"]:
        comps = crop["suitability_details"].get("component_scores", {})
        good = [
            _PHRASE[k] for k in ("temperature", "rainfall", "soil", "water")
            if comps.get(k) is not None and comps[k] >= GOOD_FIT
        ]
        name = f"{crop['crop_name']} ({crop['season'].title()})"
        reasons.append(f"{name} suits {join_phrases(good)}." if good else f"{name} is only a partial fit.")
    if sus and sus.get("available") and sus.get("legume_count"):
        reasons.append("A legume in the plan adds variety between crop families.")
    return reasons


def main_caution(rot: dict, conditions: dict, profile: Optional[dict] = None) -> Optional[str]:
    """The single most important trade-off: the weakest component below WEAK_FIT, if any.

    ``conditions`` maps season -> environmental_data (temperature_c, rainfall_mm).
    """
    weakest = None
    for crop in rot["crop_sequence"]:
        for name, value in crop["suitability_details"].get("component_scores", {}).items():
            if value is not None and value < WEAK_FIT and (weakest is None or value < weakest[2]):
                weakest = (crop, name, value)
    if weakest is None:
        return None
    crop, name, _ = weakest
    env = conditions.get(crop["season"], {})
    who = f"{crop['crop_name']} in the {crop['season'].title()} season"
    if name == "rainfall" and "rainfall_mm" in env:
        return f"{who}: rain here averages about {env['rainfall_mm']:.0f} mm, outside the usual range for this crop."
    if name == "temperature" and "temperature_c" in env:
        return f"{who}: temperature averages {env['temperature_c']:.1f} °C, outside the usual range for this crop."
    if name == "soil":
        soil = (profile or {}).get("soil_label", "your soil")
        return f"{crop['crop_name']} is not usually listed for {soil.lower()}."
    if name == "water":
        return f"{crop['crop_name']} may not match how this field is irrigated."
    return f"{who} is a weaker fit."
