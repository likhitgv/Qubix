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
    center: Optional[tuple[float, float]] = None,
    zoom: Optional[int] = None,
) -> folium.Map:
    """Build a Folium map. Pure function: no Streamlit calls, easy to test.

    grid_points: optional DataFrame (grid_id, latitude, longitude) drawn as small dots
    showing the downloaded all-India NASA coverage. grid_link: the NASA grid cell used
    for the farm point; drawn as a ring with a line from the farm. india_view zooms out
    to the whole country.
    """
    fmap = folium.Map(
        location=center or (INDIA_CENTER if india_view else KARNATAKA_CENTER),
        zoom_start=zoom or (5 if india_view else 7),
        tiles="OpenStreetMap",  # free, no API key
        control_scale=True,
    )
    # Calm light map: soften the standard tiles slightly so markers stand out.
    fmap.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tile-pane{filter:saturate(.7) sepia(.12) brightness(1.02);}"
        ".leaflet-control-attribution{font-size:10px!important;}"
        ".leaflet-popup-content-wrapper{border-radius:8px;}</style>"
    ))

    if grid_points is not None and not grid_points.empty:
        layer = folium.FeatureGroup(name="NASA grid coverage", show=True)
        for row in grid_points.itertuples():
            folium.CircleMarker(
                location=(row.latitude, row.longitude), radius=2, weight=0, fill=True,
                fill_color="#7A7461", fill_opacity=0.6, tooltip=f"NASA weather area {row.grid_id}",
            ).add_to(layer)
        layer.add_to(fmap)

    for d in DISTRICTS:
        is_selected = d["name"] == selected_district
        folium.CircleMarker(
            location=(d["latitude"], d["longitude"]),
            radius=11 if is_selected else 7,
            color="#A4673A" if is_selected else "#2F6B3A",
            weight=3 if is_selected else 2,
            fill=True,
            fill_opacity=0.55,
            tooltip=d["name"],
            popup=folium.Popup(_district_popup(d, summary), max_width=260),
        ).add_to(fmap)

    if grid_link is not None:
        folium.CircleMarker(
            location=grid_link, radius=9, color="#C98B2B", weight=2, fill=False,
            tooltip="NASA weather area used for this field",
        ).add_to(fmap)
        if farm_point is not None:
            folium.PolyLine([farm_point, grid_link], color="#C98B2B", weight=2, dash_array="6", opacity=0.9).add_to(fmap)

    if farm_point is not None:
        folium.Marker(
            location=farm_point,
            tooltip="Your field",
            icon=folium.Icon(color="green", icon="leaf", prefix="fa"),
        ).add_to(fmap)
        if selected_district:
            d = next((x for x in DISTRICTS if x["name"] == selected_district), None)
            if d:
                folium.PolyLine(
                    [farm_point, (d["latitude"], d["longitude"])],
                    color="#C98B2B", weight=2, dash_array="6", opacity=0.9,
                ).add_to(fmap)

    return fmap
