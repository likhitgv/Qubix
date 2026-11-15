
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from pathlib import Path

from modules.data_analysis import (
    load_nasa_power_data,
    generate_district_summaries,
    generate_district_trends,
    create_temperature_chart,
    create_rainfall_chart
)
from modules.crop_database import load_crop_database
from modules.crop_suitability_v2 import rank_crops_v2
from modules.rotation_engine import generate_crop_rotations

# ============================================================
# FIELDWISE AI
# NASA SPACE APPS CHALLENGE 2026
# Main Streamlit Dashboard - Member 4
# ============================================================

# -------------------- PAGE CONFIGURATION --------------------

st.set_page_config(
    page_title="FIELDWISE AI | Smart Agriculture",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------- THEME AND CUSTOM CSS --------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@500;600;700&display=swap');

:root {
    --background: #F7F1F5;
    --sidebar: #38283E;
    --plum: #513B56;
    --deep-plum: #49334F;
    --mauve: #876783;
    --rose: #D6A9B8;
    --blush: #F3E1E8;
    --lavender: #EAE1EF;
    --lavender-border: #D7C8DF;
    --ivory: #FFF8F0;
    --text: #403344;
    --muted: #806F81;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background-color: var(--background);
    color: var(--text);
}

.block-container {
    max-width: 1450px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* SIDEBAR */

section[data-testid="stSidebar"] {
    background-color: var(--sidebar);
}

section[data-testid="stSidebar"] * {
    color: var(--ivory);
}

section[data-testid="stSidebar"] h1 {
    font-family: 'Playfair Display', serif;
    color: #F2DCE6;
    font-size: 29px;
}

section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #DCC9D9;
}

/* MAIN HEADINGS */

h1, h2, h3 {
    font-family: 'Playfair Display', serif !important;
    color: var(--plum) !important;
}

h1 {
    font-size: 37px !important;
}

h2 {
    font-size: 28px !important;
}

h3 {
    font-size: 21px !important;
}

p, li, label {
    color: var(--text);
}

/* HERO SECTION */

.st-key-hero {
    background-color: var(--deep-plum);
    border: 1px solid var(--deep-plum);
    border-radius: 22px;
    padding: 30px;
    margin-bottom: 22px;
}

.st-key-hero h1 {
    color: #FFF4EC !important;
    font-family: 'Playfair Display', serif !important;
    font-size: 48px !important;
    font-weight: 700 !important;
    line-height: 1.2;
}

.st-key-hero h2,
.st-key-hero h3 {
    color: #FFF4EC !important;
}

.st-key-hero p,
.st-key-hero span,
.st-key-hero label,
.st-key-hero [data-testid="stCaptionContainer"] {
    color: #F4DFE9 !important;
}

.st-key-hero [data-testid="stMarkdownContainer"] p {
    color: #F4DFE9 !important;
    font-size: 16px;
    line-height: 1.8;
}

/* GENERAL CARDS */

div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: #EEE6F1;
    border: 1px solid var(--lavender-border);
    border-radius: 16px;
    padding: 12px;
}

/* FEATURE CARDS */

.st-key-feature-farm,
.st-key-feature-climate,
.st-key-feature-crops,
.st-key-feature-rotation,
.st-key-feature-sustainability,
.st-key-feature-nasa {
    background-color: var(--lavender);
    border-radius: 16px;
    padding: 12px;
}

.st-key-feature-farm h3,
.st-key-feature-climate h3,
.st-key-feature-crops h3,
.st-key-feature-rotation h3,
.st-key-feature-sustainability h3,
.st-key-feature-nasa h3 {
    color: var(--plum) !important;
}

/* METRIC CARDS */

[data-testid="stMetric"] {
    background-color: var(--blush);
    border: 1px solid #E7C9D5;
    border-radius: 14px;
    padding: 16px;
}

[data-testid="stMetricLabel"] {
    color: #73576F !important;
}

[data-testid="stMetricValue"] {
    color: #634665 !important;
    font-weight: 700;
}

/* BUTTONS */

.stButton > button {
    background-color: var(--mauve);
    color: white;
    border: 1px solid var(--mauve);
    border-radius: 9px;
    font-weight: 600;
    padding: 8px 18px;
}

.stButton > button:hover {
    background-color: var(--deep-plum);
    color: white;
    border-color: var(--deep-plum);
}

/* INPUTS */

