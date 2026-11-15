"""HTML building blocks for the KAIRO UI.

Every function returns a single-line HTML string (no blank lines or leading
indentation, which Markdown would turn into code blocks). Dynamic text is
escaped.
"""

from __future__ import annotations

from html import escape
from typing import Iterable, Optional

import streamlit as st

GOOD, MID = 75, 50


def _e(value) -> str:
    return escape(str(value), quote=True)


def score_color(value: Optional[float]) -> str:
    if value is None:
        return "#64748b"
    if value >= 80:
        return "#34d399"
    if value >= 60:
        return "#22d3ee"
    if value >= 40:
        return "#fbbf24"
    return "#f87171"


def render(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def tag(text: str, tone: str = "green") -> str:
    return f'<span class="tag {_e(tone)}">{_e(text)}</span>'


def tags(items: Iterable[tuple[str, str]]) -> str:
    return "".join(tag(t, tone) for t, tone in items)


def section(kicker: str, title: str, sub: str = "") -> str:
    sub_html = f'<div class="sec-sub">{_e(sub)}</div>' if sub else ""
    return (
        f'<div class="kicker">{_e(kicker)}</div>'
        f'<div class="sec-title">{_e(title)}</div>{sub_html}'
    )


def stat(icon: str, label: str, value: str, sub: str = "") -> str:
    return (
        f'<div class="card"><div class="stat"><div class="ico">{icon}</div><div>'
        f'<div class="lbl">{_e(label)}</div><div class="val">{_e(value)}</div>'
        f'<div class="sub">{_e(sub)}</div></div></div></div>'
    )


def step_card(number: int, title: str, text: str) -> str:
    return (
        f'<div class="card hover"><div class="step-num">{number}</div>'
        f"<h4>{_e(title)}</h4><p class=\"t\">{_e(text)}</p></div>"
    )


def info_card(icon: str, title: str, text: str) -> str:
    return (
        f'<div class="card hover"><div style="font-size:1.5rem">{icon}</div>'
        f"<h4>{_e(title)}</h4><p class=\"t\">{_e(text)}</p></div>"
    )


def ring(value: Optional[float], label: str = "score", small: bool = False) -> str:
    v = 0 if value is None else max(0, min(100, float(value)))
    text = "n/a" if value is None else f"{v:.0f}"
    cls = "ring sm" if small else "ring"
    return (
        f'<div class="{cls}" style="--v:{v:.1f};--c:{score_color(value)}">'
        f'<div class="n">{text}<small>{_e(label.upper())}</small></div></div>'
    )


def score_bars(components: dict[str, Optional[float]]) -> str:
    rows = []
    for name, value in components.items():
        if value is None:
            continue
        v = max(0, min(100, float(value)))
        cls = "" if v >= GOOD else ("mid" if v >= MID else "low")
        rows.append(
            f'<div class="bar"><span class="nm">{_e(name)}</span>'
            f'<div class="track"><i class="{cls}" style="width:{v:.0f}%"></i></div>'
            f"<b>{v:.0f}</b></div>"
        )
    return "".join(rows)


def sequence(crop_sequence: list[dict]) -> str:
    parts = []
    for i, crop in enumerate(crop_sequence):
        if i:
            parts.append('<div class="arrow">→</div>')
        flag = " ⚠" if crop.get("source_warnings") else ""
        parts.append(
            f'<div class="step"><div class="se">{_e(crop["season"])}</div>'
            f'<div class="cn">{_e(crop["crop_name"])}{flag}</div>'
            f'<div class="sc">Suitability <b>{crop["suitability_score"]:.0f}</b>/100</div></div>'
        )
    return f'<div class="seq">{"".join(parts)}</div>'


def grid(cards: list[str], min_width: int = 220, four: bool = False, three: bool = False) -> str:
    """Responsive equal-height card grid (single HTML block).

    ``four=True`` gives 4 columns that fall back to 2 then 1 as the screen narrows,
    so a row of four never leaves an orphan card. ``three=True`` goes 3 then 1.
    """
    cls = "grid g4" if four else ("grid g3" if three else "grid")
    return f'<div class="{cls}" style="--min:{int(min_width)}px">{"".join(cards)}</div>'


def banner(text: str, tone: str = "warn") -> None:
    cls = {"warn": "banner", "info": "banner info", "ok": "banner ok"}[tone]
    icon = {"warn": "⚠️", "info": "ℹ️", "ok": "✅"}[tone]
    render(f'<div class="{cls}"><span>{icon}</span><span>{text}</span></div>')


def empty_state(icon: str, title: str, text: str) -> None:
    render(
        f'<div class="card empty"><div class="big">{icon}</div>'
        f"<h3>{_e(title)}</h3><p>{_e(text)}</p></div>"
    )


def topbar_brand() -> str:
    return (
        '<div class="topbar"><div class="logo">K</div><div>'
        '<div class="wordmark">KAIRO</div>'
        '<div class="wordsub">Farm intelligence</div></div></div>'
    )


def farm_chip(profile: Optional[dict]) -> str:
    if not profile:
        return '<div style="text-align:right"><span class="farmchip"><span class="dot off"></span>No farm saved</span></div>'
    return (
        '<div style="text-align:right"><span class="farmchip"><span class="dot"></span>'
        f'<b>{_e(profile["district"])}</b> · {_e(profile["soil_label"])} · {_e(profile["water_label"])}'
        "</span></div>"
    )
