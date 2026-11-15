"""KAIRO - NASA-data crop rotation decision support for Karnataka farms.

Run:  py -3.11 -m streamlit run app.py
UI only: all data handling and scoring lives in modules/.
"""

from __future__ import annotations

from datetime import date
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from streamlit_folium import st_folium

from config.districts import DISTRICTS
from config.soils import (
    SOIL_TYPES,
    WATER_SOURCES,
    soil_id_from_label,
    water_availability_from_source,
)
from dashboard import components as ui
from dashboard.map_view import build_map
from dashboard.theme import ACCENT, ACCENT_2, ACCENT_3, inject_theme, plot_layout
from modules import advisor
from modules import kairo_service as svc
from modules.crop_database import load_crop_database
from modules.crop_suitability_v2 import WEIGHTS
from modules.sustainability import INDICATOR_NOTE

load_dotenv()  # reads .env (AI provider keys) if present

st.set_page_config(
    page_title="KAIRO",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()

DISTRICT_NAMES = [d["name"] for d in DISTRICTS]
SOIL_LABELS = [label for _, label in SOIL_TYPES]
PAGES = ["Home", "Farm", "Recommendations", "Climate", "Map", "Sustainability", "Advisor", "About"]
NAV_ICONS = {
    "Home": ":material/home:",
    "Farm": ":material/agriculture:",
    "Recommendations": ":material/auto_awesome:",
    "Climate": ":material/thermostat:",
    "Map": ":material/map:",
    "Sustainability": ":material/eco:",
    "Advisor": ":material/chat:",
    "About": ":material/info:",
}


# ----------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def _daily() -> pd.DataFrame:
    return pd.read_csv(svc.DATA_DIR / "daily_2024-2025.csv", parse_dates=["date"])


@st.cache_data(show_spinner=False)
def _summary() -> pd.DataFrame:
    return svc.load_seasonal_summary()


def _goto(page: str) -> None:
    st.session_state["_nav"] = page


def _need_plan() -> dict | None:
    plan = st.session_state.plan
    if not plan:
        ui.empty_state("🌾", "No farm saved yet", "Describe your farm first and KAIRO will build your plan.")
        st.button("Set up my farm", type="primary", on_click=_goto, args=("Farm",), key=f"need_{st.session_state.get('page')}")
    return plan


def _footer() -> None:
    ui.render(
        '<div class="footer">KAIRO · NASA POWER data is gridded and modelled · '
        "Decision support, not agronomic advice</div>"
    )


# ----------------------------------------------------------------- chrome
def top_bar() -> str:
    # Pending navigation and "never deselect" guard run before the widget exists.
    if "_nav" in st.session_state:
        st.session_state["page"] = st.session_state.pop("_nav")
    if st.session_state.get("page") is None:
        st.session_state["page"] = st.session_state.get("_last_page", "Home")

    brand, chip = st.columns([1, 1], vertical_alignment="center")
    brand.markdown(ui.topbar_brand(), unsafe_allow_html=True)
    chip.markdown(ui.farm_chip(st.session_state.profile), unsafe_allow_html=True)
    page = st.segmented_control(
        "Navigate", PAGES, key="page", label_visibility="collapsed",
        format_func=lambda p: f"{NAV_ICONS[p]} {p}",
    )
    page = page or st.session_state.get("_last_page", "Home")
    st.session_state["_last_page"] = page
    return page


# ----------------------------------------------------------------- Home
def page_home() -> None:
    ui.render(
        '<div class="hero"><span class="eyebrow">● NASA Space Apps Challenge 2026</span>'
        "<h1>Choose your next crop with <em>evidence</em>, not guesswork.</h1>"
        "<p>KAIRO turns NASA climate data for your district into ranked multi-season "
        "crop rotations, and explains every score.</p></div>"
    )
    c1, c2, _ = st.columns([3, 2.4, 4])
    c1.button("Start with your farm", type="primary", on_click=_goto, args=("Farm",), key="cta_farm", width="stretch")
    c2.button("Explore the map", on_click=_goto, args=("Map",), key="cta_map", width="stretch")
    st.write("")

    n_crops = len(load_crop_database())
    stats = [
        ("📍", "Districts", "5", "Ballari · Shivamogga · Vijayapura · Belagavi · Dharwad"),
        ("🛰️", "NASA POWER", "2024–25", "Daily temperature, rain, humidity, sunshine"),
        ("🌾", "Crops", str(n_crops), "Sourced; unverified rows are flagged"),
        ("🔁", "Seasons", "Kharif + Rabi", "Rotation scored across both"),
    ]
    ui.render(ui.grid([ui.stat(*s) for s in stats], four=True))

    st.write("")
    ui.render(ui.section("How it works", "Three steps to a plan"))
    steps = [
        ("Describe your farm", "Pick a district or drop a pin on the map, then set soil, water source and past crops."),
        ("We read NASA data", "KAIRO averages complete kharif and rabi seasons from NASA POWER for your location."),
        ("Get ranked rotations", "See the best crop sequences with score breakdowns, sources and honest limitations."),
    ]
    ui.render(ui.grid([ui.step_card(i, t, x) for i, (t, x) in enumerate(steps, start=1)], three=True))

    st.write("")
    ui.banner(svc.DISCLAIMER, "info")
    _footer()


# ----------------------------------------------------------------- Farm
def page_farm() -> None:
    ui.render(ui.section("Step 1", "Tell us about your farm", "Everything here shapes your recommendations. You can change it any time."))

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

    left, right = st.columns([1.05, 1], gap="large")
    district = None
    lat = lon = None
    geo = None

    with left:
        with st.container(border=True):
            st.markdown("##### :material/location_on: Location")
            mode = st.segmented_control("Method", ["District", "Pin on map"], key="loc_mode", label_visibility="collapsed")
            mode = mode or "District"
            if mode == "District":
                district = st.pills("District", DISTRICT_NAMES, selection_mode="single", key="farm_district")
            else:
                c1, c2 = st.columns(2)
                lat = c1.number_input("Latitude", -90.0, 90.0, format="%.4f", key="farm_lat")
                lon = c2.number_input("Longitude", -180.0, 180.0, format="%.4f", key="farm_lon")
                geo = svc.nearest_district(lat, lon)
                if geo["within_coverage"]:
                    ui.banner(
                        f"Nearest supported district: <b>{geo['district']}</b> ({geo['distance_km']} km away). {geo['note']}",
                        "ok",
                    )
                    district = geo["district"]
                else:
                    ui.banner(
                        f"This point is {geo['distance_km']} km from the nearest supported district "
                        f"({geo['district']}). KAIRO only has data for five Karnataka districts.",
                    )

        with st.container(border=True):
            st.markdown("##### :material/landscape: Soil and water")
            soil_label = st.pills("Soil type", SOIL_LABELS + ["Not sure"], selection_mode="single", key="farm_soil")
            water_label = st.segmented_control("Water source", WATER_SOURCES, key="farm_water")
            st.slider("Farm size (hectares)", 0.5, 100.0, step=0.5, key="farm_area")

        with st.container(border=True):
            st.markdown("##### :material/history: Previous crops")
            previous = st.pills(
                "What did you grow recently? (optional)",
                [c["crop_name"] for c in load_crop_database()],
                selection_mode="multi", key="farm_prev",
            )

    with right:
        with st.container(border=True):
            if mode == "District":
                st.markdown("##### :material/map: Selected district")
                preview = build_map(district, None, _summary())
                st_folium(preview, height=430, use_container_width=True, returned_objects=[], key="farm_map_district")
            else:
                st.markdown("##### :material/touch_app: Click the map to place your farm")
                clicked = st_folium(
                    build_map(geo["district"] if geo and geo["within_coverage"] else None, (lat, lon), _summary()),
                    height=430, use_container_width=True, returned_objects=["last_clicked"], key="farm_map_pin",
                )
                last = (clicked or {}).get("last_clicked")
                if last and (round(last["lat"], 4), round(last["lng"], 4)) != (round(lat, 4), round(lon, 4)):
                    st.session_state["_map_click"] = (round(last["lat"], 4), round(last["lng"], 4))
                    st.rerun()

    st.write("")
    if st.button("Generate recommendations", type="primary", key="generate"):
        if district is None:
            st.error("Choose a district, or drop a pin inside the supported area.")
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
            "latitude": lat,
            "longitude": lon,
        }
        try:
            plan = svc.build_plan(profile, _summary())
        except (ValueError, FileNotFoundError) as error:
            st.error(f"Could not build a plan: {error}")
            return
        st.session_state.profile = profile
        st.session_state.plan = plan
        st.session_state["_nav"] = "Recommendations"
        st.rerun()


