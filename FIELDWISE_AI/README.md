# KAIRO

A project for climate-aware crop recommendations, crop suitability analysis,
crop rotation planning, and sustainable farming insights.

## What KAIRO does

Pick a Karnataka district (or click your farm on the map), describe your soil and
water, and KAIRO ranks multi-season crop rotations from NASA POWER climate data and a
sourced crop database. Every score is explained; crops whose reference data still
needs verification are flagged. Pages: Home, Farm, Recommendations, Climate, Map,
Sustainability, Advisor, About.

KAIRO is decision support, not agronomic advice. NASA POWER is a gridded, modelled
product, not a field measurement.

## Quick start

```bash
py -3.11 -m pip install -r requirements.txt
py -3.11 -m streamlit run app.py
py -3.11 -m unittest discover -s tests -t .
```

Optional AI explanations: copy `.env.example` to `.env` and add a free Groq, Gemini or OpenRouter key (never
commit it). Without it the Advisor page uses an offline template summary.

## Structure

```text
FIELDWISE_AI/            (folder name kept so existing clones keep working)
├── app.py               Streamlit UI only
├── config/              districts.py, soils.py (shared soil/water vocabulary)
├── dashboard/           theme.py (UI theme), map_view.py (Folium map)
├── modules/
│   ├── nasa_api.py          NASA POWER fetch + seasonal summaries
│   ├── kairo_service.py      farm profile -> plan; geotag -> nearest district
│   ├── crop_database.py / crop_suitability_v2.py / rotation_engine.py
│   ├── sustainability.py    rule-based rotation indicators (not measurements)
│   └── advisor.py           offline summary + optional grounded Claude explanation
├── data/                crop_database.csv, nasa_power/, gpm/, india_grid_2021_2025/ (Git LFS)
└── tests/               105 tests: unit, service, map, advisor, headless UI
```

## Known limitations

- Stored climate data covers 2024-2025 for five districts; kharif/rabi windows are assumptions.
- Groundnut, chickpea and maize rows are flagged NEEDS VERIFICATION (secondary sources).
- `soil_database.csv` is empty; soil matching uses the crop database's soil lists.
- Sustainability output is a structural indicator, not water, yield or soil measurement.
- The AI path is tested with a fake HTTP client only; it needs a free provider key to try live.

## NASA data collection (Module M2)

`modules/nasa_api.py` retrieves daily NASA POWER data (T2M, T2M_MAX, T2M_MIN,
PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN) for the districts in
`config/districts.py`.

```python
from modules.nasa_api import fetch_for_district, to_climate_dataframe

result = fetch_for_district("Dharwad", "2025-01-01", "2025-01-31")
df = to_climate_dataframe(result, "Dharwad")   # -> modules.data_analysis
print(result["metadata"]["units"], result["metadata"]["retrieved_at"])
```

Run the demo (from the project root) and the tests:

```bash
py -3.11 -m examples.nasa_power_demo
py -3.11 -m unittest tests.test_nasa_api
```

NASA POWER is a gridded product derived from satellite observations and
reanalysis models; it is not a direct field or weather-station measurement.
If the API is unreachable, use `load_sample_data()` and disclose the data as
SAMPLE/demo data.

## All-India coverage and the state → district picker

KAIRO can plan for any location in India, using the nearest cell of the downloaded NASA
POWER grid (882 points, ~56 km apart, daily 2021–2026). The Farm page lets you choose a
**state, then a district**, or drop a pin on the map.

- Only the five Karnataka districts (Ballari, Shivamogga, Vijayapura, Belagavi, Dharwad)
  were validated. Everywhere else shows a caution: the crop database was assembled for
  Karnataka and has only 6 crops.
- Districts come from Census 2011 boundaries (datameet/maps): Telangana appears under
  Andhra Pradesh and newer districts are missing.

Rebuild the derived data (outputs are small and committed; the daily grid is Git LFS):

```bash
py -3.11 -m examples.build_india_seasonal_summary
py -3.11 -m pip install pyshp
py -3.11 -m examples.build_india_districts <path-to>/2011_Dist
```

## Saved plans (SQLite)

Every recommendation is saved to a local SQLite file, `data/kairo.db` (created automatically,
ignored by git). Open or delete earlier plans from "Your saved plans" on the Recommendation page.
Set `KAIRO_DB_PATH` to store the file somewhere else. Only the field answers and the computed
plan are stored; the crop and climate reference data remain CSV files.

## Use of AI (disclosure)

This project used AI tools. Anthropic's Claude (through Claude Code) helped the team write and review code,
tests and documentation and draft the interface; the team directed the work and reviewed the results. An
optional Advisor feature can send KAIRO's own computed results to a hosted language model (Groq by default,
key in `.env`) to explain them; the reply is accepted only if every number matches KAIRO's computed data.
Crop reference data and all weather data come from the cited sources, not from AI. See `docs/Submission.md`
for the NASA Space Apps submission text.
