# FIELDWISE AI - Front-End Build List

**For:** Member 4 (Frontend & Dashboard Developer)
**Project:** FIELDWISE AI - NASA Space Apps Challenge 2026, "Field Shift: Adapting Farms with NASA Data"
**Stack:** Python 3.11, Streamlit, Plotly, Folium + streamlit-folium, pandas, requests

## 1. Goal

Build one Streamlit app where a farmer picks a district, enters farm details, and sees NASA-based climate data, ranked crop rotations, and a clear explanation, with the data source and limitations shown on every result.

**Rule:** UI code lives in `app.py` and `dashboard/`. Do NOT put data or scoring logic in the UI. Call the module functions below and display their output.

## 2. What already exists (do not rebuild)

| Need | Function | File |
|---|---|---|
| District list and coordinates | `DISTRICTS`, `get_district(name)`, `get_locations()` | `config/districts.py` |
| Fetch live NASA POWER data | `fetch_for_district(name, start, end)` | `modules/nasa_api.py` |
| NASA data to analysis DataFrame | `to_climate_dataframe(result, name)` | `modules/nasa_api.py` |
| Offline fallback data | `load_sample_data()` (rows labelled `SAMPLE`) | `modules/nasa_api.py` |
| Clean and summarise climate data | `clean_climate_data`, `generate_climate_summary`, `generate_district_summaries`, `generate_district_trends` | `modules/data_analysis.py` |
| Plotly charts | `create_temperature_chart(df)`, `create_rainfall_chart(df)` | `modules/data_analysis.py` |
| Crop reference data | `load_crop_database()` | `modules/crop_database.py` |
| Rank crops | `rank_crops_v2(...)` | `modules/crop_suitability_v2.py` |
| Rotation recommendations | `generate_crop_rotations(crops, seasonal_conditions, farm_profile, top_n=5)` | `modules/rotation_engine.py` |
| Sustainability view | NOT BUILT YET (`modules/sustainability.py` is a stub) | - |

Example rotation call:

```python
crops = load_crop_database()
seasonal_conditions = [
    {"season": "kharif", "environmental_data": {"temperature_c": 28, "rainfall_mm": 480}},
    {"season": "rabi",   "environmental_data": {"temperature_c": 25, "rainfall_mm": 400}},
]
farm = {"soil_type": "loam", "water_availability": "rainfed"}
rotations = generate_crop_rotations(crops, seasonal_conditions, farm, top_n=3)
```

Each rotation contains `rank`, `overall_rotation_score`, `crop_sequence` (list of crops with `season`, `crop_name`, `suitability_score`, `suitability_details`, `source_urls`, `source_verification`, `source_warnings`), `explanations` and `limitations`.

## 3. Setup (do first)

1. Add to `requirements.txt`: `streamlit`, `plotly`, `folium`, `streamlit-folium` (keep `requests`, `pandas`).
2. `py -3.11 -m pip install -r requirements.txt`
3. Run with `py -3.11 -m streamlit run app.py` from the project root.
4. Replace the "Welcome" stub in `app.py` with the page layout below.

## 4. Build list (in this order)

### Step 1 - App shell (`app.py`)
- [ ] Page title, logo from `assets/logo.png`, sidebar navigation.
- [ ] Pages: **Farm Input**, **Climate**, **Crop Recommendations**, **Map**, **About & Data Sources**.
- [ ] Shared `st.session_state` for the farm profile and loaded data.

### Step 2 - Farmer input form (`dashboard/farm_input.py`)
- [ ] District dropdown from `DISTRICTS` (Ballari, Shivamogga, Vijayapura, Belagavi, Dharwad).
- [ ] Farm area (number, hectares, > 0).
- [ ] Soil type dropdown. **Use the exact soil names in the crop database**: `sandy-loam`, `loam`, `clay-loam`, `silty-loam`, `red-soil`, `black-soil`, `alluvial`, `sandy`, `loamy`. Do not let users type free text. (A soil-name mismatch currently breaks matching; ask Member 3 to confirm the final list.)
- [ ] Current crop (dropdown from the crop database).
- [ ] Water availability: `rainfed` or `irrigated` (match the database spelling).
- [ ] Season and farmer priorities (e.g. low water, soil health, diversity).
- [ ] Validate inputs and show clear error messages; return one farm-profile dict.