.stTextInput input,
.stNumberInput input,
.stDateInput input,
.stTextArea textarea {
    background-color: #FFFAFC;
    color: var(--text);
    border-radius: 8px;
}

[data-baseweb="select"] {
    background-color: #FFFAFC;
    border-radius: 8px;
}

/* TABS */

.stTabs [data-baseweb="tab"] {
    color: var(--plum);
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    color: var(--mauve) !important;
}

/* ALERTS AND DIVIDERS */

hr {
    border-color: #DDCEDF;
}

[data-testid="stAlert"] {
    border-radius: 12px;
}

/* FOOTER */

.footer-text {
    text-align: center;
    color: var(--muted);
    font-size: 13px;
    padding: 20px 0 5px 0;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTS
# ============================================================

DISTRICTS = {
    "Ballari": {
        "latitude": 15.1394,
        "longitude": 76.9214
    },
    "Shivamogga": {
        "latitude": 13.9299,
        "longitude": 75.5681
    },
    "Vijayapura": {
        "latitude": 16.8302,
        "longitude": 75.7100
    },
    "Belagavi": {
        "latitude": 15.8497,
        "longitude": 74.4977
    },
    "Dharwad": {
        "latitude": 15.4589,
        "longitude": 75.0078
    }
}

# ============================================================
# REUSABLE UI FUNCTIONS
# ============================================================

def section_title(title, description=None):
    st.subheader(title)

    if description:
        st.caption(description)


def feature_card(title, description, key):
    with st.container(border=True, key=key):
        st.markdown(f"### {title}")
        st.write(description)


def information_card(title, description, key):
    with st.container(border=True, key=key):
        st.markdown(f"### {title}")
        st.write(description)


def show_pending_message(module_name):
    st.info(
        f"{module_name} integration is pending. "
        "Results will appear here after the relevant team module "
        "is connected."
    )


def show_data_source(source):
    st.caption(f"Data source: {source}")


# ============================================================
# SESSION STATE
# ============================================================

if "farm_profile" not in st.session_state:
    st.session_state.farm_profile = None

if "climate_data" not in st.session_state:
    st.session_state.climate_data = None

if "crop_results" not in st.session_state:
    st.session_state.crop_results = None

if "rotation_results" not in st.session_state:
    st.session_state.rotation_results = None

if "sustainability_results" not in st.session_state:
    st.session_state.sustainability_results = None
# ============================================================
# MEMBER 2 - CLIMATE DATA INTEGRATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

SUMMARY_PATH = (
    BASE_DIR / "outputs" / "member3_handoff"
    / "district_climate_summary.csv"
)

TRENDS_PATH = (
    BASE_DIR / "outputs" / "member3_handoff"
    / "daily_climate_trends.csv"
)


@st.cache_data
def load_member2_climate_outputs():
    nasa_data_path = BASE_DIR / "data" / "nasa_power" / "nasa_power_consolidated.csv"

    climate_data, report = load_nasa_power_data(nasa_data_path)

    summary_data = pd.DataFrame(
        generate_district_summaries(climate_data)
    )

    trends_data = generate_district_trends(climate_data)

    return summary_data, trends_data

@st.cache_data
def load_seasonal_summary():
    """Load NASA POWER seasonal data for crop intelligence."""

    seasonal_path = (
        BASE_DIR / "data" / "nasa_power" / "seasonal_summary.csv"
    )

    if not seasonal_path.exists():
        raise FileNotFoundError(
            f"Seasonal NASA data not found: {seasonal_path}"
        )

    data = pd.read_csv(seasonal_path)

    required_columns = [
        "location",
        "season",
        "season_year",
        "complete",
        "temperature_c",
        "rainfall_mm",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Seasonal data is missing columns: {missing_columns}"
        )

    data["complete"] = (
        data["complete"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    data["season_year"] = pd.to_numeric(
        data["season_year"], errors="coerce"
    )

    data["temperature_c"] = pd.to_numeric(
        data["temperature_c"], errors="coerce"
    )

    data["rainfall_mm"] = pd.to_numeric(
        data["rainfall_mm"], errors="coerce"
    )

    return data


def get_latest_complete_seasons(district):
    """Return the latest complete NASA record for each season."""

    data = load_seasonal_summary()

    district_data = data[
        (data["location"].str.strip() == district)
        & data["complete"]
    ].copy()

    district_data = district_data.dropna(
        subset=["season_year", "temperature_c", "rainfall_mm"]
    )

    district_data = district_data.sort_values(
        "season_year", ascending=False
    )

    latest = district_data.drop_duplicates(
        subset=["season"], keep="first"
    )

    return latest

def prepare_engine_farm_profile(profile, season=None):
    """Convert dashboard farm values into crop-engine values."""

    soil_mapping = {
        "Red Soil": "red-soil",
        "Black Soil": "black-soil",
        "Sandy Soil": "sandy",
        "Alluvial Soil": "alluvial",
    }

    soil_type = soil_mapping.get(profile.get("soil_type"))

    # Current crop database contains rainfed requirements only.
    water_availability = (
        "rainfed"
        if profile.get("irrigation") == "Rainfed"
        else None
    )

    return {
        "soil_type": soil_type,
        "water_availability": water_availability,
        "season": season.lower() if season else None,
    }


def build_seasonal_conditions(district):
    """Prepare complete NASA seasonal records for rotation planning."""

    seasonal_data = get_latest_complete_seasons(district)

    conditions = []

    for _, row in seasonal_data.iterrows():
        conditions.append({
            "season": str(row["season"]).lower(),
            "environmental_data": {
                "temperature_c": float(row["temperature_c"]),
                "rainfall_mm": float(row["rainfall_mm"]),
            },
        })

    return conditions

def calculate_crop_recommendations(profile, season):
    """Calculate crop suitability using NASA seasonal data."""

    seasonal_data = get_latest_complete_seasons(
        profile["district"]
    )

    selected = seasonal_data[
        seasonal_data["season"].str.lower() == season.lower()
    ]

    if selected.empty:
        raise ValueError(
            f"No complete NASA data available for {season}."
        )

    row = selected.iloc[0]

    environmental_data = {
        "temperature_c": float(row["temperature_c"]),
        "rainfall_mm": float(row["rainfall_mm"]),
    }

    engine_profile = prepare_engine_farm_profile(
        profile, season
    )

    crops = load_crop_database()

    results = rank_crops_v2(
        crops=crops,
        environmental_data=environmental_data,
        farm_profile=engine_profile,
        minimum_data_coverage=60,
    )

    return results, int(row["season_year"])


def calculate_rotation_recommendations(profile):
    """Generate multi-season crop rotation strategies."""

    seasonal_conditions = build_seasonal_conditions(
        profile["district"]
    )

    if len(seasonal_conditions) < 2:
        raise ValueError(
            "At least two complete seasons are required."
        )

    engine_profile = prepare_engine_farm_profile(profile)

    crops = load_crop_database()

    return generate_crop_rotations(
        crops=crops,
        seasonal_conditions=seasonal_conditions,
        farm_profile=engine_profile,
        top_n=5,
        minimum_data_coverage=60,
    )


# ============================================================
# SIDEBAR NAVIGATION
# ============================================================

with st.sidebar:

    st.title("FIELDWISE AI")

    st.caption("NASA Space Apps Challenge 2026")

    st.divider()

    st.markdown("### NAVIGATION")

    page = st.radio(
        "Choose a dashboard",
        [
            "Overview",
            "Farm Profile",
            "Climate Analysis",
            "Crop Recommendations",
            "Crop Rotation",
            "Sustainability"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    st.markdown("### PROJECT")

    st.caption("Field Shift: Adapting Farms with NASA Data")

    st.caption("Initial coverage: Karnataka")

    st.divider()

    st.caption("Developed by Team FIELDWISE AI")


# ============================================================
# PAGE 1: OVERVIEW
# ============================================================

if page == "Overview":

    # HERO SECTION

    with st.container(border=True, key="hero"):

        st.caption("NASA SPACE APPS CHALLENGE 2026")

        st.title("Agriculture, Reimagined.")

        st.write(
            "Transform environmental intelligence into smarter "
            "crop decisions and sustainable farming strategies."
        )

        st.write("")

        st.markdown("**PLATFORM STATUS**")

        st.markdown("**● Initializing**")

        st.caption("Awaiting team integration")

    # OVERVIEW METRICS

    section_title(
        "Platform Overview",
        "Your workspace for climate-aware agricultural planning."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Target Districts",
            value="05"
        )
        st.caption("Initial Karnataka coverage")

    with col2:
        st.metric(
            label="Dashboard Modules",
            value="06"
        )
        st.caption("Agricultural decision-support areas")

    with col3:
        st.metric(
            label="Primary Data Source",
            value="NASA POWER"
        )
        st.caption("Climate data integration")

    st.write("")

    # WORKSPACE CARDS

    section_title(
        "Explore Your Workspace",
        "Choose a module to explore the platform."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        feature_card(
            "Farm Profile",
            "Enter your district, farm size, soil type "
            "and irrigation details.",
            "feature-farm"
        )

    with col2:
        feature_card(
            "Climate Analysis",
            "Explore climate indicators retrieved from "
            "NASA POWER data.",
            "feature-climate"
        )

    with col3:
        feature_card(
            "Crop Recommendations",
            "Explore crop suitability based on available "
            "climate and soil information.",
            "feature-crops"
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        feature_card(
            "Crop Rotation",
            "Understand crop sequences and rotation "
            "strategies for agricultural planning.",
            "feature-rotation"
        )

    with col2:
        feature_card(
            "Sustainability",
            "Explore sustainability indicators and "
            "resource-related insights.",
            "feature-sustainability"
        )

    with col3:
        feature_card(
            "NASA Data Integration",
            "Use environmental intelligence to support "
            "agricultural decisions.",
            "feature-nasa"
        )

    st.write("")

    # DISTRICT COVERAGE

    section_title(
        "Initial District Coverage",
        "The first version of FIELDWISE AI focuses on five Karnataka districts."
    )

    district_cols = st.columns(5)

    for index, district in enumerate(DISTRICTS.keys()):
        with district_cols[index]:
            with st.container(border=True):
                st.markdown(f"**{district}**")
                st.caption("Karnataka")

    # ABOUT THE PLATFORM

    st.write("")

    section_title("About FIELDWISE AI")

    with st.container(border=True):

        st.write(
            "FIELDWISE AI is a climate-aware agricultural "
            "decision-support platform. It aims to combine "
            "NASA environmental data, soil information and "
            "crop requirements to support informed farming decisions."
        )

        st.write(
            "**Technology:** Python | Streamlit | NASA POWER API | "
            "Pandas | NumPy | Plotly"
        )

        st.write(
            "**Workflow:** Farm Profile → Climate Analysis → "
            "Crop Suitability → Crop Rotation → Sustainability"
        )

        st.caption(
            "Recommendations will depend on the availability "
            "and quality of the connected data."
        )


# ============================================================
# PAGE 2: FARM PROFILE
# ============================================================

elif page == "Farm Profile":

    section_title(
        "Farm Profile",
        "Provide your farm details to begin the assessment."
    )

    st.write("")

    with st.container(border=True):

        st.markdown("### Location Details")

        with st.form("farm_profile_form"):

            district = st.selectbox(
                "Select District",
                list(DISTRICTS.keys())
            )

            farm_size = st.number_input(
                "Farm Size (acres)",
                min_value=0.1,
                max_value=10000.0,
                value=1.0,
                step=0.5
            )

            st.markdown("### Soil and Irrigation")

            soil_type = st.selectbox(
                "Soil Type",
                [
                    "Red Soil",
                    "Black Soil",
                    "Laterite Soil",
                    "Sandy Soil",
                    "Alluvial Soil",
                    "Other",
                    "Not Sure"
                ]
            )

            irrigation = st.selectbox(
                "Irrigation Availability",
                [
                    "Rainfed",
                    "Canal",
                    "Borewell",
                    "Drip Irrigation",
                    "Other"
                ]
            )

            farming_season = st.selectbox(
                "Farming Season",
                [
                    "Kharif",
                    "Rabi",
                    "Summer",
                    "Multiple Seasons",
                    "Not Sure"
                ]
            )

            crop_history = st.text_area(
                "Previously Grown Crops (Optional)",
                placeholder="Example: Paddy, Maize, Groundnut"
            )

            submitted = st.form_submit_button(
                "Save Farm Profile"
            )

            if submitted:

                st.session_state.farm_profile = {
                    "district": district,
                    "coordinates": DISTRICTS[district],
                    "farm_size_acres": farm_size,
                    "soil_type": soil_type,
                    "irrigation": irrigation,
                    "farming_season": farming_season,
                    "previous_crops": crop_history
                }

                st.success("Farm profile saved successfully.")

    if st.session_state.farm_profile:

        st.write("")

        section_title("Saved Farm Information")

        st.json(st.session_state.farm_profile)

        st.caption(
            "This profile is currently stored in the Streamlit session. "
            "Permanent database storage requires backend integration."
        )


# ============================================================
# PAGE 3: CLIMATE ANALYSIS
# ============================================================


# ============================================================
# PAGE 3: CLIMATE ANALYSIS
# ============================================================

elif page == "Climate Analysis":

    section_title(
        "Climate Analysis",
        "Explore environmental indicators for your selected district."
    )

    profile = st.session_state.farm_profile

    try:
        summary_data, trends_data = load_member2_climate_outputs()

        available_districts = sorted(
            summary_data["location"].dropna().unique()
        )

        if profile and profile["district"] in available_districts:

            selected_district = profile["district"]

            st.write(f"**Selected District:** {selected_district}")

            st.write(
                f"**Coordinates:** "
                f"{profile['coordinates']['latitude']}, "
                f"{profile['coordinates']['longitude']}"
            )

        else:

            selected_district = st.selectbox(
                "Select District",
                available_districts
            )

            if profile:
                st.warning(
                    "Saved farm district was not found in the "
                    "climate dataset. Select an available district."
                )
            else:
                st.info(
                    "Save a farm profile to automatically use its "
                    "district across the dashboard."
                )

        # Get selected district summary

        district_summary = summary_data[
            summary_data["location"] == selected_district
        ]

        if district_summary.empty:
            st.warning("No climate summary found for this district.")

        else:

            district_summary = district_summary.iloc[0]

            st.write("")
            section_title("Climate Indicators")

            # First row

            col1, col2, col3 = st.columns(3)

            with col1:
                with st.container(border=True):
                    st.metric(
                        "Average Temperature",
                        f"{district_summary['average_temperature_c']:.2f} °C"
                    )

            with col2:
                with st.container(border=True):
                    st.metric(
                        "Minimum Temperature",
                        f"{district_summary['minimum_temperature_c']:.2f} °C"
                    )

            with col3:
                with st.container(border=True):
                    st.metric(
                        "Maximum Temperature",
                        f"{district_summary['maximum_temperature_c']:.2f} °C"
                    )

            # Second row

            col1, col2, col3 = st.columns(3)

            with col1:
                with st.container(border=True):
                    st.metric(
                        "Total Rainfall",
                        f"{district_summary['total_rainfall_mm']:.2f} mm"
                    )

            with col2:
                with st.container(border=True):
                    st.metric(
                        "Average Humidity",
                        f"{district_summary['average_humidity_percent']:.2f}%"
                    )

            with col3:
                with st.container(border=True):
                    st.metric(
                        "Solar Radiation",
                        f"{district_summary['average_solar_radiation']:.2f} "
                        "MJ/m²/day"
                    )

            # Filter daily records

            district_trends = trends_data[
                trends_data["location"] == selected_district
            ].copy()

            st.write("")
            section_title("Climate Data Visualization")

            # Temperature chart

            st.markdown("### Temperature Trends")

            temperature_fig = create_temperature_chart(
                district_trends
            )

            temperature_fig.update_layout(
                template="plotly_white",
                title_font_color="#513B56",
                font_color="#403344",
                paper_bgcolor="#FFF8F0",
                plot_bgcolor="#FFF8F0",
                yaxis_title="Temperature (°C)"
            )

            st.plotly_chart(
                temperature_fig,
                use_container_width=True
            )

            # Rainfall chart

            st.markdown("### Rainfall Trends")

            rainfall_fig = create_rainfall_chart(
                district_trends
            )

            rainfall_fig.update_layout(
                template="plotly_white",
                title_font_color="#513B56",
                font_color="#403344",
                paper_bgcolor="#FFF8F0",
                plot_bgcolor="#FFF8F0",
                yaxis_title="Rainfall (mm/day)"
            )

            st.plotly_chart(
                rainfall_fig,
                use_container_width=True
            )

            # Daily data table

            with st.expander("View Daily Climate Records"):

                st.dataframe(
                    district_trends,
                    use_container_width=True
                )

            show_data_source(
                "NASA POWER | January 1–31, 2025 | "
                "Processed by Member 2"
            )

    except Exception as error:

        st.error(
            f"Unable to load climate data: {error}"
        )

        st.info(
            "Check whether Member 2's climate CSV files are "
            "available in outputs/member3_handoff."
        )


# ============================================================
# PAGE 4: CROP RECOMMENDATIONS
# ============================================================

elif page == "Crop Recommendations":

    section_title(
        "Crop Recommendations",
        "Explore crops based on farm conditions and environmental data."
    )

    profile = st.session_state.farm_profile

    if profile:

        st.write(f"**District:** {profile['district']}")
        st.write(f"**Soil Type:** {profile['soil_type']}")
        st.write(f"**Farm Size:** {profile['farm_size_acres']} acres")

    else:

        st.warning(
            "Please complete your Farm Profile before exploring "
            "personalized crop recommendations."
        )

    st.write("")

    section_title("Suitability Assessment")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("### Soil Compatibility")
            st.caption("Based on soil characteristics")

    with col2:
        with st.container(border=True):
            st.markdown("### Climate Compatibility")
            st.caption("Based on climate requirements")

    with col3:
        with st.container(border=True):
            st.markdown("### Crop Suitability")
            st.caption("Combined suitability assessment")

    st.write("")

    section_title("Recommended Crops")

    crop_results = st.session_state.crop_results

    if crop_results is not None:

        if isinstance(crop_results, pd.DataFrame):

            st.dataframe(
                crop_results,
                use_container_width=True
            )

        else:

            st.write(crop_results)

        st.caption(
            "Review the recommendation scores, explanations, "
            "assumptions and limitations provided by the crop engine."
        )

    else:

        show_pending_message("Crop suitability engine")

        st.write(
            "The crop recommendation module will provide "
            "candidate crops, suitability scores, rankings "
            "and explanations after integration."
        )


# ============================================================
# PAGE 5: CROP ROTATION
# ============================================================

elif page == "Crop Rotation":

    section_title(
        "Crop Rotation Planner",
        "Explore crop sequences for long-term agricultural planning."
    )

    profile = st.session_state.farm_profile

    if profile:

        st.write(f"**Selected District:** {profile['district']}")

    else:

        st.warning(
            "Complete your Farm Profile to provide the rotation "
            "engine with farm information."
        )

    st.write("")

    section_title("Rotation Planning Features")

    col1, col2, col3 = st.columns(3)

    with col1:
        feature_card(
            "Crop Sequence",
            "View suggested crop sequences across farming seasons.",
            "rotation-sequence"
        )

    with col2:
        feature_card(
            "Soil Considerations",
            "Understand how crop choices relate to soil health.",
            "rotation-soil"
        )

    with col3:
        feature_card(
            "Strategy Comparison",
            "Compare available crop rotation strategies.",
            "rotation-strategy"
        )

    st.write("")

    section_title("Rotation Results")

    rotation_results = st.session_state.rotation_results

    if rotation_results is not None:

        if isinstance(rotation_results, pd.DataFrame):

            st.dataframe(
                rotation_results,
                use_container_width=True
            )

        else:

            st.write(rotation_results)

    else:

        show_pending_message("Crop rotation engine")

        st.caption(
            "Rotation sequences and their explanations will appear "
            "after the team's rotation module is connected."
        )


# ============================================================
# PAGE 6: SUSTAINABILITY
# ============================================================

elif page == "Sustainability":

    section_title(
        "Sustainability Dashboard",
        "Explore environmental indicators that support sustainable farming."
    )

    st.write("")

    col1, col2, col3 = st.columns(3)

    with col1:
        feature_card(
            "Water Use",
            "Explore water-related indicators when supporting "
            "data is available.",
            "sustainability-water"
        )

    with col2:
        feature_card(
            "Climate Resilience",
            "Understand climate-related agricultural risks "
            "and considerations.",
            "sustainability-climate"
        )

    with col3:
        feature_card(
            "Soil Health",
            "Explore soil-related indicators and crop rotation "
            "considerations.",
            "sustainability-soil"
        )

    st.write("")

    section_title("Sustainability Indicators")

    sustainability_results = st.session_state.sustainability_results

    if sustainability_results is not None:

        if isinstance(sustainability_results, pd.DataFrame):

            st.dataframe(
                sustainability_results,
                use_container_width=True
            )

        else:

            st.write(sustainability_results)

    else:

        show_pending_message("Sustainability module")

        st.caption(
            "Sustainability indicators will be displayed after "
            "the team's calculation module is connected. "
            "No estimated savings or environmental benefits "
            "are assumed here."
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.markdown("""
<div class="footer-text">
    <strong>FIELDWISE AI</strong><br>
    NASA Space Apps Challenge 2026<br>
    Climate Intelligence for Sustainable Agriculture
</div>
""", unsafe_allow_html=True)
