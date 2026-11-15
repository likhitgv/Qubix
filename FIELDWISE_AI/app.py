"""Kyro - NASA-data crop rotation decision support for Karnataka farms.

Run:  py -3.11 -m streamlit run app.py
UI only: all data handling and scoring lives in modules/.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from config.districts import DISTRICTS
from config.soils import (
    SOIL_TYPES,
    WATER_SOURCES,
    soil_id_from_label,
    water_availability_from_source,
)
from streamlit_folium import st_folium

from dashboard.map_view import build_map
from dashboard.theme import PLOT_LAYOUT, banner, inject_theme, metric_card, pill
from modules import advisor
from modules import kyro_service as svc
from modules.crop_database import load_crop_database

load_dotenv()  # reads .env (AI provider keys) if present

st.set_page_config(page_title="Kyro", page_icon="🌱", layout="wide")
inject_theme()

DISTRICT_NAMES = [d["name"] for d in DISTRICTS]
PAGES = ["Home", "Farm", "Recommendations", "Climate", "Map", "Sustainability", "Advisor", "About"]


# ----------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def _daily() -> pd.DataFrame:
    df = pd.read_csv(svc.DATA_DIR / "daily_2024-2025.csv", parse_dates=["date"])
    return df


@st.cache_data(show_spinner=False)
def _summary() -> pd.DataFrame:
    return svc.load_seasonal_summary()


def _state() -> None:
    st.session_state.setdefault("profile", None)
    st.session_state.setdefault("plan", None)
    st.session_state.setdefault("page", "Home")


def _goto(page: str) -> None:
    st.session_state["page"] = page


# ----------------------------------------------------------------- sidebar
def sidebar() -> str:
    with st.sidebar:
        st.markdown('<p class="kyro-brand">Kyro</p>', unsafe_allow_html=True)
        st.markdown('<div class="kyro-tag">Adapt your farm with NASA data</div>', unsafe_allow_html=True)
        st.write("")
        page = st.radio("Navigate", PAGES, key="page", label_visibility="collapsed")
        st.write("")
        profile = st.session_state.profile
        if profile:
            st.markdown(
                f'<div class="glass"><div class="metric-label">Current farm</div>'
                f'<b>{profile["district"]}</b><br>'
                f'<span class="metric-sub">{profile["soil_label"]} · {profile["water_label"]}</span></div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("No farm saved yet.")
    return page


# ----------------------------------------------------------------- pages
def page_home() -> None:
    st.markdown(
        '<div class="hero"><h1>Choose the next crop with evidence, not guesswork.</h1>'
        "<p>Kyro reads NASA POWER climate data for your district and ranks multi-season crop "
        "rotations against a sourced crop database, with every score explained.</p></div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    cards = [
        ("5", "Karnataka districts", "Ballari, Shivamogga, Vijayapura, Belagavi, Dharwad"),
        ("2024–25", "NASA POWER daily data", "Temperature, rainfall, humidity, solar"),
        (str(len(load_crop_database())), "Crops in database", "Sourced, with unverified rows flagged"),
    ]
    for col, (v, l, s) in zip(cols, cards):
        col.markdown(metric_card(l, v, s), unsafe_allow_html=True)
    st.write("")
    st.button("Start with your farm →", on_click=_goto, args=("Farm",))
    banner(svc.DISCLAIMER, info=True)


def page_farm() -> None:
    st.header("Your farm")
    st.caption("Tell Kyro where your farm is and what it has.")

    mode = st.radio("Location", ["Pick a district", "Use coordinates"], horizontal=True)
    district = None
    lat = lon = None
    geo = None
    if mode == "Pick a district":
        district = st.selectbox("District", DISTRICT_NAMES)
    else:
        # A map click from the previous run is applied before the inputs exist.
        click = st.session_state.pop("_map_click", None)
        if click:
            st.session_state["farm_lat"], st.session_state["farm_lon"] = click
        st.session_state.setdefault("farm_lat", 15.4589)
        st.session_state.setdefault("farm_lon", 75.0078)
        c1, c2 = st.columns(2)
        lat = c1.number_input("Latitude", -90.0, 90.0, format="%.4f", key="farm_lat")
        lon = c2.number_input("Longitude", -180.0, 180.0, format="%.4f", key="farm_lon")
        geo = svc.nearest_district(lat, lon)
        st.caption("Click the map to place your farm, or type coordinates above.")
        clicked = st_folium(
            build_map(geo["district"] if geo["within_coverage"] else None, (lat, lon), _summary()),
            height=360, use_container_width=True, returned_objects=["last_clicked"],
            key="farm_map",
        )
        last = (clicked or {}).get("last_clicked")
        if last and (round(last["lat"], 4), round(last["lng"], 4)) != (round(lat, 4), round(lon, 4)):
            st.session_state["_map_click"] = (round(last["lat"], 4), round(last["lng"], 4))
            st.rerun()
        if geo["within_coverage"]:
            banner(
                f"Nearest supported district: <b>{geo['district']}</b> "
                f"({geo['distance_km']} km away). {geo['note']}",
                info=True,
            )
            district = geo["district"]
        else:
            banner(
                f"This point is {geo['distance_km']} km from the nearest supported district "
                f"({geo['district']}). Kyro only has data for five Karnataka districts.",
            )

    with st.form("farm_form"):
        c1, c2 = st.columns(2)
        soil_label = c1.selectbox("Soil type", ["Not sure"] + [l for _, l in SOIL_TYPES])
        water_label = c2.selectbox("Water source", WATER_SOURCES)
        c3, c4 = st.columns(2)
        area = c3.number_input("Farm size (hectares)", 0.1, 10000.0, 1.0, 0.1)
        previous = c4.text_input("Previous crops (optional)", placeholder="e.g. sorghum, groundnut")
        submitted = st.form_submit_button("Generate recommendations")

    if submitted:
        if district is None:
            st.error("Choose a district, or enter coordinates inside the supported area.")
            return
        profile = {
            "district": district,
            "soil_type": soil_id_from_label(soil_label),
            "soil_label": soil_label,
            "water_availability": water_availability_from_source(water_label),
            "water_label": water_label,
            "area_ha": area,
            "previous_crops": previous.strip() or None,
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
        st.success("Saved. Opening your recommendations…")
        st.session_state["_nav"] = "Recommendations"
        st.rerun()


def _need_plan() -> dict | None:
    plan = st.session_state.plan
    if not plan:
        st.info("Save your farm first to see this page.")
        st.button("Go to Farm", on_click=_goto, args=("Farm",))
    return plan


def page_recommendations() -> None:
    st.header("Recommended rotations")
    plan = _need_plan()
    if not plan:
        return
    for note in plan["warnings"]:
        banner(note)
    cond = {c["season"]: c["environmental_data"] for c in plan["conditions"]}
    cols = st.columns(len(cond))
    for col, (season, env) in zip(cols, cond.items()):
        col.markdown(
            metric_card(
                f"{season.title()} climate",
                f"{env['temperature_c']:.1f} °C",
                f"{env['rainfall_mm']:.0f} mm rain · NASA POWER seasonal average",
            ),
            unsafe_allow_html=True,
        )
    st.write("")
    if not plan["rotations"]:
        st.warning("No rotation met the minimum requirements for this farm.")
        return

    for rot, sus in zip(plan["rotations"], plan["sustainability"]):
        with st.container():
            h1, h2 = st.columns([1, 12])
            h1.markdown(f'<div class="rank-badge">{rot["rank"]}</div>', unsafe_allow_html=True)
            h2.markdown(f"**Rotation score {rot['overall_rotation_score']:.1f} / 100**")
            chips = "".join(
                f'<span class="crop-chip"><small>{c["season"]}</small>{c["crop_name"]} '
                f'<span style="color:#6ee7b7">{c["suitability_score"]:.0f}</span></span>'
                for c in rot["crop_sequence"]
            )
            st.markdown(chips, unsafe_allow_html=True)
            flagged = [c for c in rot["crop_sequence"] if c.get("source_warnings")]
            if flagged:
                st.markdown(
                    pill("Data needs verification", "amber")
                    + " ".join(c["crop_name"] for c in flagged),
                    unsafe_allow_html=True,
                )
            if sus.get("available"):
                st.markdown(
                    pill(f"Sustainability indicator {sus['indicator_score']}", "blue")
                    + (pill("Includes legume", "green") if sus["legume_count"] else pill("No legume", "red")),
                    unsafe_allow_html=True,
                )
            with st.expander("Why this score?"):
                for e in rot.get("explanations", []):
                    st.write("•", e)
                for c in rot["crop_sequence"]:
                    details = c.get("suitability_details", {})
                    st.markdown(f"**{c['crop_name']}** ({c['season']})")
                    comps = details.get("component_scores", {})
                    if comps:
                        st.dataframe(
                            pd.DataFrame({"component": list(comps), "score": list(comps.values())}),
                            hide_index=True, width="stretch",
                        )
                    for w in c.get("source_warnings", []):
                        st.caption(f"⚠ {w}")
                    if c.get("source_urls"):
                        st.caption(f"Sources: {c['source_urls']}")
                for lim in rot.get("limitations", []):
                    st.caption(f"Limitation: {lim}")
            st.write("")

    st.download_button(
        "Download recommendations (CSV)",
        _plan_csv(plan).to_csv(index=False).encode("utf-8"),
        file_name=f"kyro_{plan['district'].lower()}_{date.today().isoformat()}.csv",
        mime="text/csv",
    )
    banner(plan["disclaimer"], info=True)


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


def page_climate() -> None:
    st.header("Climate (NASA POWER)")
    banner(svc.DATA_NATURE, info=True)
    plan = st.session_state.plan
    default = plan["district"] if plan else DISTRICT_NAMES[0]
    district = st.selectbox("District", DISTRICT_NAMES, index=DISTRICT_NAMES.index(default))
    df = _daily()
    df = df[df["location"] == district].sort_values("date")
    if df.empty:
        st.warning("No stored data for this district.")
        return
    monthly = df.set_index("date").resample("MS").agg({"temperature_c": "mean", "rainfall_mm": "sum"}).reset_index()

    c1, c2, c3 = st.columns(3)
    c1.markdown(metric_card("Mean temperature", f"{df['temperature_c'].mean():.1f} °C", "daily mean, 2024–2025"), unsafe_allow_html=True)
    c2.markdown(metric_card("Total rainfall", f"{df['rainfall_mm'].sum():.0f} mm", "sum of daily values"), unsafe_allow_html=True)
    c3.markdown(metric_card("Days of data", f"{len(df)}", f"{df['date'].min():%d %b %Y} – {df['date'].max():%d %b %Y}"), unsafe_allow_html=True)
    st.write("")

    fig = go.Figure()
    fig.add_bar(x=monthly["date"], y=monthly["rainfall_mm"], name="Rainfall (mm)", marker_color="#22d3ee", opacity=.7)
    fig.add_scatter(x=monthly["date"], y=monthly["temperature_c"], name="Temperature (°C)", yaxis="y2",
                    line=dict(color="#34d399", width=3))
    fig.update_layout(**PLOT_LAYOUT, height=420,
                      yaxis=dict(title="Rainfall (mm / month)"),
                      yaxis2=dict(title="Temperature (°C)", overlaying="y", side="right"))
    st.plotly_chart(fig, width="stretch")

    seas = _summary()
    seas = seas[seas["location"] == district].sort_values(["season_year", "season"])
    st.subheader("Season summaries")
    st.dataframe(
        seas[["season", "season_year", "days_available", "complete", "temperature_c", "rainfall_mm"]],
        hide_index=True, width="stretch",
    )
    meta = svc.load_provenance(district)
    with st.expander("Data source and coverage"):
        if meta:
            st.markdown(
                f"- **Source:** {meta.get('source', 'NASA POWER')} daily point API (community AG, UTC)\n"
                f"- **Period:** {meta.get('start_date', 'not recorded')} to {meta.get('end_date', 'not recorded')}\n"
                f"- **Retrieved:** {meta.get('retrieved_at', 'not recorded')}\n"
                f"- **Grid point:** {meta.get('latitude')}, {meta.get('longitude')}"
            )
        else:
            st.write("No provenance record found for this district.")
        st.caption("Incomplete seasons are not used for recommendations.")


def page_map() -> None:
    st.header("District map")
    st.caption("Click a marker for the latest complete NASA POWER seasonal averages.")
    plan = st.session_state.plan
    profile = st.session_state.profile
    point = None
    if profile and profile.get("latitude") is not None:
        point = (profile["latitude"], profile["longitude"])
    st_folium(
        build_map(plan["district"] if plan else None, point, _summary()),
        height=520, use_container_width=True, returned_objects=[], key="district_map",
    )
    banner("Markers are district reference points, not farm boundaries. " + svc.DATA_NATURE, info=True)


def page_sustainability() -> None:
    st.header("Sustainability indicators")
    plan = _need_plan()
    if not plan:
        return
    banner("These indicators describe rotation structure only. They are not measured or modelled water, yield or soil results.", info=True)
    if not plan["rotations"]:
        st.warning("No rotations to evaluate.")
        return
    rows = []
    for rot, sus in zip(plan["rotations"], plan["sustainability"]):
        if sus.get("available"):
            rows.append({"Rotation": f"#{rot['rank']} " + " → ".join(c["crop_name"] for c in rot["crop_sequence"]),
                         "Suitability": rot["overall_rotation_score"], "Indicator": sus["indicator_score"]})
    if rows:
        d = pd.DataFrame(rows)
        fig = go.Figure()
        fig.add_bar(y=d["Rotation"], x=d["Suitability"], name="Suitability", orientation="h", marker_color="#34d399")
        fig.add_bar(y=d["Rotation"], x=d["Indicator"], name="Sustainability indicator", orientation="h", marker_color="#22d3ee")
        fig.update_layout(**PLOT_LAYOUT, barmode="group", height=120 + 90 * len(d))
        st.plotly_chart(fig, width="stretch")
    for rot, sus in zip(plan["rotations"], plan["sustainability"]):
        if not sus.get("available"):
            continue
        with st.expander(f"Rotation #{rot['rank']} details"):
            tone = {"good": "green", "warning": "amber", "none": "red", "moderate": "blue", "info": "blue"}
            for ind in sus["indicators"]:
                st.markdown(pill(ind["name"], tone.get(ind["status"], "blue")) + ind["detail"], unsafe_allow_html=True)


def page_advisor() -> None:
    st.header("Kyro Advisor")
    plan = _need_plan()
    if not plan:
        return
    st.markdown("#### Plain-language summary")
    st.write(advisor.template_explanation(plan))
    st.caption("Built only from Kyro's computed results. Works offline.")

    st.markdown("#### Ask Kyro AI")
    if not advisor.ai_available():
        banner(
            "AI explanations are off. Add a free provider key (GROQ_API_KEY, GEMINI_API_KEY or "
            "OPENROUTER_API_KEY) to .env and restart Kyro. The summary above always works.",
            info=True,
        )
        return
    language = st.selectbox("Language", ["English", "Kannada", "Hindi"])
    if st.button("Explain with AI"):
        with st.spinner("Asking Kyro AI…"):
            result = advisor.ai_explanation(plan, language=language)
        st.session_state["ai_result"] = result
    result = st.session_state.get("ai_result")
    if result:
        if result["source"] == "ai":
            st.markdown(pill("AI-generated", "blue") + f"via {advisor.active_provider_label()}, checked against Kyro's computed numbers", unsafe_allow_html=True)
        else:
            banner(f"Showing the standard summary instead. {result['fallback_reason']}")
        st.write(result["text"])


def page_about() -> None:
    st.header("About Kyro")
    st.markdown(
        "**Kyro** supports crop-rotation decisions for five Karnataka districts using NASA POWER "
        "climate data and a sourced crop reference database."
    )
    banner(svc.DATA_NATURE, info=True)
    st.subheader("Data sources")
    st.markdown(
        "- **NASA POWER** daily point API (community AG): temperature, precipitation, humidity, solar radiation.\n"
        "- **NASA GPM IMERG** rainfall (January 2025 sample).\n"
        "- **Crop database**: ICAR/TNAU/extension sources with access dates; rows marked *needs verification* use secondary sources."
    )
    st.subheader("Limitations")
    st.markdown(
        "- Climate values are grid averages for district centres, not your field.\n"
        "- Season windows (kharif Jun–Oct, rabi Nov–Mar, summer Apr–May) are assumptions.\n"
        "- Scores use prototype weights; no yield, water-saving or soil-restoration claims are made.\n"
        "- Soil and water matching is simplified."
    )
    banner(svc.DISCLAIMER)


# ----------------------------------------------------------------- main
_state()
if "_nav" in st.session_state:
    st.session_state["page"] = st.session_state.pop("_nav")
_page = sidebar()
{
    "Home": page_home,
    "Farm": page_farm,
    "Recommendations": page_recommendations,
    "Climate": page_climate,
    "Sustainability": page_sustainability,
    "Map": page_map,
    "Advisor": page_advisor,
    "About": page_about,
}[_page]()