# ----------------------------------------------------------------- Recommendations
def _rotation_label(rot: dict) -> str:
    return " → ".join(c["crop_name"] for c in rot["crop_sequence"])


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


def _rotation_card(rot: dict, sus: dict) -> None:
    with st.container(border=True):
        left, right = st.columns([1, 6], vertical_alignment="center")
        left.markdown(ui.ring(rot["overall_rotation_score"], "match"), unsafe_allow_html=True)
        flagged = sorted({c["crop_name"] for c in rot["crop_sequence"] if c.get("source_warnings")})
        chips = [("Best match", "green")] if rot["rank"] == 1 else []
        if sus.get("available"):
            chips.append((f"Sustainability {sus['indicator_score']}", "cyan"))
            chips.append(("Includes legume", "green") if sus["legume_count"] else ("No legume", "gray"))
        if flagged:
            chips.append((f"Needs verification: {', '.join(flagged)}", "amber"))
        right.markdown(
            f'<div class="kicker">Rotation #{rot["rank"]}</div>{ui.sequence(rot["crop_sequence"])}{ui.tags(chips)}',
            unsafe_allow_html=True,
        )
        with st.expander("Why this score?"):
            cols = st.columns(len(rot["crop_sequence"]))
            for col, crop in zip(cols, rot["crop_sequence"]):
                details = crop.get("suitability_details", {})
                with col:
                    st.markdown(f"**{crop['crop_name']}** · {crop['season'].title()}")
                    st.markdown(ui.score_bars(details.get("component_scores", {})), unsafe_allow_html=True)
                    for line in details.get("explanations", []):
                        st.caption(f"• {line}")
                    for warning in crop.get("source_warnings", []):
                        st.caption(f"⚠ {warning}")
                    if crop.get("source_urls"):
                        st.caption(f"Sources: {crop['source_urls']}")
            for note in rot.get("explanations", []):
                st.caption(f"Rotation: {note}")
            for limit in rot.get("limitations", []):
                st.caption(f"Limitation: {limit}")
    st.write("")


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
        fill="toself", line=dict(color=ACCENT, width=3), fillcolor="rgba(52,211,153,.22)",
    ))
    fig.update_layout(**plot_layout(height=360, showlegend=False), polar=dict(
        bgcolor="rgba(0,0,0,0)",
        radialaxis=dict(range=[0, 100], gridcolor="rgba(148,163,184,.18)", tickfont=dict(size=9)),
        angularaxis=dict(gridcolor="rgba(148,163,184,.18)"),
    ))
    return fig


