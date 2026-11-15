"""KAIRO advisor: plain-language explanation of a computed plan.

Two layers:
  1. ``template_explanation`` - deterministic text built only from the plan.
     Always available, works offline.
  2. ``ai_explanation`` - optional LLM explanation. It receives only the
     facts the modules computed, and its reply is rejected (falling back to the
     template) if it contains numbers that are not in those facts.

Any OpenAI-compatible chat API works. Free options are preconfigured: Groq,
Google Gemini and OpenRouter. Choose one with KAIRO_AI_PROVIDER and set that
provider's key in the environment (see .env.example). Keys are never logged.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable, Optional

import requests

# Preset free-tier providers (OpenAI-compatible /chat/completions). Free-tier
# model names change over time: override with KAIRO_MODEL if a default is retired.
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
        "key_env": "GROQ_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "key_env": "GEMINI_API_KEY",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_env": "OPENROUTER_API_KEY",
    },
}
DEFAULT_PROVIDER = "groq"
REQUEST_TIMEOUT_S = 30

SYSTEM_PROMPT = (
    "You are KAIRO, a careful farm-advisory explainer. You are given FACTS computed "
    "by KAIRO's modules for one farm. Explain the ranked crop rotations in plain, "
    "friendly language for a farmer.\n"
    "Rules:\n"
    "- Use ONLY numbers and crops present in FACTS. Never invent yields, prices, "
    "water savings, dates or soil improvements.\n"
    "- If FACTS show data needs verification or a limitation, say so.\n"
    "- Say that NASA POWER data is gridded and modelled, not measured on the farm.\n"
    "- This is decision support, not agronomic advice: tell the farmer to confirm with "
    "a local agronomist and a soil test.\n"
    "- Write crop names exactly as they appear in FACTS (English). In another language "
    "you may add the local name in brackets, but never replace the English name.\n"
    "- Never copy field names such as needs_verification; say it in words.\n"
    "- Plain text only: no markdown, no bullet symbols, no asterisks. Keep it under 180 words."
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


def _setting(name: str, default: str) -> str:
    """Read KAIRO_<name>, falling back to the legacy KYRO_<name> spelling."""
    return os.environ.get(f"KAIRO_{name}") or os.environ.get(f"KYRO_{name}") or default


def provider_config() -> Optional[dict[str, str]]:
    """Resolve the active provider's settings, or None if unknown/no key."""
    name = _setting("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    preset = PROVIDERS.get(name)
    if preset is None:
        return None
    key = os.environ.get(preset["key_env"], "").strip()
    if not key:
        return None
    return {
        "provider": name,
        "api_key": key,
        "base_url": _setting("AI_BASE_URL", preset["base_url"]).rstrip("/"),
        "model": _setting("MODEL", preset["model"]),
    }


def ai_available() -> bool:
    return provider_config() is not None


def active_provider_label() -> str:
    name = _setting("AI_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    return name if name in PROVIDERS else f"{name} (unknown)"


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
    post: Optional[Callable[..., Any]] = None,
    config: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Ask the configured LLM to explain the plan. Always returns a usable result.

    Returns {"text", "source", "fallback_reason"}; source is "ai" or "template".
    ``post`` and ``config`` exist so tests can run without network or keys.
    """
    fallback = template_explanation(plan)
    cfg = config or provider_config()
    if cfg is None:
        return {"text": fallback, "source": "template",
                "fallback_reason": "No AI provider key configured."}

    facts = build_facts(plan)
    sender = post or requests.post
    try:
        response = sender(
            f"{cfg['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {cfg['api_key']}",
                     "Content-Type": "application/json"},
            json={
                "model": cfg["model"],
                "max_tokens": 1500,  # reasoning models spend tokens thinking first
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",
                     "content": f"Reply in {language}.\nFACTS:\n{json.dumps(facts, indent=2)}"},
                ],
            },
            timeout=REQUEST_TIMEOUT_S,
        )
        response.raise_for_status()
        text = (response.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as error:  # network, auth, rate limit, bad payload
        # Report only the error type: messages can echo request details.
        return {"text": fallback, "source": "template",
                "fallback_reason": f"AI request failed ({type(error).__name__})."}

    if not text:
        return {"text": fallback, "source": "template", "fallback_reason": "Empty AI reply."}
    if not numbers_are_grounded(text, facts):
        return {"text": fallback, "source": "template",
                "fallback_reason": "AI reply contained figures not in the computed data."}
    # Required wording is added by code, never left to the model.
    text = f"{text}\n\n{plan['data_nature']} {plan['disclaimer']}"
    return {"text": text, "source": "ai", "fallback_reason": None}
