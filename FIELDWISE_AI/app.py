from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.districts import DISTRICTS, get_district
from modules.crop_database import load_crop_database
from modules.crop_suitability_v2 import rank_crops_v2
from modules.data_analysis import (
    create_rainfall_chart,
    create_temperature_chart,
    generate_district_summaries,
    generate_district_trends,
    load_nasa_power_data,
)
from modules.rotation_engine import generate_crop_rotations


BASE_DIR = Path(__file__).resolve().parent
SEASONS = ("kharif", "rabi", "summer")
SOILS = (
    "sandy-loam", "loam", "clay-loam", "silty-loam", "red-soil",
    "black-soil", "alluvial", "sandy", "loamy",
)
DISTRICT_NAMES = [item["name"] for item in DISTRICTS]
NAV_ITEMS = [
    "Overview", "Farm Profile", "Climate Intelligence",
    "Crop Intelligence", "Rotation Planner", "Sustainability", "District Map",
]

st.set_page_config(
    page_title="KAIRO | Farm Intelligence",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "appearance" not in st.session_state:
    st.session_state.appearance = "Light"
appearance = st.session_state.appearance

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:#14251f; --muted:#65756c; --green:#174c3b; --green2:#256b50; --lime:#cce36b; --paper:#f5f7f2; --card:#ffffff; --line:#e2e9e1; --orange:#da8e49; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; color:var(--ink); }
.stApp { background:radial-gradient(ellipse at 78% 8%,rgba(211,232,220,.72),transparent 34%),linear-gradient(145deg,#f5f8f5 0%,#edf3f0 54%,#f8faf8 100%); background-attachment:fixed; }
.block-container { max-width:1480px; padding-top:1.6rem; padding-bottom:3rem; }
header.stAppHeader, header[data-testid="stHeader"] { background:rgba(244,249,246,.72) !important; backdrop-filter:blur(24px) saturate(180%); border-bottom:1px solid rgba(255,255,255,.68); }
.stAppToolbar { background:transparent !important; }
.stAppDeployButton, div[data-testid="stAppDeployButton"] { display:none !important; }
section[data-testid="stSidebar"] { background:rgba(13,43,33,.91); backdrop-filter:blur(26px) saturate(155%); border-right:1px solid rgba(222,242,229,.15); box-shadow:12px 0 34px rgba(20,54,39,.08); }
section[data-testid="stSidebar"] * { color:#edf4eb; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label { color:#f4f8f3 !important; font-weight:600; padding:.58rem .68rem; border-radius:10px; transition:background .15s ease; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { color:#fff !important; background:#1d4134; }
section[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) { color:#fff !important; background:#1d4938; font-weight:800; }
section[data-testid="stSidebar"] input[type="radio"] { accent-color:#cce36b !important; }
section[data-testid="stSidebar"] [data-testid="stSelectbox"] label { color:#d9e7dc !important; font-weight:700; }
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * { color:#cad8cd !important; opacity:1 !important; }
section[data-testid="stSidebar"] .status-pill { background:#e4f3e8 !important; color:#174e35 !important; }
section[data-testid="stSidebar"] hr { border-color:#375348; }
section[role="dialog"] { background:rgba(249,252,249,.92) !important; border:1px solid rgba(255,255,255,.85); border-radius:24px !important; color:#14251f !important; backdrop-filter:blur(30px) saturate(170%); box-shadow:0 28px 80px rgba(14,38,28,.22); }
section[role="dialog"] h1, section[role="dialog"] h2, section[role="dialog"] h3,
section[role="dialog"] p, section[role="dialog"] label { color:#14251f !important; }
section[role="dialog"] [data-testid="stCaptionContainer"],
section[role="dialog"] [data-testid="stCaptionContainer"] * { color:#405548 !important; }
section[role="dialog"] button[aria-label="Close"] { color:#173b2b !important; opacity:1 !important; background:rgba(226,238,229,.76) !important; border:1px solid rgba(42,91,59,.18) !important; border-radius:12px !important; }
section[role="dialog"] button[aria-label="Close"] svg { color:#173b2b !important; }
section[role="dialog"] [data-testid="stMetric"] { background:#fff !important; }
section[role="dialog"] [data-testid="stSelectbox"] [role="group"] { background:#fff !important; border:1px solid #d4ded3 !important; }
section[role="dialog"] [data-testid="stSelectbox"] input[role="combobox"] { color:#14251f !important; }
/* Keep Streamlit's semantic alerts readable even when the OS/browser prefers dark UI. */
[data-testid="stAlertContainer"] { border-radius:12px !important; background:#eaf2f8 !important; border:1px solid #cbddea !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { background:#fff4e4 !important; border-color:#efd9b5 !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { background:#fff0ee !important; border-color:#edceca !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { background:#eaf5ed !important; border-color:#cee4d3 !important; }
[data-testid="stAlertContentInfo"] { color:#163b57 !important; }
[data-testid="stAlertContentInfo"] p, [data-testid="stAlertContentInfo"] span { color:#163b57 !important; opacity:1 !important; }
[data-testid="stAlertContentWarning"] { color:#684713 !important; }
[data-testid="stAlertContentWarning"] p, [data-testid="stAlertContentWarning"] span { color:#684713 !important; opacity:1 !important; }
[data-testid="stAlertContentError"] { color:#7b2929 !important; }
[data-testid="stAlertContentError"] p, [data-testid="stAlertContentError"] span { color:#7b2929 !important; opacity:1 !important; }
[data-testid="stAlertContentSuccess"] { color:#1c5836 !important; }
[data-testid="stAlertContentSuccess"] p, [data-testid="stAlertContentSuccess"] span { color:#1c5836 !important; opacity:1 !important; }
.stDeployButton { display:none !important; }
h1,h2,h3 { font-family:'Manrope','DM Sans',sans-serif !important; letter-spacing:-.035em; color:var(--ink) !important; }
h1 { font-size:2.4rem !important; font-weight:800 !important; line-height:1.1 !important; }
h2 { font-size:1.55rem !important; font-weight:750 !important; }
h3 { font-size:1.05rem !important; font-weight:750 !important; }
p,li { color:var(--ink); }
[data-testid="stMetric"] { background:rgba(255,255,255,.72); backdrop-filter:blur(18px) saturate(160%); border:1px solid rgba(255,255,255,.9); border-radius:20px; padding:18px 20px; box-shadow:0 10px 30px rgba(18,43,32,.06),inset 0 1px rgba(255,255,255,.85); }
[data-testid="stMetricLabel"] { color:var(--muted) !important; font-size:.82rem !important; }
[data-testid="stMetricValue"] { color:var(--green) !important; font-family:'Manrope',sans-serif; font-size:clamp(1.2rem,2vw,1.9rem) !important; font-weight:800; }
main[data-testid="stMain"] [data-testid="stSelectbox"] [role="group"] { background:#fff !important; border:1px solid #d4ded3 !important; color:#14251f !important; }
main[data-testid="stMain"] [data-testid="stSelectbox"] input[role="combobox"] { color:#14251f !important; }
main[data-testid="stMain"] input:not([type="checkbox"]):not([type="radio"]),
main[data-testid="stMain"] textarea { background:#fff !important; color:#14251f !important; border-color:#d4ded3 !important; }
main[data-testid="stMain"] [data-testid="stNumberInput"] button { color:#31483a !important; }
main[data-testid="stMain"] [data-testid="stRadio"] label { color:#263a30 !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"] { background:#eaf2f8 !important; border:1px solid #cbddea !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { background:#fff4e4 !important; border-color:#efd9b5 !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { background:#fff0ee !important; border-color:#edceca !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { background:#eaf5ed !important; border-color:#cee4d3 !important; }
div[data-testid="stVerticalBlockBorderWrapper"] { background:rgba(255,255,255,.58); backdrop-filter:blur(20px) saturate(160%); border:1px solid rgba(255,255,255,.82); border-radius:22px; box-shadow:0 12px 32px rgba(18,43,32,.045),inset 0 1px rgba(255,255,255,.7); }
.stButton>button, .stFormSubmitButton>button { border-radius:13px; border:1px solid rgba(255,255,255,.92); background:rgba(230,241,234,.88); backdrop-filter:blur(18px) saturate(160%); color:#143d2c !important; font-weight:750; padding:.62rem 1rem; box-shadow:0 6px 18px rgba(19,62,43,.10),inset 0 1px rgba(255,255,255,.95); transition:all .18s ease; }
.stButton>button *, .stFormSubmitButton>button * { color:#143d2c !important; }
.stButton>button:hover, .stFormSubmitButton>button:hover { background:rgba(210,232,218,.96); border-color:#c3ddcb; color:#103a29 !important; transform:translateY(-1px); box-shadow:0 10px 24px rgba(19,62,43,.14); }
[data-testid="stExpander"] { border:1px solid var(--line); border-radius:12px; background:white; }
[data-testid="stAlert"] { border-radius:12px; }
.eyebrow { color:#91b54d; font-size:.73rem; text-transform:uppercase; letter-spacing:.16em; font-weight:800; }
.hero { background:linear-gradient(118deg,rgba(20,62,48,.93) 0%,rgba(29,96,70,.86) 64%,rgba(57,128,82,.82) 100%); color:white; padding:34px 38px; border:1px solid rgba(255,255,255,.32); border-radius:28px; position:relative; overflow:hidden; backdrop-filter:blur(24px) saturate(145%); box-shadow:0 20px 54px rgba(20,60,45,.18),inset 0 1px rgba(255,255,255,.2); }
.hero:after { content:' '; position:absolute; width:310px; height:310px; border:1px solid rgba(223,242,178,.17); border-radius:50%; right:-52px; top:-120px; box-shadow:0 0 0 36px rgba(223,242,178,.035),0 0 0 75px rgba(223,242,178,.025); }
.hero h1 { color:white !important; max-width:720px; margin:.55rem 0 .65rem 0; }
.hero p { color:#e2efe5; max-width:680px; font-size:1.03rem; line-height:1.7; }
.hero .eyebrow { color:#d6ec8c; }
.hero-note { color:#d6e6d7; font-size:.82rem; }
.section-kicker { color:#71904e; font-size:.72rem; text-transform:uppercase; letter-spacing:.14em; font-weight:800; margin-bottom:.2rem; }
.mini-card { background:rgba(255,255,255,.60); border:1px solid rgba(255,255,255,.88); border-radius:22px; padding:20px; min-height:142px; backdrop-filter:blur(20px) saturate(165%); box-shadow:0 12px 32px rgba(18,43,32,.055),inset 0 1px rgba(255,255,255,.9); }
.mini-card .icon { display:flex; width:44px; height:44px; margin:0 auto 14px; align-items:center; justify-content:center; border-radius:15px; background:rgba(36,112,72,.13); border:1px solid rgba(36,112,72,.12); color:#175d3c; }
.mini-card .icon svg { display:block; width:23px; height:23px; fill:none; stroke:currentColor; stroke-width:1.9; stroke-linecap:round; stroke-linejoin:round; }
.mini-card p { color:var(--muted); font-size:.9rem; line-height:1.55; margin:.35rem 0 .7rem; }
.mini-card strong { color:var(--ink); font-size:1.02rem; }
.status-pill { display:inline-block; padding:5px 10px; border-radius:99px; font-size:.72rem; font-weight:800; background:#e5f3e8; color:#1b6141 !important; }
.source-note { padding:12px 15px; border-radius:12px; background:#edf4eb; border:1px solid #dbe7d8; color:#4c6153; font-size:.83rem; line-height:1.55; }
.warning-note { padding:12px 15px; border-radius:12px; background:#fff5e9; border:1px solid #f1ddc6; color:#805324; font-size:.83rem; line-height:1.55; }
.score { color:#1f6849; font:800 1.5rem 'Manrope',sans-serif; }
.sequence { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:.5rem 0; }
.sequence span { display:inline-block; background:#edf4eb; border:1px solid #d9e7d5; border-radius:9px; padding:8px 11px; color:#194b39; font-size:.84rem; font-weight:700; }
.footer { color:#859289; font-size:.78rem; text-align:center; padding-top:1.4rem; }
@media(max-width:760px) { .block-container { padding:1rem .8rem 2rem; } .hero { padding:25px 22px; border-radius:19px; } .hero h1 { font-size:1.9rem !important; } }
</style>
""", unsafe_allow_html=True)

DARK_THEME_CSS = """
<style>
.stApp { background:#101914 !important; color:#edf4eb !important; }
.block-container { color:#edf4eb !important; }
header.stAppHeader, header[data-testid="stHeader"] { background:rgba(16,29,23,.72) !important; border-bottom-color:rgba(216,235,222,.12) !important; }
section[data-testid="stSidebar"] { background:rgba(9,29,22,.90) !important; border-right-color:rgba(216,235,222,.12) !important; }
h1,h2,h3,p,li,label { color:#eaf1eb !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * { color:#bac9bd !important; }
[data-testid="stMetric"] { background:rgba(23,37,30,.74) !important; backdrop-filter:blur(20px); border-color:rgba(207,231,214,.17) !important; }
[data-testid="stMetricLabel"] { color:#becbbf !important; }
[data-testid="stMetricValue"] { color:#cce36b !important; }
div[data-testid="stVerticalBlockBorderWrapper"], .mini-card { background:rgba(23,37,30,.70) !important; backdrop-filter:blur(22px) saturate(145%); border-color:rgba(207,231,214,.16) !important; }
.mini-card strong, .mini-card p { color:#eaf1eb !important; }
.mini-card .icon { background:rgba(204,227,107,.14) !important; border-color:rgba(204,227,107,.18) !important; color:#d7ed8a !important; }
.stButton>button, .stFormSubmitButton>button { color:#eaf1eb !important; background:rgba(204,227,107,.13) !important; border-color:rgba(204,227,107,.28) !important; box-shadow:0 8px 22px rgba(0,0,0,.18),inset 0 1px rgba(255,255,255,.10) !important; }
.stButton>button *, .stFormSubmitButton>button * { color:#eaf1eb !important; }
.stButton>button:hover, .stFormSubmitButton>button:hover { background:rgba(204,227,107,.21) !important; }
[data-testid="stExpander"] { background:#17251e !important; border-color:#34493b !important; color:#edf4eb !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] p { color:#edf4eb !important; }
 [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
main[data-testid="stMain"] [data-testid="stSelectbox"] [role="group"] { background:#17251e !important; color:#edf4eb !important; border-color:#49604f !important; }
main[data-testid="stMain"] [data-testid="stSelectbox"] input[role="combobox"] { color:#edf4eb !important; }
main[data-testid="stMain"] input:not([type="checkbox"]):not([type="radio"]), main[data-testid="stMain"] textarea { background:#17251e !important; color:#edf4eb !important; border-color:#49604f !important; }
main[data-testid="stMain"] [data-testid="stNumberInput"] button { color:#edf4eb !important; }
main[data-testid="stMain"] [data-testid="stRadio"] label { color:#edf4eb !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"] { background:#1d3038 !important; border:1px solid #3c5561 !important; }
main[data-testid="stMain"] [data-testid="stAlertContentInfo"], main[data-testid="stMain"] [data-testid="stAlertContentInfo"] * { color:#deebf1 !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { background:#3a301f !important; border-color:#5d4a2c !important; }
main[data-testid="stMain"] [data-testid="stAlertContentWarning"], main[data-testid="stMain"] [data-testid="stAlertContentWarning"] * { color:#f3dfb9 !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { background:#3b2424 !important; border-color:#654040 !important; }
main[data-testid="stMain"] [data-testid="stAlertContentError"], main[data-testid="stMain"] [data-testid="stAlertContentError"] * { color:#f5d4d1 !important; }
main[data-testid="stMain"] [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { background:#1e3729 !important; border-color:#3b5a43 !important; }
main[data-testid="stMain"] [data-testid="stAlertContentSuccess"], main[data-testid="stMain"] [data-testid="stAlertContentSuccess"] * { color:#d9ecdc !important; }
[data-testid="stAlertContainer"] { background:#1d3038 !important; border-color:#3c5561 !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { background:#3a301f !important; border-color:#5d4a2c !important; }
[data-testid="stAlertContentWarning"], [data-testid="stAlertContentWarning"] * { color:#f3dfb9 !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { background:#3b2424 !important; border-color:#654040 !important; }
[data-testid="stAlertContentError"], [data-testid="stAlertContentError"] * { color:#f5d4d1 !important; }
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { background:#1e3729 !important; border-color:#3b5a43 !important; }
[data-testid="stAlertContentSuccess"], [data-testid="stAlertContentSuccess"] * { color:#d9ecdc !important; }
[data-testid="stAlertContentInfo"], [data-testid="stAlertContentInfo"] * { color:#deebf1 !important; }
section[role="dialog"] { background:rgba(21,35,27,.94) !important; border-color:rgba(216,235,222,.16) !important; color:#edf4eb !important; }
section[role="dialog"] h1, section[role="dialog"] h2, section[role="dialog"] h3,
section[role="dialog"] p, section[role="dialog"] label { color:#edf4eb !important; }
section[role="dialog"] [data-testid="stCaptionContainer"], section[role="dialog"] [data-testid="stCaptionContainer"] * { color:#bac9bd !important; }
section[role="dialog"] button[aria-label="Close"] { color:#edf4eb !important; background:rgba(204,227,107,.13) !important; border-color:rgba(204,227,107,.22) !important; }
section[role="dialog"] button[aria-label="Close"] svg { color:#edf4eb !important; }
section[role="dialog"] [data-testid="stMetric"] { background:#1d3025 !important; border-color:#3b5543 !important; }
section[role="dialog"] [data-testid="stSelectbox"] [role="group"] { background:#17251e !important; border-color:#49604f !important; }
section[role="dialog"] [data-testid="stSelectbox"] input[role="combobox"] { color:#edf4eb !important; }
.source-note { background:#1a3225 !important; border-color:#35523d !important; color:#dce9dc !important; }
.warning-note { background:#382d1e !important; border-color:#5c4829 !important; color:#f1d4a6 !important; }
.sequence span { background:#1a3225 !important; border-color:#35523d !important; color:#e2efdf !important; }
.section-kicker { color:#bfd779 !important; }
</style>
"""
if appearance == "Dark":
    st.markdown(DARK_THEME_CSS, unsafe_allow_html=True)
elif appearance == "System":
    st.markdown("<style>@media (prefers-color-scheme: dark) {" + DARK_THEME_CSS.removeprefix("<style>").removesuffix("</style>") + "}</style>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_climate():
    file_path = BASE_DIR / "data" / "nasa_power" / "nasa_power_consolidated.csv"
    data, report = load_nasa_power_data(file_path)
    return data, pd.DataFrame(generate_district_summaries(data)), generate_district_trends(data), report


@st.cache_data(show_spinner=False)
def load_seasonal_summary():
    path = BASE_DIR / "data" / "nasa_power" / "seasonal_summary.csv"
    frame = pd.read_csv(path)
    frame["complete"] = frame["complete"].astype(str).str.lower().isin(("true", "1", "yes"))
    for column in ("season_year", "temperature_c", "rainfall_mm"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


@st.cache_data(show_spinner=False)
def load_crop_records():
    return load_crop_database()


@st.cache_data(show_spinner=False)
def load_provenance():
    path = BASE_DIR / "data" / "nasa_power" / "provenance.json"
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_seasonal_provenance():
    path = BASE_DIR / "data" / "nasa_power" / "provenance_seasonal.json"
    return json.loads(path.read_text(encoding="utf-8"))


def latest_complete_seasons(district: str) -> pd.DataFrame:
    frame = load_seasonal_summary()
    chosen = frame[(frame.location.str.strip() == district) & frame.complete].dropna(
        subset=["season_year", "temperature_c", "rainfall_mm"]
    ).sort_values("season_year", ascending=False)
    return chosen.drop_duplicates("season", keep="first")


def rotation_conditions(district: str) -> list[dict]:
    frame = load_seasonal_summary()
    rows = frame[(frame.location.str.strip() == district) & frame.complete].dropna(
        subset=["season_year", "temperature_c", "rainfall_mm"]
    )
    # Use a chronological, comparable Kharif-to-Rabi pair where available.
    kharif = rows[rows.season.str.lower() == "kharif"].sort_values("season_year", ascending=False)
    rabi = rows[rows.season.str.lower() == "rabi"].sort_values("season_year", ascending=False)
    pair = None
    for _, rabi_row in rabi.iterrows():
        candidates = kharif[kharif.season_year <= rabi_row.season_year]
        if not candidates.empty:
            pair = (candidates.iloc[0], rabi_row)
            break
    if pair is None:
        return []
    return [
        {
            "season": str(row.season).lower(),
            "environmental_data": {
                "temperature_c": float(row.temperature_c),
                "rainfall_mm": float(row.rainfall_mm),
            },
        }
        for row in pair
    ]


def engine_profile(profile: dict, season: str | None = None) -> dict:
    return {
        "soil_type": profile.get("soil_type") or None,
        "water_availability": profile.get("water_availability") or None,
        "season": season.lower() if season else None,
    }


def source_label(district: str) -> str:
    metadata = load_provenance().get(district, {})
    return "NASA POWER · gridded modelled data"


def fmt(value, digits=1, unit=""):
    if pd.isna(value):
        return "Unavailable"
    return f"{float(value):,.{digits}f}{unit}"


def section_header(kicker: str, title: str, description: str | None = None):
    st.markdown(f'<div class="section-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.subheader(title)
    if description:
        st.caption(description)


def provenance_panel(district: str):
    meta = load_provenance().get(district, {})
    seasonal_meta = load_seasonal_provenance().get(district, {})
    dates = f"daily series {meta.get('start_date', '—')} to {meta.get('end_date', '—')}"
    seasonal_dates = f"seasonal summaries {seasonal_meta.get('start_date', '—')} to {seasonal_meta.get('end_date', '—')}"
    retrieval = seasonal_meta.get("retrieved_at") or meta.get("retrieved_at", "Not recorded")
    st.markdown(
        f'<div class="source-note"><b>Source & coverage</b> · NASA POWER Daily Point API · {dates}; {seasonal_dates} · Retrieved {retrieval}. '
        "Values are gridded, modelled estimates based on satellite and reanalysis inputs, not field or weather-station measurements.</div>",
        unsafe_allow_html=True,
    )


def render_profile_summary(profile):
    if not profile:
        st.info("Add your farm details to unlock tailored crop and rotation assessments.")
        return
    st.write(f"**{profile['district']}** · {profile.get('area_ha', '—')} ha · {profile.get('soil_type') or 'Soil not selected'}")
    st.caption(f"Water: {profile.get('water_availability') or 'Not selected'} · Previous crop: {profile.get('previous_crop') or 'Not provided'}")


def render_climate(district: str):
    _, summaries, trends, _ = load_climate()
    seasonal = latest_complete_seasons(district)
    selected = summaries[summaries.location == district]
    if selected.empty:
        st.warning("No climate summary is available for this district in the current data files.")
        return
    summary = selected.iloc[0]
    st.caption("Stored daily time series currently covers January 2025. Seasonal indicators use the latest complete NASA POWER season records available.")
    a, b, c = st.columns(3)
    a.metric("Mean temperature · Jan 2025", fmt(summary.average_temperature_c, 1, " °C"))
    b.metric("Rainfall · Jan 2025", fmt(summary.total_rainfall_mm, 1, " mm"))
    c.markdown(f"**Daily temperature range**  \n{fmt(summary.minimum_temperature_c,1,' °C')} to {fmt(summary.maximum_temperature_c,1,' °C')}")
    if not seasonal.empty:
        st.markdown("#### Latest complete seasonal conditions")
        cols = st.columns(min(3, len(seasonal)))
        for index, (_, row) in enumerate(seasonal.iterrows()):
            with cols[index % len(cols)]:
                st.metric(f"{str(row.season).title()} · {int(row.season_year)}", f"{row.temperature_c:.1f} °C")
                st.caption(f"{row.rainfall_mm:,.0f} mm seasonal rainfall")
    district_trends = trends[trends.location == district].copy()
    if not district_trends.empty:
        st.markdown("#### Daily climate · January 2025")
        tfig = create_temperature_chart(district_trends)
        tfig.update_layout(template="plotly_white", title="Daily temperature", title_x=0, height=330, margin=dict(l=10,r=10,t=42,b=10), showlegend=False, paper_bgcolor="white", plot_bgcolor="white")
        rfig = create_rainfall_chart(district_trends)
        rfig.update_layout(template="plotly_white", title="Daily rainfall", title_x=0, height=300, margin=dict(l=10,r=10,t=42,b=10), showlegend=False, paper_bgcolor="white", plot_bgcolor="white")
        st.plotly_chart(tfig, use_container_width=True, config={"displayModeBar": False})
        st.plotly_chart(rfig, use_container_width=True, config={"displayModeBar": False})
    st.markdown("#### Compare districts")
    comparison = summaries[["location", "average_temperature_c", "total_rainfall_mm"]].copy()
    comparison["Selected"] = comparison.location.eq(district)
    fig = px.bar(comparison, x="location", y="total_rainfall_mm", color="Selected", color_discrete_map={True: "#1d694a", False: "#b9cbb8"}, labels={"location":"District", "total_rainfall_mm":"Rainfall (mm) · Jan 2025", "Selected":"Selected district"})
    fig.update_layout(template="plotly_white", height=300, showlegend=False, margin=dict(l=10,r=10,t=15,b=5), paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    provenance_panel(district)


def render_crop_results(profile: dict, season: str):
    if not profile or not profile.get("soil_type"):
        st.info("Complete the farm profile and select a soil type before running a crop assessment.")
        return
    latest = latest_complete_seasons(profile["district"])
    selected = latest[latest.season.str.lower() == season.lower()]
    if selected.empty:
        st.warning(f"No complete NASA seasonal record is available for {season.title()} in {profile['district']}.")
        return
    row = selected.iloc[0]
    crop_rows = load_crop_records()
    try:
        results = rank_crops_v2(
            crops=crop_rows,
            environmental_data={"temperature_c": float(row.temperature_c), "rainfall_mm": float(row.rainfall_mm)},
            farm_profile=engine_profile(profile, season),
            minimum_data_coverage=60,
        )
    except Exception as error:
        st.error(f"Assessment could not be generated: {error}")
        return
    st.markdown(f'<div class="source-note">Conditions used: {season.title()} {int(row.season_year)} · {row.temperature_c:.1f} °C mean temperature · {row.rainfall_mm:,.0f} mm seasonal rainfall. Scores are rule-based decision-support scores, not probabilities or yield predictions.</div>', unsafe_allow_html=True)
    if not results:
        st.warning("The crop reference database currently has no records to assess.")
        return
    for index, result in enumerate(results, start=1):
        title = result.get("crop_name") or result.get("crop_id") or "Crop"
        cols = st.columns([.1, .62, .28])
        cols[0].markdown(f"**{index:02d}**")
        cols[1].markdown(f"**{title}**")
        score = result.get("overall_score")
        cols[2].markdown(f'<span class="score">{fmt(score,0," / 100")}</span>', unsafe_allow_html=True)
        state = "Eligible for ranking" if result.get("eligible_for_ranking") else "Insufficient data coverage"
        st.caption(f"{state} · {result.get('data_coverage_percent', 0):.0f}% data coverage · {result.get('source_verification', 'unverified')}")
        with st.expander(f"Why {title}? · score components, sources & limits"):
            components = result.get("component_scores", {})
            st.write("**Score components**")
            st.json(components)
            for explanation in result.get("explanations", []):
                st.write(f"• {explanation}")
            if result.get("source_warnings"):
                st.warning("Source verification warning: " + " ".join(result["source_warnings"]))
            st.caption("Sources: " + str(result.get("source_name") or "Not recorded"))
            source_urls = result.get("source_urls") or ""
            for url in [part.strip() for part in str(source_urls).split("|") if part.strip()]:
                st.markdown(f"[Open crop reference]({url})")
            st.caption("Limitations: " + " ".join(result.get("limitations", [])))


def render_rotations(profile: dict):
    if not profile or not profile.get("soil_type"):
        st.info("Complete the farm profile and select a soil type before planning rotations.")
        return
    conditions = rotation_conditions(profile["district"])
    if len(conditions) < 2:
        st.warning("Two complete, comparable season records are required for a rotation plan.")
        return
    try:
        rotations = generate_crop_rotations(
            crops=load_crop_records(),
            seasonal_conditions=conditions,
            farm_profile=engine_profile(profile),
            top_n=5,
            minimum_data_coverage=60,
        )
    except Exception as error:
        st.error(f"Rotation plan could not be generated: {error}")
        return
    if not rotations:
        st.warning("No eligible rotation sequences were found for the available conditions and crop references.")
        return
    st.markdown('<div class="warning-note">Rotation scores are heuristic. This prototype does not model pests, disease cycles, nutrient balances, field history, or local agronomic constraints.</div>', unsafe_allow_html=True)
    for item in rotations:
        st.markdown(f"### Plan {item.get('rank', '—')} <span class='score'>{item.get('overall_rotation_score', 0):.1f} / 100</span>", unsafe_allow_html=True)
        pieces = [f"{row.get('season','').title()} · {row.get('crop_name')} ({row.get('suitability_score',0):.0f})" for row in item.get("crop_sequence", [])]
        st.markdown('<div class="sequence">' + "<span>→</span>".join(f"<span>{piece}</span>" for piece in pieces) + '</div>', unsafe_allow_html=True)
        with st.expander("Ranking rationale and crop source details"):
            st.write(f"Average crop suitability: {item.get('average_crop_suitability', 0):.1f} · repeated-family adjustment: −{item.get('family_penalty', 0)} · legume transition adjustment: +{item.get('legume_bonus', 0)}")
            for explanation in item.get("explanations", []):
                st.write(f"• {explanation}")
            for crop in item.get("crop_sequence", []):
                st.markdown(f"**{crop.get('season','').title()} · {crop.get('crop_name')}** — {crop.get('source_name') or 'Source not recorded'} (accessed {crop.get('source_accessed_date') or 'date unavailable'})")
                if crop.get("source_warnings"):
                    st.warning("Needs source verification: " + " ".join(crop["source_warnings"]))
            st.caption("Limitations: " + " ".join(item.get("limitations", [])))


def render_map(selected: str):
    frame = pd.DataFrame(DISTRICTS)
    frame["selected"] = frame.name.eq(selected)
    frame["point_size"] = frame["selected"].map({True:18, False:10})
    fig = px.scatter(frame, x="longitude", y="latitude", text="name", color="selected", size="point_size", size_max=22, color_discrete_map={True:"#d5893d",False:"#24694d"}, hover_name="name", hover_data={"state":True,"latitude":":.4f","longitude":":.4f","selected":False,"point_size":False})
    fig.update_traces(textposition="top center", marker=dict(line=dict(width=2,color="white")))
    fig.update_layout(template="plotly_white", height=420, xaxis_title="Longitude", yaxis_title="Latitude", showlegend=False, margin=dict(l=15,r=15,t=15,b=15), paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.caption("Markers are representative district reference points from project configuration, not administrative boundaries or precise farm locations.")


@st.dialog("KAIRO · Module preview", width="large")
def module_popup(module: str, district: str):
    if module == "Climate Intelligence":
        section_header("NASA DATA", "Climate intelligence", "Season summaries, daily trends and district comparisons.")
        render_climate(district)
    elif module == "District Map":
        section_header("KARNATAKA", "District explorer", "Select a marker by updating the district selector on the overview.")
        render_map(district)
    elif module == "Farm Profile":
        section_header("YOUR FIELD", "Farm profile", "Your saved profile is stored in this browser session.")
        render_profile_summary(st.session_state.get("farm_profile"))
        st.info("Open Farm Profile in the sidebar to edit the details.")
    elif module == "Crop Intelligence":
        section_header("DECISION SUPPORT", "Crop intelligence", "Transparent scoring from available crop and seasonal references.")
        profile = st.session_state.get("farm_profile")
        season = st.selectbox("Season for preview", ["kharif", "rabi", "summer"], key="popup_crop_season")
        render_crop_results(profile, season)
    elif module == "Rotation Planner":
        section_header("SEASONAL STRATEGY", "Rotation planner", "Ranked crop sequences with rationale and verification warnings.")
        render_rotations(st.session_state.get("farm_profile"))
    else:
        section_header("RESPONSIBLE FARMING", "Sustainability view", "Descriptive rotation characteristics only; no impact estimates.")
        st.info("No sustainability calculation module is available yet. The dashboard does not estimate water savings, carbon reductions, yield changes, or soil restoration.")


# Persistent session state: editable inputs remain populated between pages.
if "active_page" not in st.session_state:
    st.session_state.active_page = "Overview"
if "selected_district" not in st.session_state:
    st.session_state.selected_district = "Ballari"
if "farm_profile" not in st.session_state:
    st.session_state.farm_profile = None

with st.sidebar:
    logo = BASE_DIR / "assets" / "logo.png"
    if logo.exists():
        st.image(str(logo), width=48)
    st.markdown("## KAIRO")
    st.caption("FIELD & CLIMATE INTELLIGENCE")
    st.markdown("<span class='status-pill'>● SYSTEM READY</span>", unsafe_allow_html=True)
    st.divider()
    st.radio("Workspace", NAV_ITEMS, key="active_page", label_visibility="collapsed")
    st.divider()
    st.selectbox("Appearance", ["Light", "Dark", "System"], key="appearance", help="Choose a light, dark, or operating-system-matched workspace theme.")
    st.caption("Karnataka · 5 supported districts")

page = st.session_state.active_page
try:
    climate_data, climate_summaries, climate_trends, climate_report = load_climate()
    data_ready = True
except Exception as exc:
    data_ready = False
    climate_data = climate_summaries = climate_trends = climate_report = None
    st.error(f"Climate data could not be loaded: {exc}")

profile = st.session_state.get("farm_profile")
active_district = profile.get("district") if profile else st.session_state.selected_district

if page == "Overview":
    hero_left, hero_right = st.columns([.74,.26], vertical_alignment="center")
    with hero_left:
        st.markdown('<div class="hero"><div class="eyebrow">KAIRO · NASA SPACE APPS CHALLENGE</div><h1>Make every growing decision more informed.</h1><p>Bring NASA climate intelligence and transparent crop planning into one clear workspace for Karnataka farms.</p><span class="hero-note">Climate context · Crop suitability · Seasonal rotation</span></div>', unsafe_allow_html=True)
    with hero_right:
        st.markdown("<div class='section-kicker'>WORKSPACE LOCATION</div>", unsafe_allow_html=True)
        selection = st.selectbox("District", DISTRICT_NAMES, index=DISTRICT_NAMES.index(active_district), label_visibility="collapsed", key="overview_district")
        if selection != st.session_state.selected_district:
            st.session_state.selected_district = selection
            if profile:
                profile["district"] = selection
                profile["coordinates"] = get_district(selection)
            st.rerun()
        district_info = get_district(selection)
        st.caption(f"{district_info['state']} · {district_info['latitude']:.4f}, {district_info['longitude']:.4f}")
        st.markdown("<span class='status-pill'>● NASA DATA AVAILABLE</span>", unsafe_allow_html=True)

    st.write("")
    if not data_ready:
        st.warning("Climate records are unavailable. Climate-derived insights are hidden until the project data can be loaded.")
    else:
        row = climate_summaries[climate_summaries.location == selection]
        seasonal = latest_complete_seasons(selection)
        left, right, third, fourth = st.columns(4)
        left.metric("Mean temp · Jan 2025", fmt(row.iloc[0].average_temperature_c,1," °C") if not row.empty else "—")
        left.caption("NASA POWER daily series")
        right.metric("Rainfall · Jan 2025", fmt(row.iloc[0].total_rainfall_mm,1," mm") if not row.empty else "—")
        right.caption("NASA POWER daily series")
        latest = seasonal.sort_values("season_year",ascending=False).iloc[0] if not seasonal.empty else None
        third.metric("Season", f"{str(latest.season).title()} ’{int(latest.season_year) % 100:02d}" if latest is not None else "Unavailable")
        third.caption(f"{latest.rainfall_mm:,.0f} mm seasonal rainfall" if latest is not None else "No complete record")
        fourth.metric("Farm profile", "Ready" if profile and profile.get("soil_type") else "Set up")
        fourth.caption("Saved for this session" if profile else "Add soil and water details")

    st.write("")
    section_header("YOUR WORKSPACE", "Explore the intelligence suite", "Open a module preview or use the sidebar for the complete workspace view.")
    icons = {
        "farm": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21v-9m0 5c-4.5 0-7-2.7-7-7 4.7 0 7 2.7 7 7Zm0-4c0-4.7 2.7-7 7-7 0 4.5-2.7 7-7 7Z"/></svg>',
        "climate": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.42 1.42m11.3 11.3 1.42 1.42M2 12h2m16 0h2M4.93 19.07l1.42-1.42m11.3-11.3 1.42-1.42"/></svg>',
        "crop": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21V11m0 3c-4.5 0-7-2.5-7-7 4.5 0 7 2.5 7 7Zm0-4c0-4.5 2.5-7 7-7 0 4.5-2.5 7-7 7Z"/><path d="M5 21h14"/></svg>',
        "rotation": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.6 9A7 7 0 0 1 18 6l2 2M4 16l2 2a7 7 0 0 0 12.4-3"/></svg>',
        "sustainability": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 4c-8 0-13 3.5-13 9a5 5 0 0 0 5 5c5.5 0 8-6 8-14Z"/><path d="M3 21c3-5 6-8 11-11"/></svg>',
        "map": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    }
    cards = [
        ("Farm Profile","farm","Set up field details, soil and irrigation.","Farm Profile"),
        ("Climate Intelligence","climate","Review seasonal signals and daily NASA trends.","Climate Intelligence"),
        ("Crop Intelligence","crop","Understand suitability scores and source caveats.","Crop Intelligence"),
        ("Rotation Planner","rotation","Compare explainable multi-season sequences.","Rotation Planner"),
        ("Sustainability","sustainability","Review descriptive rotation characteristics.","Sustainability"),
        ("District Map","map","Explore supported locations and coordinates.","District Map"),
    ]
    for start in range(0, len(cards), 3):
        cols = st.columns(3)
        for col, (title, icon, description, key) in zip(cols, cards[start:start+3]):
            with col:
                st.markdown(f'<div class="mini-card"><div class="icon">{icons[icon]}</div><strong>{title}</strong><p>{description}</p></div>', unsafe_allow_html=True)
                if st.button("Open preview  →", key=f"open_{key}", use_container_width=True):
                    module_popup(key, selection)
    st.write("")
    section_header("DATA CONFIDENCE", "Know what informs the view", "Source and coverage stay visible alongside the numbers.")
    if data_ready:
        provenance_panel(selection)
    st.markdown('<div class="footer">KAIRO · Climate intelligence for more informed agricultural planning</div>', unsafe_allow_html=True)

elif page == "Farm Profile":
    section_header("FARM SETUP", "Tell us about your field", "These details personalize the rule-based assessment. Your profile stays in this Streamlit session.")
    existing = profile or {}
    with st.form("farm_profile_form", border=True):
        c1,c2 = st.columns(2)
        district = c1.selectbox("District", DISTRICT_NAMES, index=DISTRICT_NAMES.index(existing.get("district", st.session_state.selected_district)))
        area = c2.number_input("Farm area (hectares)", min_value=.01, max_value=10000.0, value=float(existing.get("area_ha",1.0)), step=.1)
        c3,c4 = st.columns(2)
        soil_options = ["Select soil type"] + list(SOILS)
        prior_soil = existing.get("soil_type")
        soil_index = soil_options.index(prior_soil) if prior_soil in soil_options else 0
        soil = c3.selectbox("Soil type", soil_options, index=soil_index, help="Use a soil test where possible. Exact soil matching in this prototype is simplified.")
        irrigation_options = ["Select water availability", "rainfed", "irrigated"]
        prior_water = existing.get("water_availability")
        water_index = irrigation_options.index(prior_water) if prior_water in irrigation_options else 0
        water = c4.selectbox("Water availability", irrigation_options, index=water_index)
        crop_names = ["Not provided"] + [crop["crop_name"] for crop in load_crop_records()]
        prior_crop = existing.get("previous_crop")
        prior_crop_index = crop_names.index(prior_crop) if prior_crop in crop_names else 0
        previous = st.selectbox("Previous crop (optional)", crop_names, index=prior_crop_index)
        st.caption("Previous crop is recorded for your reference; the current rotation engine does not yet use crop history in its ranking.")
        submitted = st.form_submit_button("Save farm profile", use_container_width=True)
    if submitted:
        if soil == "Select soil type" or water == "Select water availability":
            st.error("Choose a soil type and water availability before saving your profile.")
        else:
            st.session_state.farm_profile = {
                "district":district, "coordinates":get_district(district), "area_ha":area,
                "soil_type":soil, "water_availability":water,
                "previous_crop":None if previous == "Not provided" else previous,
            }
            st.session_state.selected_district = district
            st.success("Farm profile saved for this session.")
            st.rerun()
    st.write("")
    section_header("PROFILE SUMMARY", "Current saved details")
    render_profile_summary(profile)
    if profile and profile.get("water_availability") == "irrigated":
        st.warning("The current crop reference records are rainfed-only. Irrigated farms may receive a zero water match; the assessment will show that clearly.")

elif page == "Climate Intelligence":
    section_header("NASA POWER", "Climate intelligence", "Daily observations and seasonal summaries for the selected district.")
    district = st.selectbox("District", DISTRICT_NAMES, index=DISTRICT_NAMES.index(active_district), key="climate_district")
    if data_ready:
        render_climate(district)
    else:
        st.info("Climate records are not available in the current workspace.")

elif page == "Crop Intelligence":
    section_header("CROP SUITABILITY", "Compare crop fit with current conditions", "Each score is an explainable heuristic from the project engine; it is not a probability of success.")
    render_profile_summary(profile)
    season = st.selectbox("Season", ["kharif","rabi","summer"], key="crop_season")
    if profile:
        render_crop_results(profile, season)
    else:
        st.info("Save a farm profile to run a crop assessment.")

elif page == "Rotation Planner":
    section_header("ROTATION STRATEGY", "Plan across seasons", "See how suitability, crop-family repetition and legume transitions affect the ranking.")
    render_profile_summary(profile)
    if profile:
        render_rotations(profile)
    else:
        st.info("Save a farm profile to run the rotation engine.")

elif page == "Sustainability":
    section_header("SUSTAINABILITY", "A transparent view of rotation characteristics", "The current project does not calculate measured sustainability impacts.")
    st.markdown('<div class="warning-note"><b>Evidence boundary:</b> no water savings, carbon reduction, yield change, or soil restoration are estimated by this dashboard.</div>', unsafe_allow_html=True)
    if profile and profile.get("soil_type"):
        conditions = rotation_conditions(profile["district"])
        plans = generate_crop_rotations(load_crop_records(), conditions, engine_profile(profile), top_n=1) if len(conditions) >= 2 else []
        if plans:
            sequence = plans[0]["crop_sequence"]
            crop_by_id = {crop["crop_id"]:crop for crop in load_crop_records()}
            distinct = len({item["crop_id"] for item in sequence})
            legume_count = sum(bool(crop_by_id.get(item["crop_id"],{}).get("legume")) for item in sequence)
            a,b = st.columns(2)
            a.metric("Distinct crops in top sequence", f"{distinct} / {len(sequence)}")
            b.metric("Legume crops in sequence", f"{legume_count} / {len(sequence)}")
            st.caption("Descriptive counts derived from the rotation engine output. They are not measured benefits or proof of improved soil health.")
        else:
            st.info("No supported rotation sequence is currently available for this profile.")
    else:
        st.info("Complete the farm profile to view descriptive characteristics from a generated rotation.")

elif page == "District Map":
    section_header("REGIONAL COVERAGE", "Karnataka district explorer", "Select a supported district and review its representative reference location.")
    district = st.selectbox("Selected district", DISTRICT_NAMES, index=DISTRICT_NAMES.index(active_district), key="map_district")
    render_map(district)
    if data_ready:
        subset = climate_summaries[climate_summaries.location == district]
        if not subset.empty:
            st.metric("January 2025 mean temperature", fmt(subset.iloc[0].average_temperature_c,1," °C"))
            provenance_panel(district)

st.divider()
st.markdown('<div class="footer">KAIRO · NASA climate data is gridded and modelled · Recommendations are decision support; consult local agricultural experts and soil-test results.</div>', unsafe_allow_html=True)