def page_recommendations() -> None:
    ui.render(ui.section("Your plan", "Recommended rotations", "Ranked by how well each crop sequence fits your climate, soil and water."))
    plan = _need_plan()
    if not plan:
        return
    for note in plan["warnings"]:
        ui.banner(note)

    cond = {c["season"]: c["environmental_data"] for c in plan["conditions"]}
    best = plan["rotations"][0]["overall_rotation_score"] if plan["rotations"] else None
    kpis = [
        '<div class="card" style="display:flex;gap:1rem;align-items:center">'
        f'{ui.ring(best, "best")}<div><div class="lbl" style="color:#8b9ab0;font-size:.72rem;text-transform:uppercase;letter-spacing:.1em">Top rotation</div>'
        f'<div style="font-weight:700;margin-top:2px">{plan["district"]}</div></div></div>'
    ]
    icons = {"kharif": "🌧️", "rabi": "🌤️", "summer": "☀️"}
    for season, env in cond.items():
        kpis.append(ui.stat(icons.get(season, "🌱"), f"{season.title()} climate", f"{env['temperature_c']:.1f} °C",
                            f"{env['rainfall_mm']:.0f} mm rain · NASA POWER avg"))
    ui.render(ui.grid(kpis, 230))

    if not plan["rotations"]:
        ui.empty_state("🔍", "No rotation met the requirements", "Try a different soil type or water source.")
        return

    tab_rank, tab_compare, tab_method = st.tabs(["Ranked rotations", "Compare", "How scoring works"])
    with tab_rank:
        for rot, sus in zip(plan["rotations"], plan["sustainability"]):
            _rotation_card(rot, sus)
        st.download_button(
            "Download recommendations (CSV)",
            _plan_csv(plan).to_csv(index=False).encode("utf-8"),
            file_name=f"kairo_{plan['district'].lower()}_{date.today().isoformat()}.csv",
            mime="text/csv",
        )
    with tab_compare:
        labels = [f"#{r['rank']} {_rotation_label(r)}" for r in plan["rotations"]]
        fig = go.Figure()
        fig.add_bar(y=labels, x=[r["overall_rotation_score"] for r in plan["rotations"]], name="Rotation score",
                    orientation="h", marker_color=ACCENT)
        fig.add_bar(y=labels, x=[r["average_crop_suitability"] for r in plan["rotations"]], name="Avg crop suitability",
                    orientation="h", marker_color=ACCENT_2)
        fig.update_layout(**plot_layout(height=130 + 90 * len(labels), barmode="group", xaxis=dict(range=[0, 100])))
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, width="stretch")
        pick = st.segmented_control("Component profile of", [f"#{r['rank']}" for r in plan["rotations"]], default="#1", key="radar_pick")
        idx = int((pick or "#1").lstrip("#")) - 1
        st.plotly_chart(_radar(plan["rotations"][min(idx, len(plan["rotations"]) - 1)]), width="stretch")
    with tab_method:
        st.markdown("Each crop is scored from five components, then combined into a rotation score. Weight of each component (%):")
        ui.render(ui.score_bars({k: v for k, v in WEIGHTS.items()}))
        st.caption(
            "Weights are prototype design choices, not calibrated agronomic values. "
            "Rotation scores add a bonus for legumes and a penalty for repeating a crop family."
        )
    ui.banner(plan["disclaimer"], "info")
    _footer()


