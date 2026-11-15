"""Folium map for KAIRO: district markers, selected district, farm pin."""

from __future__ import annotations

from typing import Optional

import folium
import pandas as pd

from config.districts import DISTRICTS

KARNATAKA_CENTER = (15.0, 75.7)
INDIA_CENTER = (22.5, 79.0)


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
    grid_points: Optional[pd.DataFrame] = None,
    grid_link: Optional[tuple[float, float]] = None,
    india_view: bool = False,
) -> folium.Map:
    """Build a Folium map. Pure function: no Streamlit calls, easy to test.

    grid_points: optional DataFrame (grid_id, latitude, longitude) drawn as small dots
    showing the downloaded all-India NASA coverage. grid_link: the NASA grid cell used
    for the farm point; drawn as a ring with a line from the farm. india_view zooms out
    to the whole country.
    """
    fmap = folium.Map(
        location=INDIA_CENTER if india_view else KARNATAKA_CENTER,
        zoom_start=5 if india_view else 7,
        tiles="OpenStreetMap",  # free, no API key
        control_scale=True,
    )
    # Dark look without a paid basemap: invert the tile layer only.
    fmap.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tile-pane{filter:invert(1) hue-rotate(180deg) "
        "brightness(.85) contrast(.9) saturate(.7);}"
        ".leaflet-control-attribution{background:rgba(6,10,17,.72)!important;color:#8b9ab0!important;font-size:10px!important;}"
        ".leaflet-control-attribution a{color:#67e8f9!important;}"
        ".leaflet-bar a{background:#0f1726!important;color:#e6edf6!important;border-color:rgba(148,163,184,.25)!important;}"
        ".leaflet-bar a:hover{background:#16233a!important;}"
        ".leaflet-popup-content-wrapper,.leaflet-popup-tip{background:#0f1726;color:#e6edf6;}"
        ".leaflet-control-scale-line{background:rgba(6,10,17,.6)!important;color:#8b9ab0!important;"
        "border-color:#5f6f86!important;}</style>"
    ))

    if grid_points is not None and not grid_points.empty:
        layer = folium.FeatureGroup(name="NASA grid coverage", show=True)
        for row in grid_points.itertuples():
            folium.CircleMarker(
                location=(row.latitude, row.longitude), radius=2, weight=0, fill=True,
                fill_color="#64748b", fill_opacity=0.55, tooltip=f"NASA grid point {row.grid_id}",
            ).add_to(layer)
        layer.add_to(fmap)

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

    if grid_link is not None:
        folium.CircleMarker(
            location=grid_link, radius=9, color="#fbbf24", weight=2, fill=False,
            tooltip="NASA grid cell used for this farm",
        ).add_to(fmap)
        if farm_point is not None:
            folium.PolyLine([farm_point, grid_link], color="#fbbf24", weight=2, dash_array="6", opacity=0.8).add_to(fmap)

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
