"""Folium map for KAIRO: district markers, selected district, farm pin."""

from __future__ import annotations

from typing import Optional

import folium
import pandas as pd

from config.districts import DISTRICTS

KARNATAKA_CENTER = (15.0, 75.7)


def _district_popup(district: dict, summary: Optional[pd.DataFrame]) -> str:
    html = (
        f"<b>{district['name']}</b><br>"
        f"{district['latitude']:.4f}, {district['longitude']:.4f}<br>"
    )
    if summary is not None and not summary.empty:
        rows = summary[
            (summary["location"] == district["name"]) & (summary["complete"] == True)  # noqa: E712
        ]
        if not rows.empty:
            html += "<hr style='margin:4px 0'>"
            for season in ("kharif", "rabi"):
                s = rows[rows["season"] == season]
                if not s.empty:
                    html += (
                        f"{season.title()}: {s['temperature_c'].mean():.1f} °C, "
                        f"{s['rainfall_mm'].mean():.0f} mm<br>"
                    )
            html += "<small>NASA POWER seasonal averages</small>"
    return html


def build_map(
    selected_district: Optional[str] = None,
    farm_point: Optional[tuple[float, float]] = None,
    summary: Optional[pd.DataFrame] = None,
) -> folium.Map:
    """Build a Folium map. Pure function: no Streamlit calls, easy to test."""
    fmap = folium.Map(
        location=KARNATAKA_CENTER,
        zoom_start=7,
        tiles="OpenStreetMap",  # free, no API key
        control_scale=True,
    )
    # Dark look without a paid basemap: invert the tile layer only.
    fmap.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tile-pane{filter:invert(1) hue-rotate(180deg) "
        "brightness(.85) contrast(.9) saturate(.7);}</style>"
    ))

    for d in DISTRICTS:
        is_selected = d["name"] == selected_district
        folium.CircleMarker(
            location=(d["latitude"], d["longitude"]),
            radius=11 if is_selected else 7,
            color="#34d399" if is_selected else "#22d3ee",
            weight=3 if is_selected else 2,
            fill=True,
            fill_opacity=0.55,
            tooltip=d["name"],
            popup=folium.Popup(_district_popup(d, summary), max_width=260),
        ).add_to(fmap)

    if farm_point is not None:
        folium.Marker(
            location=farm_point,
            tooltip="Your farm",
            icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
        ).add_to(fmap)
        if selected_district:
            d = next((x for x in DISTRICTS if x["name"] == selected_district), None)
            if d:
                folium.PolyLine(
                    [farm_point, (d["latitude"], d["longitude"])],
                    color="#fbbf24", weight=2, dash_array="6", opacity=0.8,
                ).add_to(fmap)

    return fmap