# ----------------------------------------------------------------- Climate
def page_climate() -> None:
    ui.render(ui.section("NASA POWER", "Climate", svc.DATA_NATURE))
    plan = st.session_state.plan
    st.session_state.setdefault("climate_district", plan["district"] if plan else DISTRICT_NAMES[0])
    district = st.pills("District", DISTRICT_NAMES, selection_mode="single", key="climate_district") or DISTRICT_NAMES[0]

    df = _daily()
    df = df[df["location"] == district].sort_values("date")
    if df.empty:
        ui.empty_state("🛰️", "No stored data", "There is no stored NASA data for this district.")
        return
    monthly = df.set_index("date").resample("MS").agg({"temperature_c": "mean", "rainfall_mm": "sum"}).reset_index()

    cards = [
        ("🌡️", "Mean temperature", f"{df['temperature_c'].mean():.1f} °C", "daily mean, 2024–2025"),
        ("🌧️", "Total rainfall", f"{df['rainfall_mm'].sum():.0f} mm", "sum of daily values"),
        ("🔥", "Warmest month", f"{monthly.loc[monthly['temperature_c'].idxmax(), 'date']:%b %Y}", f"{monthly['temperature_c'].max():.1f} °C avg"),
        ("💧", "Wettest month", f"{monthly.loc[monthly['rainfall_mm'].idxmax(), 'date']:%b %Y}", f"{monthly['rainfall_mm'].max():.0f} mm"),
    ]
    ui.render(ui.grid([ui.stat(*c) for c in cards], four=True))
    st.write("")

    t1, t2, t3 = st.tabs(["Trends", "Seasons", "Source"])
    with t1:
        fig = go.Figure()
        fig.add_bar(x=monthly["date"], y=monthly["rainfall_mm"], name="Rainfall (mm)", marker_color=ACCENT_2, opacity=.75)
        fig.add_scatter(x=monthly["date"], y=monthly["temperature_c"], name="Temperature (°C)", yaxis="y2",
                        line=dict(color=ACCENT, width=3, shape="spline"), mode="lines+markers")
        fig.update_layout(**plot_layout(height=420, yaxis=dict(title="Rainfall (mm / month)")),
                          yaxis2=dict(title="Temperature (°C)", overlaying="y", side="right", showgrid=False))
        st.plotly_chart(fig, width="stretch")
    with t2:
        seas = _summary()
        seas = seas[seas["location"] == district].sort_values(["season_year", "season"])
        fig = go.Figure()
        for year, color in zip(sorted(seas["season_year"].unique()), [ACCENT, ACCENT_3, ACCENT_2]):
            part = seas[seas["season_year"] == year]
            fig.add_bar(x=part["season"].str.title(), y=part["rainfall_mm"], name=str(year), marker_color=color)
        fig.update_layout(**plot_layout(height=360, barmode="group", yaxis=dict(title="Season rainfall (mm)")))
        st.plotly_chart(fig, width="stretch")
        st.dataframe(
            seas[["season", "season_year", "days_available", "complete", "temperature_c", "rainfall_mm"]],
            hide_index=True, width="stretch",
        )
        st.caption("Incomplete seasons are not used for recommendations.")
    with t3:
        meta = svc.load_provenance(district)
        if meta:
            c1, c2 = st.columns(2)
            c1.markdown(ui.info_card("🛰️", "Source", f"{meta.get('source', 'NASA POWER')} daily point API (community AG, UTC)"), unsafe_allow_html=True)
            c2.markdown(ui.info_card("📅", "Period", f"{meta.get('start_date', 'not recorded')} to {meta.get('end_date', 'not recorded')} · retrieved {meta.get('retrieved_at', 'not recorded')}"), unsafe_allow_html=True)
            st.caption(f"Grid point: {meta.get('latitude')}, {meta.get('longitude')}")
        else:
            st.write("No provenance record found for this district.")
    _footer()


