"""Kyro advisor: plain-language explanation of a computed plan.

Two layers:
  1. ``template_explanation`` - deterministic text built only from the plan.
     Always available, works offline.
  2. ``ai_explanation`` - optional Claude explanation. It receives only the
     facts the modules computed, and its reply is rejected (falling back to the
     template) if it contains numbers that are not in those facts.

The API key is read from the ANTHROPIC_API_KEY environment variable only.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Optional

DEFAULT_MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = (
    "You are Kyro, a careful farm-advisory explainer. You are given FACTS computed "
    "by Kyro's modules for one farm. Explain the ranked crop rotations in plain, "
    "friendly language for a farmer.\n"
    "Rules:\n"
    "- Use ONLY numbers and crops present in FACTS. Never invent yields, prices, "
    "water savings, dates or soil improvements.\n"
    "- If FACTS show data needs verification or a limitation, say so.\n"
    "- Say that NASA POWER data is gridded and modelled, not measured on the farm.\n"
    "- This is decision support, not agronomic advice: tell the farmer to confirm with "
    "a local agronomist and a soil test.\n"
    "- Keep it under 220 words. No markdown headings."
)


def build_facts(plan: dict[str, Any]) -> dict[str, Any]:
    """Reduce a plan to the compact facts the advisor may talk about."""
    seasons = {
        c["season"]: {
            "temperature_c": round(c["environmental_data"]["temperature_c"], 1),
            "rainfall_mm": round(c["environmental_data"]["rainfall_mm"]),
        }
        for c in plan["conditions"]
    }
    rotations = []
    for rot, sus in zip(plan["rotations"], plan["sustainability"]):
        rotations.append({
            "rank": rot["rank"],
            "score": round(rot["overall_rotation_score"], 1),
            "crops": [
                {
                    "season": c["season"],
                    "crop": c["crop_name"],
                    "score": round(c["suitability_score"]),
                    "needs_verification": bool(c.get("source_warnings")),
                }
                for c in rot["crop_sequence"]
            ],
            "legume_included": bool(sus.get("legume_count")) if sus.get("available") else None,
            "sustainability_indicator": sus.get("indicator_score"),
        })
    return {
        "district": plan["district"],
        "farm_inputs_used": plan["profile_used"],
        "season_climate": seasons,
        "rotations": rotations,
        "warnings": plan["warnings"],
        "data_nature": plan["data_nature"],
    }


def template_explanation(plan: dict[str, Any]) -> str:
    """Deterministic explanation; no external service, no invented figures."""
    facts = build_facts(plan)
    lines = []
    clim = facts["season_climate"]
    parts = [
        f"{s} averages {v['temperature_c']} °C with about {v['rainfall_mm']} mm of rain"
        for s, v in clim.items()
    ]
    lines.append(
        f"For {facts['district']}, NASA POWER data shows " + "; ".join(parts) + "."
    )
    if not facts["rotations"]:
        lines.append("No rotation met the minimum requirements for the inputs given.")
    else:
        top = facts["rotations"][0]
        seq = " then ".join(f"{c['crop']} in {c['season']}" for c in top["crops"])
        lines.append(f"The highest-ranked rotation is {seq} (rotation score {top['score']} out of 100).")
        if top["legume_included"]:
            lines.append("It includes a legume, which is a structural plus for rotation variety.")
        flagged = sorted({c["crop"] for r in facts["rotations"] for c in r["crops"] if c["needs_verification"]})
        if flagged:
            lines.append(
                "Reference data for " + ", ".join(flagged) + " still needs verification "
                "against primary sources, so treat those scores with extra caution."
            )
    for w in facts["warnings"]:
        lines.append(w)
    lines.append(facts["data_nature"])
    lines.append(plan["disclaimer"])
    return " ".join(lines)


def ai_available() -> bool:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


_NUM = re.compile(r"\d+(?:\.\d+)?")


def numbers_are_grounded(text: str, facts: dict[str, Any]) -> bool:
    """True if every number in ``text`` also appears in the facts JSON."""
    allowed = set(_NUM.findall(json.dumps(facts)))
    # Rounded/percent forms of grounded numbers are acceptable (e.g. 94.1 -> 94).
    allowed |= {str(int(float(n))) for n in allowed}
    return all(n in allowed for n in _NUM.findall(text))


def ai_explanation(
    plan: dict[str, Any],
    language: str = "English",
    client_factory: Optional[Callable[[], Any]] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """Ask Claude to explain the plan. Always returns a usable result.

    Returns {"text", "source"} where source is "ai" or "template", plus
    "fallback_reason" when the template was used.
    """
    fallback = template_explanation(plan)
    if client_factory is None and not ai_available():
        return {"text": fallback, "source": "template",
                "fallback_reason": "No ANTHROPIC_API_KEY configured."}
    facts = build_facts(plan)
    try:
        if client_factory is None:
            import anthropic
            client = anthropic.Anthropic()
        else:
            client = client_factory()
        reply = client.messages.create(
            model=model or os.environ.get("KYRO_MODEL", DEFAULT_MODEL),
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Reply in {language}.\nFACTS:\n{json.dumps(facts, indent=2)}",
            }],
        )
        text = "".join(b.text for b in reply.content if getattr(b, "type", "") == "text").strip()
    except Exception as error:  # network, auth, rate limit, SDK errors
        return {"text": fallback, "source": "template",
                "fallback_reason": f"AI request failed ({type(error).__name__})."}

    if not text:
        return {"text": fallback, "source": "template", "fallback_reason": "Empty AI reply."}
    if not numbers_are_grounded(text, facts):
        return {"text": fallback, "source": "template",
                "fallback_reason": "AI reply contained figures not in the computed data."}
    return {"text": text, "source": "ai", "fallback_reason": None}