### Step 3 - Climate page (`dashboard/climate_dashboard.py`)
- [ ] "Fetch NASA data" button calling `fetch_for_district` then `to_climate_dataframe`, with a spinner.
- [ ] Handle `NASAPowerError`: show the message and offer the labelled SAMPLE fallback.
- [ ] Summary cards (average, min, max temperature; total rainfall) from `generate_climate_summary`.
- [ ] Temperature and rainfall charts (`create_temperature_chart`, `create_rainfall_chart`) via `st.plotly_chart`.
- [ ] District comparison table/chart using `generate_district_summaries`.
- [ ] Data panel showing source, retrieval date, period, units and missing-value counts (from `result["metadata"]`).

### Step 4 - Crop recommendations (`dashboard/crop_dashboard.py`)
- [ ] Build `seasonal_conditions` from the climate data (see data note in section 6).
- [ ] Call `generate_crop_rotations`; show ranked rotation cards: rank, score, crop sequence by season, explanation.
- [ ] Expandable "Why this score?" per crop showing `suitability_details` components (temperature, rainfall, soil, water, season).
- [ ] Rotation comparison table/bar chart.
- [ ] Show `limitations` on every result.
- [ ] **Show source warnings.** Groundnut, chickpea and maize are flagged "NEEDS VERIFICATION"; display a visible badge when `source_verification` or `source_warnings` is present.

### Step 5 - Map (`dashboard/map_view.py`)
- [ ] Folium map centred on Karnataka with markers for the five districts (`st.components`/`streamlit-folium`).
- [ ] Popup with district name, coordinates and latest summary.
- [ ] Highlight the selected district.

### Step 6 - Sustainability panel (after Member 3/1 provide `sustainability.py`)
- [ ] Water demand comparison per crop/rotation; legume inclusion; crop diversity.
- [ ] Label every figure as an **estimate**. Never show it as a measured result.

### Step 7 - About & Data Sources page
- [ ] Source list: NASA POWER (name, endpoint, what it is), crop database sources with accessed dates.
- [ ] Limitations list (see section 5).

### Step 8 - Polish and test
- [ ] Layout works on the team's Windows laptop from a clean start.
- [ ] Test: valid and invalid inputs, API timeout / offline, empty data, every district.
- [ ] Download button for results (CSV; PDF optional).
- [ ] Optional: AI advisor panel (see section 7).

## 5. Required honesty rules (judging and brief requirements)

Every page must follow these:
- Say NASA POWER is a **gridded, modelled** product (satellite and reanalysis), not a field or station measurement.
- Always show source, units, and data dates next to numbers.
- If using sample data, show a clear **SAMPLE / DEMO DATA** banner; never present it as live NASA data.
- Recommendations are **decision support**, not agronomic advice. Show "consult a local agronomist and soil test".
- Do not claim yield increases, water savings or soil restoration.
- Show the flagged-crop warnings (section 4, Step 4).

## 6. Known data issues to handle

1. **Only January 2025 NASA data is stored.** Rotations need kharif and rabi conditions. Until full-year data is fetched (Member 1), build the form to accept a date range and compute seasonal averages from whatever period was fetched, and say which period was used.
2. **Soil names:** use the dropdown list in Step 2 only.
3. **Water matching is exact:** `irrigated` farms currently score 0 on water for rainfed-only crops. Display this in the explanation; don't hide it.
4. **Chickpea rainfall range** is flagged and may over-penalise; show its warning.

## 7. Optional: AI advisor panel

Add a panel that explains the ranked rotations in plain language (English, optionally Kannada).
- The AI may only use numbers the modules computed; it must say when data is missing and must not invent yields or savings.
- Read the API key from an environment variable; never hard-code or commit it.
- If no key or no network, show a fixed template explanation instead.

## 8. Definition of done

- [ ] `streamlit run app.py` works from a fresh clone on Windows.
- [ ] Select district, enter farm, see climate charts, ranked rotations, explanations, map, sources, limitations.
- [ ] Offline fallback works and is clearly labelled.
- [ ] No logic duplicated from `modules/`.
- [ ] Short handoff note: files created, how to run, tests done, known limitations.

## 9. Who to ask

| Question | Ask |
|---|---|
| NASA data, fetch functions, date ranges | Member 1 |
| Analysis output, charts | Member 2 |
| Crop data, scoring, rotations, soil names | Member 3 |
| Testing, bug reports | Member 5 |