# ----------------------------------------------------------------- Map
def page_map() -> None:
    ui.render(ui.section("Geography", "District map", "Click a marker for the latest complete NASA POWER seasonal averages."))
    plan = st.session_state.plan
    profile = st.session_state.profile
    point = (profile["latitude"], profile["longitude"]) if profile and profile.get("latitude") is not None else None
    with st.container(border=True):
        st_folium(
            build_map(plan["district"] if plan else None, point, _summary()),
            height=520, use_container_width=True, returned_objects=[], key="district_map",
        )
    st.write("")
    summary = _summary()
    summary = summary[summary["complete"] == True]  # noqa: E712
    district_cards = []
    for name in DISTRICT_NAMES:
        rows = summary[summary["location"] == name]
        lines = []
        for season in ("kharif", "rabi"):
            s = rows[rows["season"] == season]
            if not s.empty:
                lines.append(f"{season.title()}: {s['temperature_c'].mean():.1f} °C · {s['rainfall_mm'].mean():.0f} mm")
        selected = plan and plan["district"] == name
        district_cards.append(ui.info_card("📍", name + (" ✓" if selected else ""), " | ".join(lines)))
    ui.render(ui.grid(district_cards, 200))
    ui.banner("Markers are district reference points, not farm boundaries. " + svc.DATA_NATURE, "info")
    _footer()


