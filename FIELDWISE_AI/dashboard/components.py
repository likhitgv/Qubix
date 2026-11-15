"""HTML building blocks for the KAIRO UI.

Functions return single-line HTML (no blank lines or 4-space indents, which Markdown
would turn into code blocks). All dynamic text is escaped.
"""

from __future__ import annotations

from html import escape
from typing import Iterable, Optional

import streamlit as st

GOOD, MID = 75, 50


def _e(value) -> str:
    return escape(str(value), quote=True)


def render(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


# ----------------------------------------------------------------- headings
def page_header(title: str, sub: str = "") -> str:
    sub_html = f'<div class="page-sub">{_e(sub)}</div>' if sub else ""
    return f'<div class="page-title">{_e(title)}</div>{sub_html}'


def step(number: int, title: str, hint: str = "") -> str:
    hint_html = f"<p>{_e(hint)}</p>" if hint else ""
    return (
        f'<div class="step"><div class="n">{int(number)}</div>'
        f"<div><h3>{_e(title)}</h3>{hint_html}</div></div>"
    )


def brand() -> str:
    return (
        '<div class="brand"><span class="wordmark">KAIRO</span>'
        '<span class="tagline">Crop planning from NASA weather records</span></div>'
    )


def field_note(profile: Optional[dict]) -> str:
    if not profile:
        return '<div class="fieldnote">No field added yet</div>'
    return (
        f'<div class="fieldnote">Your field: <b>{_e(profile["district"])}</b> · '
        f'{_e(profile["soil_label"])} · {_e(profile["water_label"])}</div>'
    )


def source_line(text: str) -> str:
    return f'<div class="source">{_e(text)}</div>'


# ----------------------------------------------------------------- notes
def note_html(text: str, tone: str = "plain") -> str:
    """``text`` may contain trusted inline HTML (e.g. <b>); never pass user input."""
    cls = {"plain": "note", "caution": "note caution", "good": "note good"}[tone]
    return f'<div class="{cls}">{text}</div>'


def note(text: str, tone: str = "plain") -> None:
    render(note_html(text, tone))


def banner(text: str, tone: str = "warn") -> None:
    """Compatibility wrapper: warn -> caution note, info -> plain note, ok -> good note."""
    note(text, {"warn": "caution", "info": "plain", "ok": "good"}[tone])


def empty_state(title: str, text: str) -> None:
    render(f'<div class="panel empty"><h3>{_e(title)}</h3><p>{_e(text)}</p></div>')


# ----------------------------------------------------------------- recommendation
def reco_card(
    label: str,
    title: str,
    seasons: str,
    fit: str,
    reasons: Iterable[str],
    caution: Optional[str],
    check: str,
) -> str:
    reasons_html = "".join(f"<li>{_e(r)}</li>" for r in reasons)
    why = f"<h4>Why this may fit your field</h4><ul>{reasons_html}</ul>" if reasons_html else ""
    keep = f'<div class="keep"><b>Keep in mind:</b> {_e(caution)}</div>' if caution else ""
    return (
        f'<div class="reco"><div class="eyebrow">{_e(label)}</div>'
        f'<div class="plan">{_e(title)} <span>{_e(seasons)}</span></div>'
        f'<div class="fit">{_e(fit)}</div>{why}{keep}'
        f'<div class="note" style="margin-top:1rem">{_e(check)}</div></div>'
    )


def alt_card(label: str, title: str, meta: str, caution: Optional[str] = None) -> str:
    extra = f'<div class="m" style="margin-top:.4rem">{_e(caution)}</div>' if caution else ""
    return (
        f'<div class="alt"><div class="eyebrow" style="color:#5F5A48">{_e(label)}</div>'
        f'<div class="t">{_e(title)}</div><div class="m">{_e(meta)}</div>{extra}</div>'
    )


def facts(items: list[tuple[str, str, str]]) -> str:
    """Quiet key/value strip: (label, value, small text)."""
    cells = "".join(
        f'<div><div class="k">{_e(k)}</div><div class="v">{_e(v)}</div><div class="s">{_e(s)}</div></div>'
        for k, v, s in items
    )
    return f'<div class="weather">{cells}</div>'


# ----------------------------------------------------------------- bars / grid
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


def grid(cards: list[str], min_width: int = 220, cols: int = 0) -> str:
    """Responsive card grid. cols=2 or 3 gives that many columns, then 1 on narrow screens."""
    cls = {2: "grid g2", 3: "grid g3"}.get(cols, "grid")
    return f'<div class="{cls}" style="--min:{int(min_width)}px">{"".join(cards)}</div>'
