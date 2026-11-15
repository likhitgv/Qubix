"""KAIRO - crop planning from NASA weather records.

Run:  py -3.11 -m streamlit run app.py
UI only: all data handling and scoring lives in modules/.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

from config.districts import DISTRICTS, districts_in_state, get_india_district, list_states
from config.soils import (
    SOIL_TYPES,
    WATER_SOURCES,
    soil_id_from_label,
    water_availability_from_source,
)
from dashboard import components as ui
from dashboard.advice import fit_reasons, main_caution, rotation_label, season_label
from dashboard.map_view import build_map
from dashboard.theme import ACCENT, ACCENT_2, ACCENT_3, inject_theme, plot_layout
from modules import advisor
from modules import kairo_service as svc
from modules import storage
from modules.crop_database import load_crop_database
from modules.crop_suitability_v2 import WEIGHTS
from modules.sustainability import INDICATOR_NOTE

load_dotenv()  # reads .env (AI provider keys) if present

st.set_page_config(
    page_title="KAIRO",
    page_icon="🌱",
    layout="centered",
    initial_sidebar_state="collapsed",
)
inject_theme()

DISTRICT_NAMES = [d["name"] for d in DISTRICTS]
SOIL_LABELS = [label for _, label in SOIL_TYPES]
PAGES = ["Home", "Farm", "Recommendations", "Climate", "Map", "Sustainability", "Advisor", "About"]
NAV_LABELS = {
    "Home": "Home",
    "Farm": "Your field",
    "Recommendations": "Recommendation",
    "Climate": "Weather",
    "Map": "Map",
    "Sustainability": "Rotation health",
    "Advisor": "Summary",
    "About": "About",
}
CHECK_LOCALLY = "Check with a local agronomist before planting."
NASA_SOURCE = (
    "Weather data: NASA POWER (gridded model estimates for a ~56 km area, not measurements from your field). "
    "KAIRO is decision support, not agronomic advice."
)
OUTSIDE_SHORT = "This place is outside the Karnataka districts KAIRO was tested in. Treat the advice as a starting point."


# ----------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def _daily() -> pd.DataFrame:
    return pd.read_csv(svc.DATA_DIR / "daily_2024-2025.csv", parse_dates=["date"])


@st.cache_data(show_spinner=False)
def _summary() -> pd.DataFrame:
    return svc.load_seasonal_summary()


@st.cache_data(show_spinner=False)
def _grid_points() -> pd.DataFrame:
    return svc.load_grid_points()


@st.cache_data(show_spinner=False)
def _grid_summary() -> pd.DataFrame:
    return svc.load_grid_summary()


def _grid_id_for(lat: float | None, lon: float | None) -> str | None:
    """NASA grid cell id for a location, or None if the grid files are missing/too far."""
    if lat is None or lon is None:
        return None
    try:
        g = svc.nearest_grid_point(lat, lon, _grid_points())
    except FileNotFoundError:
        return None
    return g["grid_id"] if g["within_coverage"] else None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "farm"


def _goto(page: str) -> None:
    st.session_state["_nav"] = page


def _open_saved(plan_id: int) -> None:
    loaded = storage.load_plan(plan_id)
    if loaded:
        st.session_state.profile, st.session_state.plan = loaded
        st.session_state["_nav"] = "Recommendations"


def _delete_saved(plan_id: int) -> None:
    storage.delete_plan(plan_id)


def _saved_plans_panel(expanded: bool = False) -> None:
    """List recent saved recommendations (SQLite) with Open and Delete."""
    try:
        rows = storage.list_plans(10)
    except (OSError, sqlite3.Error):
        return  # storage is a convenience; never block the main journey
    if not rows:
        return
    with st.expander(f"Your saved plans ({len(rows)})", expanded=expanded):
        for r in rows:
            c1, c2, c3 = st.columns([6, 1.3, 1.3], vertical_alignment="center")
            score = f" · fit score {r['top_score']:.0f}" if r["top_score"] is not None else ""
            c1.markdown(
                f"**{r['place']}** · {r['soil_label'] or 'Soil not given'} · {r['water_label'] or 'Water not given'}  \n"
                f"{r['top_rotation'] or 'No plan'}{score} · saved {r['created_at'][:10]}"
            )
            c2.button("Open", key=f"open_{r['id']}", on_click=_open_saved, args=(r["id"],))
            c3.button("Delete", key=f"del_{r['id']}", on_click=_delete_saved, args=(r["id"],))


def _need_plan() -> dict | None:
    plan = st.session_state.plan
    if not plan:
        ui.empty_state("Add your field details first", "KAIRO needs your location, soil and water to suggest a plan.")
        st.button("Add your field details", type="primary", on_click=_goto, args=("Farm",), key=f"need_{st.session_state.get('page')}")
        _saved_plans_panel(expanded=True)
    return plan


def _footer() -> None:
    ui.render(ui.source_line(NASA_SOURCE))


def _friendly(warning: str) -> str:
    """Shorter wording for the longer service warnings."""
    if warning == svc.OUTSIDE_KARNATAKA_NOTE:
        return OUTSIDE_SHORT
    return warning


# ----------------------------------------------------------------- chrome
def top_bar() -> str:
    # Pending navigation and the "never deselect" guard run before the widget exists.
    if "_nav" in st.session_state:
        st.session_state["page"] = st.session_state.pop("_nav")
    if "page" not in st.session_state:
        st.session_state["page"] = "Farm"  # the field setup is the main experience
    if st.session_state.get("page") is None:
        st.session_state["page"] = st.session_state.get("_last_page", "Farm")

    brand, chip = st.columns([3, 2], vertical_alignment="center")
    brand.markdown(ui.brand(), unsafe_allow_html=True)
    chip.markdown(ui.field_note(st.session_state.profile), unsafe_allow_html=True)
    page = st.segmented_control(
        "Navigate", PAGES, key="page", label_visibility="collapsed",
        format_func=lambda p: NAV_LABELS[p],
    )
    page = page or st.session_state.get("_last_page", "Farm")
    st.session_state["_last_page"] = page
    return page


# ----------------------------------------------------------------- Home
def page_home() -> None:
    ui.render(ui.page_header(
        "Plan your next crop with NASA weather records",
        "Add your field details and KAIRO suggests a crop plan for the coming seasons, with the reasons shown.",
    ))
    st.button("Add your field details", type="primary", on_click=_goto, args=("Farm",), key="cta_farm")
    st.write("")
    ui.render(ui.grid([
        '<div class="panel"><h4>1. Add your field</h4><p>Choose where it is, your soil type and how it gets water.</p></div>',
        '<div class="panel"><h4>2. We read the weather</h4><p>KAIRO averages past seasons of NASA weather data for your location.</p></div>',
        '<div class="panel"><h4>3. See the plan and why</h4><p>You get a best option, two alternatives and the reasons behind them.</p></div>',
    ], cols=3))
    ui.note(
        f"Works anywhere in India using NASA weather data. KAIRO's crop information was tested in five Karnataka districts. {CHECK_LOCALLY}",
    )
    _footer()


# ----------------------------------------------------------------- Farm
def page_farm() -> None:
    ui.render(ui.page_header("Add your field details", "Four short questions. You can change any answer later."))

    # Apply a map click from the previous run before the inputs exist.
    click = st.session_state.pop("_map_click", None)
    if click:
        st.session_state["farm_lat"], st.session_state["farm_lon"] = click
    st.session_state.setdefault("farm_lat", 15.4589)
    st.session_state.setdefault("farm_lon", 75.0078)
    st.session_state.setdefault("farm_district", "Ballari")
    st.session_state.setdefault("farm_soil", "Not sure")
    st.session_state.setdefault("farm_water", "Rainfed")
    st.session_state.setdefault("farm_area", 2.0)
    st.session_state.setdefault("farm_prev", [])
    st.session_state.setdefault("loc_mode", "District")

    left, right = st.columns([1.15, 1], gap="large")
    district = None
    district_rec = None
    lat = lon = None
    geo = None
    state = dname = None

    with left:
        # 1 ----- location
        ui.render(ui.step(1, "Where is your field?", "Choose a state and district, or drop a pin on the map."))
        mode = st.segmented_control("Method", ["District", "Pin on map"], key="loc_mode", label_visibility="collapsed")
        mode = mode or "District"
        if mode == "District":
            st.session_state.setdefault("farm_state", "Karnataka")
            c1, c2 = st.columns(2)
            state = c1.selectbox("State / UT", list_states(), key="farm_state")
            names = [d["district"] for d in districts_in_state(state)]
            if st.session_state.get("farm_district") not in names:
                st.session_state["farm_district"] = names[0]
            dname = c2.selectbox("District", names, key="farm_district")
            district_rec = get_india_district(state, dname)
            district = district_rec["label"]
            note = "Districts follow Census 2011 boundaries; newer districts are not listed."
            if state == "Andhra Pradesh":
                note += " Telangana's districts appear here because Telangana was part of Andhra Pradesh in 2011."
            st.caption(note)
            if district_rec["validated"]:
                ui.note("KAIRO's crop information was tested in this district.", "good")
            else:
                ui.note(OUTSIDE_SHORT, "caution")
        else:
            c1, c2 = st.columns(2)
            lat = c1.number_input("Latitude", -90.0, 90.0, format="%.4f", key="farm_lat")
            lon = c2.number_input("Longitude", -180.0, 180.0, format="%.4f", key="farm_lon")
            geo = svc.nearest_grid_point(lat, lon, _grid_points())
            near = svc.nearest_district(lat, lon)
            if geo["within_coverage"]:
                ui.note(f"Using NASA weather data for the nearest area, {geo['distance_km']} km from your pin.", "good")
                if near["within_coverage"]:
                    district = near["district"]
                    ui.note(f"Closest tested district: {near['district']} ({near['distance_km']} km away).")
                else:
                    district = f"Pin {lat:.2f}°N, {lon:.2f}°E"
                    ui.note(OUTSIDE_SHORT, "caution")
            else:
                ui.note(
                    f"This point is {geo['distance_km']} km from the nearest NASA weather area, so it is outside the "
                    "data KAIRO has for India. Move the pin onto India.",
                    "caution",
                )
        st.slider("Field size (hectares)", 0.5, 100.0, step=0.5, key="farm_area")

        # 2 ----- soil
        ui.render(ui.step(2, "Select your soil type", "Not sure? Choose “Not sure” and KAIRO will leave soil out when ranking."))
        soil_label = st.pills("Soil type", SOIL_LABELS + ["Not sure"], selection_mode="single", key="farm_soil")

        # 3 ----- water
        ui.render(ui.step(3, "How is this field irrigated?", "Rainfed means the crop depends on rain only."))
        water_label = st.segmented_control("Water source", WATER_SOURCES, key="farm_water")

        # 4 ----- previous crops
        ui.render(ui.step(4, "What did you grow previously?", "Optional. It helps avoid planting the same crop family twice."))
        previous = st.pills(
            "Previous crops",
            [c["crop_name"] for c in load_crop_database()],
            selection_mode="multi", key="farm_prev",
        )

        st.write("")
        submitted = st.button("Get recommendation", type="primary", key="generate")

    with right:
        if mode == "District":
            ui.render('<div class="page-sub" style="margin:.2rem 0 .4rem">Your field on the map</div>')
            dlat, dlon = district_rec["latitude"], district_rec["longitude"]
            gid = _grid_id_for(dlat, dlon)
            gpt = None
            if gid:
                row = _grid_points().set_index("grid_id").loc[gid]
                gpt = (float(row["latitude"]), float(row["longitude"]))
            preview = build_map(
                district_rec["district"] if district_rec["validated"] else None,
                (dlat, dlon), _summary(), grid_link=gpt, center=(dlat, dlon), zoom=8,
            )
            st_folium(preview, height=430, use_container_width=True, returned_objects=[], key=f"farm_map_district_{state}_{dname}")
        else:
            ui.render('<div class="page-sub" style="margin:.2rem 0 .4rem">Click the map to place your field</div>')
            clicked = st_folium(
                build_map(
                    district if geo and geo["within_coverage"] and district in DISTRICT_NAMES else None,
                    (lat, lon), _summary(), grid_points=_grid_points(),
                    grid_link=(geo["latitude"], geo["longitude"]) if geo and geo["within_coverage"] else None,
                    india_view=True,
                ),
                height=430, use_container_width=True, returned_objects=["last_clicked"], key="farm_map_pin",
            )
            last = (clicked or {}).get("last_clicked")
            if last and (round(last["lat"], 4), round(last["lng"], 4)) != (round(lat, 4), round(lon, 4)):
                st.session_state["_map_click"] = (round(last["lat"], 4), round(last["lng"], 4))
                st.rerun()

    _footer()

    if submitted:
        if district is None:
            st.error("Choose a state and district, or drop a pin inside India.")
            return
        soil_label = soil_label or "Not sure"
        water_label = water_label or "Rainfed"
        profile = {
            "district": district,
            "soil_type": soil_id_from_label(soil_label),
            "soil_label": soil_label,
            "water_availability": water_availability_from_source(water_label),
            "water_label": water_label,
            "area_ha": st.session_state["farm_area"],
            "previous_crops": ", ".join(previous) if previous else None,
            "latitude": district_rec["latitude"] if district_rec else lat,
            "longitude": district_rec["longitude"] if district_rec else lon,
            "state": district_rec["state"] if district_rec else None,
            "grid_id": (
                _grid_id_for(district_rec["latitude"], district_rec["longitude"]) if district_rec
                else (geo["grid_id"] if geo and geo["within_coverage"] else None)
            ),
        }
        try:
            plan = svc.build_plan(profile, _grid_summary() if profile["grid_id"] else _summary())
        except (ValueError, FileNotFoundError) as error:
            st.error(f"Could not build a plan: {error}")
            return
        st.session_state.profile = profile
        st.session_state.plan = plan
        try:
            storage.save_plan(profile, plan)
        except (OSError, sqlite3.Error):
            pass  # the plan still shows; it just is not remembered
        st.session_state["_nav"] = "Recommendations"
        st.rerun()


# ----------------------------------------------------------------- Recommendation
def _plan_csv(plan: dict) -> pd.DataFrame:
    rows = []
    for rot in plan["rotations"]:
        for c in rot["crop_sequence"]:
            rows.append({
                "district": plan["district"], "rotation_rank": rot["rank"],
                "rotation_score": rot["overall_rotation_score"], "season": c["season"],
                "crop": c["crop_name"], "crop_score": c["suitability_score"],
                "source_verification": c.get("source_verification"),
            })
    return pd.DataFrame(rows)


def _radar(rot: dict) -> go.Figure:
    totals: dict[str, list[float]] = {}
    for crop in rot["crop_sequence"]:
        for name, value in crop["suitability_details"].get("component_scores", {}).items():
            if value is not None:
                totals.setdefault(name, []).append(value)
    names = list(totals)
    values = [sum(v) / len(v) for v in totals.values()]
    fig = go.Figure(go.Scatterpolar(
        r=values + values[:1], theta=[n.title() for n in names] + [names[0].title()],
        fill="toself", line=dict(color=ACCENT, width=2), fillcolor="rgba(31,77,43,.18)",
    ))
    fig.update_layout(**plot_layout(height=340, showlegend=False), polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 100], gridcolor="#E3D9C0", tickfont=dict(size=9)),
        angularaxis=dict(gridcolor="#E3D9C0"),
    ))
    return fig


def _how_calculated(plan: dict) -> None:
    with st.expander("How this was calculated"):
        st.markdown(
            "KAIRO compares each crop's needs (temperature, rainfall, soil, water and season) with the weather "
            "records for your location and the answers you gave. Crops are combined into two-season plans, "
            "with a small bonus for including a legume and a penalty for repeating a crop family."
        )
        t_scores, t_compare, t_method = st.tabs(["Score details", "Compare options", "Method and limits"])
        with t_scores:
            for rot, sus in zip(plan["rotations"], plan["sustainability"]):
                st.markdown(f"**Option {rot['rank']}: {rotation_label(rot)}**  ·  fit score {rot['overall_rotation_score']:.0f} of 100")
                cols = st.columns(len(rot["crop_sequence"]))
                for col, crop in zip(cols, rot["crop_sequence"]):
                    details = crop.get("suitability_details", {})
                    with col:
                        st.markdown(f"{crop['crop_name']} · {crop['season'].title()}")
                        st.markdown(ui.score_bars(details.get("component_scores", {})), unsafe_allow_html=True)
                        for line in details.get("explanations", []):
                            st.caption(f"• {line}")
                        for warning in crop.get("source_warnings", []):
                            st.caption(f"Data note: {warning}")
                        if crop.get("source_urls"):
                            st.caption(f"Sources: {crop['source_urls']}")
                for line in rot.get("explanations", []):
                    st.caption(f"Plan: {line}")
                st.divider()
        with t_compare:
            labels = [f"Option {r['rank']}: {rotation_label(r)}" for r in plan["rotations"]]
            fig = go.Figure()
            fig.add_bar(y=labels, x=[r["overall_rotation_score"] for r in plan["rotations"]], name="Fit score",
                        orientation="h", marker_color=ACCENT)
            fig.add_bar(y=labels, x=[r["average_crop_suitability"] for r in plan["rotations"]], name="Average crop fit",
                        orientation="h", marker_color=ACCENT_3)
            fig.update_layout(**plot_layout(height=130 + 80 * len(labels), barmode="group", xaxis=dict(range=[0, 100])))
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, width="stretch")
            pick = st.segmented_control("Component profile of", [f"#{r['rank']}" for r in plan["rotations"]], default="#1", key="radar_pick")
            idx = int((pick or "#1").lstrip("#")) - 1
            st.plotly_chart(_radar(plan["rotations"][min(idx, len(plan["rotations"]) - 1)]), width="stretch")
        with t_method:
            st.markdown("How much each part counts toward a crop's score (%):")
            ui.render(ui.score_bars({k: v for k, v in WEIGHTS.items()}))
            st.caption("These weights are prototype design choices, not calibrated agronomic values.")
            st.markdown("**Limits to keep in mind**")
            seen = set()
            for rot in plan["rotations"]:
                for line in rot.get("limitations", []):
                    if line not in seen:
                        seen.add(line)
                        st.caption(f"• {line}")
            st.caption(f"• {svc.DATA_NATURE}")
            st.caption(f"• {INDICATOR_NOTE}")


def page_recommendations() -> None:
    plan = _need_plan()
    if not plan:
        return
    profile = st.session_state.profile
    ui.render(ui.page_header("Recommended for this season", f"For your field in {plan['district']}, based on NASA weather records, your soil and your water."))
    for warning in plan["warnings"]:
        ui.note(_friendly(warning), "caution")

    if not plan["rotations"]:
        ui.empty_state("No plan fits these answers", "Try a different soil type or water source.")
        _footer()
        return

    cond = {c["season"]: c["environmental_data"] for c in plan["conditions"]}
    best, sus = plan["rotations"][0], plan["sustainability"][0]
    ui.render(ui.reco_card(
        label="Best option",
        title=rotation_label(best),
        seasons=season_label(best),
        fit=f"Fit score {best['overall_rotation_score']:.0f} out of 100",
        reasons=fit_reasons(best, sus),
        caution=main_caution(best, cond, profile),
        check=CHECK_LOCALLY,
    ))
    flagged = sorted({c["crop_name"] for c in best["crop_sequence"] if c.get("source_warnings")})
    if flagged:
        ui.note(f"Reference data for {', '.join(flagged)} still needs verification. Details are under “How this was calculated”.")

    others = list(zip(plan["rotations"][1:3], plan["sustainability"][1:3]))
    if others:
        ui.render('<h3 style="margin:1.6rem 0 .5rem">Two alternatives</h3>' if len(others) == 2 else '<h3 style="margin:1.6rem 0 .5rem">Alternative</h3>')
        cols = st.columns(len(others))
        for col, (rot, _) in zip(cols, others):
            col.markdown(
                ui.alt_card(
                    f"Option {rot['rank']}", rotation_label(rot),
                    f"{season_label(rot)} · fit score {rot['overall_rotation_score']:.0f}",
                    main_caution(rot, cond, profile),
                ),
                unsafe_allow_html=True,
            )

    ui.render('<h3 style="margin:1.8rem 0 .3rem">The weather behind this advice</h3>')
    items = []
    for season, env in cond.items():
        years = env.get("season_years_used") or []
        basis = f"average of {len(years)} seasons, {min(years)}–{max(years)}" if years else "NASA POWER average"
        items.append((f"{season.title()} season", f"{env['temperature_c']:.1f} °C · {env['rainfall_mm']:.0f} mm", basis))
    ui.render(ui.facts(items))

    _how_calculated(plan)
    st.write("")
    st.download_button(
        "Download as CSV",
        _plan_csv(plan).to_csv(index=False).encode("utf-8"),
        file_name=f"kairo_{_slug(plan['district'])}_{date.today().isoformat()}.csv",
        mime="text/csv",
    )
    _saved_plans_panel()
    _footer()


# ----------------------------------------------------------------- Weather
def page_climate() -> None:
    ui.render(ui.page_header("Weather records", "NASA estimates for the area around each district, 2024–2025."))
    plan = st.session_state.plan
    default = plan["district"] if plan and plan["district"] in DISTRICT_NAMES else DISTRICT_NAMES[0]
    st.session_state.setdefault("climate_district", default)
    district = st.pills("District", DISTRICT_NAMES, selection_mode="single", key="climate_district") or DISTRICT_NAMES[0]

    df = _daily()
    df = df[df["location"] == district].sort_values("date")
    if df.empty:
        ui.empty_state("No stored data", "There is no stored NASA data for this district.")
        return
    monthly = df.set_index("date").resample("MS").agg({"temperature_c": "mean", "rainfall_mm": "sum"}).reset_index()

    ui.render(ui.facts([
        ("Average temperature", f"{df['temperature_c'].mean():.1f} °C", "daily mean, 2024–2025"),
        ("Total rainfall", f"{df['rainfall_mm'].sum():.0f} mm", "sum of daily values"),
        ("Warmest month", f"{monthly.loc[monthly['temperature_c'].idxmax(), 'date']:%b %Y}", f"{monthly['temperature_c'].max():.1f} °C average"),
        ("Wettest month", f"{monthly.loc[monthly['rainfall_mm'].idxmax(), 'date']:%b %Y}", f"{monthly['rainfall_mm'].max():.0f} mm"),
    ]))

    t1, t2, t3 = st.tabs(["Month by month", "By season", "About this data"])
    with t1:
        fig = go.Figure()
        fig.add_bar(x=monthly["date"], y=monthly["rainfall_mm"], name="Rainfall (mm)", marker_color=ACCENT_2, opacity=.8)
        fig.add_scatter(x=monthly["date"], y=monthly["temperature_c"], name="Temperature (°C)", yaxis="y2",
                        line=dict(color=ACCENT_3, width=3, shape="spline"), mode="lines+markers")
        fig.update_layout(**plot_layout(height=400, yaxis=dict(title="Rainfall (mm / month)")),
                          yaxis2=dict(title="Temperature (°C)", overlaying="y", side="right", showgrid=False))
        st.plotly_chart(fig, width="stretch")
    with t2:
        seas = _summary()
        seas = seas[seas["location"] == district].sort_values(["season_year", "season"])
        fig = go.Figure()
        for year, color in zip(sorted(seas["season_year"].unique()), [ACCENT, ACCENT_3, ACCENT_2]):
            part = seas[seas["season_year"] == year]
            fig.add_bar(x=part["season"].str.title(), y=part["rainfall_mm"], name=str(year), marker_color=color)
        fig.update_layout(**plot_layout(height=340, barmode="group", yaxis=dict(title="Season rainfall (mm)")))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(
            seas[["season", "season_year", "days_available", "complete", "temperature_c", "rainfall_mm"]],
            hide_index=True, width="stretch",
        )
        st.caption("Incomplete seasons are not used for recommendations.")
    with t3:
        st.markdown(svc.DATA_NATURE)
        meta = svc.load_provenance(district)
        if meta:
            st.markdown(
                f"- **Source:** {meta.get('source', 'NASA POWER')} daily point data (community AG, UTC)\n"
                f"- **Period:** {meta.get('start_date', 'not recorded')} to {meta.get('end_date', 'not recorded')}\n"
                f"- **Retrieved:** {meta.get('retrieved_at', 'not recorded')}\n"
                f"- **Grid point:** {meta.get('latitude')}, {meta.get('longitude')}"
            )
        else:
            st.write("No provenance record found for this district.")
    _footer()


# ----------------------------------------------------------------- Map
def page_map() -> None:
    ui.render(ui.page_header("Where KAIRO has weather data", "Green markers are the five districts KAIRO was tested in. Grey dots are the NASA weather grid across India."))
    plan = st.session_state.plan
    profile = st.session_state.profile
    point = (profile["latitude"], profile["longitude"]) if profile and profile.get("latitude") is not None else None
    show_grid = st.toggle("Show the NASA grid for all of India", value=True, key="show_grid")
    st_folium(
        build_map(
            plan["district"] if plan and plan["district"] in DISTRICT_NAMES else None, point, _summary(),
            grid_points=_grid_points() if show_grid else None, india_view=show_grid,
        ),
        height=500, use_container_width=True, returned_objects=[], key=f"district_map_{show_grid}",
    )
    summary = _summary()
    summary = summary[summary["complete"] == True]  # noqa: E712
    cards = []
    for name in DISTRICT_NAMES:
        rows = summary[summary["location"] == name]
        lines = []
        for season in ("kharif", "rabi"):
            s = rows[rows["season"] == season]
            if not s.empty:
                lines.append(f"{season.title()}: {s['temperature_c'].mean():.1f} °C, {s['rainfall_mm'].mean():.0f} mm")
        selected = plan and plan["district"] == name
        cards.append(f'<div class="panel"><h4>{escape(name)}{" (your field)" if selected else ""}</h4><p>{escape("  ·  ".join(lines))}</p></div>')
    ui.render(ui.grid(cards, 200))
    ui.note("Markers are district reference points, not field boundaries.")
    _footer()


# ----------------------------------------------------------------- Rotation health
def page_sustainability() -> None:
    plan = _need_plan()
    if not plan:
        return
    ui.render(ui.page_header("Rotation health", "How varied each option is across seasons and crop families."))
    if not plan["rotations"]:
        ui.empty_state("Nothing to show", "No plan was generated for these answers.")
        return
    for rot, sus in zip(plan["rotations"], plan["sustainability"]):
        if not sus.get("available"):
            continue
        items = "".join(f"<li><b>{escape(i['name'])}:</b> {escape(i['detail'])}</li>" for i in sus["indicators"])
        ui.render(
            f'<div class="panel" style="margin-bottom:.9rem"><div class="eyebrow" style="color:#5F5A48">Option {rot["rank"]}</div>'
            f'<h4 style="font-size:1.25rem;margin:.2rem 0">{escape(rotation_label(rot))}</h4>'
            f'<p>Variety indicator: {sus["indicator_score"]} out of 100</p>'
            f'<ul style="margin:.5rem 0 0 1.1rem;color:#2A2A22">{items}</ul></div>'
        )
    ui.note(INDICATOR_NOTE)
    _footer()


# ----------------------------------------------------------------- Summary (advisor)
def page_advisor() -> None:
    plan = _need_plan()
    if not plan:
        return
    ui.render(ui.page_header("Plain-language summary", "Written from KAIRO's own results, so it only says what the numbers support."))
    ui.render(f'<div class="bubble">{escape(advisor.template_explanation(plan))}</div>')
    st.caption("This summary works offline and does not send your data anywhere.")

    st.markdown("##### Ask for an AI explanation (optional)")
    if not advisor.ai_available():
        ui.note(
            "AI explanations are off. Add a free provider key (GROQ_API_KEY, GEMINI_API_KEY or "
            "OPENROUTER_API_KEY) to .env and restart KAIRO. The summary above always works."
        )
    else:
        language = st.segmented_control("Language", ["English", "Kannada", "Hindi"], default="English", key="ai_lang") or "English"
        if st.button("Explain with AI", type="primary", key="ask_ai"):
            with st.spinner("Preparing the explanation…"):
                st.session_state["ai_result"] = advisor.ai_explanation(plan, language=language)
    result = st.session_state.get("ai_result") if advisor.ai_available() else None
    if result:
        st.write("")
        if result["source"] == "ai":
            ui.note(f"AI-written ({advisor.active_provider_label()}). Numbers were checked against KAIRO's results.", "good")
        else:
            ui.note(f"Showing the standard summary instead. {result['fallback_reason']}", "caution")
        ui.render(f'<div class="bubble">{escape(result["text"])}</div>')
    _footer()


# ----------------------------------------------------------------- About
def page_about() -> None:
    ui.render(ui.page_header("About KAIRO", "Crop planning from NASA weather records, for farmers and local agronomists."))
    st.markdown(
        "**What it does.** You describe a field; KAIRO compares the weather of past seasons at that place with what each "
        "crop needs, then suggests a two-season plan and shows its reasoning.\n\n"
        "**Where the weather comes from.** NASA POWER daily data on a grid about 56 km across, covering India. "
        "It is modelled from satellites and reanalysis, so it describes the area, not your field.\n\n"
        "**Where it was tested.** Crop information was checked in five Karnataka districts: Ballari, Shivamogga, "
        "Vijayapura, Belagavi and Dharwad. Elsewhere, treat results as a starting point."
    )
    st.markdown("##### Limits")
    st.markdown(
        "- Season windows (kharif Jun–Oct, rabi Nov–Mar, summer Apr–May) are assumptions.\n"
        "- The crop list is short (six crops) and some figures are still being verified.\n"
        "- Scores use prototype weights; soil and water matching is simplified.\n"
        "- KAIRO makes no yield, water-saving or soil-restoration claims."
    )
    st.markdown("##### How KAIRO was built (use of AI)")
    st.markdown(
        "This project used AI tools. Anthropic's Claude (through Claude Code) helped the team write and review code, "
        "tests and documentation and draft the interface; the team directed the work and reviewed the results. "
        "An optional feature can send KAIRO's own computed results to a hosted language model to explain them in plain "
        "language. That text is accepted only if every number in it matches KAIRO's computed data. "
        "Crop reference data and all weather data come from the cited sources, not from AI."
    )
    ui.note(CHECK_LOCALLY, "good")
    _footer()


# ----------------------------------------------------------------- main
st.session_state.setdefault("profile", None)
st.session_state.setdefault("plan", None)
_PAGE = top_bar()
{
    "Home": page_home,
    "Farm": page_farm,
    "Recommendations": page_recommendations,
    "Climate": page_climate,
    "Map": page_map,
    "Sustainability": page_sustainability,
    "Advisor": page_advisor,
    "About": page_about,
}[_PAGE]()