# ----------------------------------------------------------------- Sustainability
def page_sustainability() -> None:
    ui.render(ui.section("Rotation health", "Sustainability indicators", "Structure-based indicators that compare options. They are not measured water, yield or soil results."))
    plan = _need_plan()
    if not plan:
        return
    if not plan["rotations"]:
        ui.empty_state("🔍", "Nothing to evaluate", "No rotations were generated for this farm.")
        return
    tone = {"good": "green", "warning": "amber", "none": "gray", "moderate": "cyan", "info": "violet"}
    for rot, sus in zip(plan["rotations"], plan["sustainability"]):
        if not sus.get("available"):
            continue
        with st.container(border=True):
            c1, c2 = st.columns([1, 6], vertical_alignment="center")
            c1.markdown(ui.ring(sus["indicator_score"], "indicator"), unsafe_allow_html=True)
            rows = "".join(
                f'<div style="margin:.35rem 0">{ui.tag(i["name"], tone.get(i["status"], "gray"))}'
                f'<span style="color:#aab8cb;font-size:.9rem">{i["detail"]}</span></div>'
                for i in sus["indicators"]
            )
            c2.markdown(f'<div class="kicker">Rotation #{rot["rank"]}</div><div style="font-weight:700;font-size:1.1rem;margin:.2rem 0 .4rem">{_rotation_label(rot)}</div>{rows}', unsafe_allow_html=True)
    ui.banner(INDICATOR_NOTE, "info")
    _footer()


# ----------------------------------------------------------------- Advisor
def page_advisor() -> None:
    ui.render(ui.section("Plain language", "KAIRO Advisor", "A readable summary of your plan. Built only from KAIRO's computed results."))
    plan = _need_plan()
    if not plan:
        return
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        st.markdown("##### Summary")
        ui.render(f'<div class="bubble">{escape(advisor.template_explanation(plan))}</div>')
        st.caption("Works offline. No data leaves your computer for this summary.")
    with right:
        with st.container(border=True):
            st.markdown("##### :material/auto_awesome: Ask KAIRO AI")
            if not advisor.ai_available():
                ui.banner(
                    "AI explanations are off. Add a free provider key (GROQ_API_KEY, GEMINI_API_KEY or "
                    "OPENROUTER_API_KEY) to .env and restart KAIRO. The summary always works.",
                    "info",
                )
            else:
                language = st.segmented_control("Language", ["English", "Kannada", "Hindi"], default="English", key="ai_lang") or "English"
                if st.button("Explain with AI", type="primary", key="ask_ai"):
                    with st.spinner("Asking KAIRO AI…"):
                        st.session_state["ai_result"] = advisor.ai_explanation(plan, language=language)
    result = st.session_state.get("ai_result") if advisor.ai_available() else None
    if result:
        st.write("")
        if result["source"] == "ai":
            ui.render(ui.tags([("AI-generated", "cyan"), (advisor.active_provider_label(), "gray"), ("numbers checked against KAIRO data", "green")]))
        else:
            ui.banner(f"Showing the standard summary instead. {result['fallback_reason']}")
        ui.render(f'<div class="bubble">{escape(result["text"])}</div>')
    _footer()


# ----------------------------------------------------------------- About
def page_about() -> None:
    ui.render(ui.section("About", "What KAIRO is", "Crop-rotation decision support for five Karnataka districts, built on NASA climate data."))
    ui.render(ui.grid([
        ui.info_card("🛰️", "Data", "NASA POWER daily point data (temperature, rainfall, humidity, solar) and a GPM IMERG rainfall sample."),
        ui.info_card("🧮", "Method", "Rule-based suitability scoring against a sourced crop database, then rotation scoring with legume and family effects."),
        ui.info_card("⚖️", "Honesty", "No yield, water-saving or soil-restoration claims. Unverified crop data is flagged wherever it appears."),
    ], three=True))
    st.write("")
    ui.banner(svc.DATA_NATURE, "info")
    st.markdown("##### Limitations")
    st.markdown(
        "- Climate values are grid averages for district centres, not your field.\n"
        "- Season windows (kharif Jun–Oct, rabi Nov–Mar, summer Apr–May) are assumptions.\n"
        "- Scores use prototype weights; soil and water matching is simplified.\n"
        "- Stored climate data covers 2024–2025."
    )
    ui.banner(svc.DISCLAIMER)
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
