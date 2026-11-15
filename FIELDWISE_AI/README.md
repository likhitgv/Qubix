# Kyro

A project for climate-aware crop recommendations, crop suitability analysis,
crop rotation planning, and sustainable farming insights.

## What Kyro does

Pick a Karnataka district (or click your farm on the map), describe your soil and
water, and Kyro ranks multi-season crop rotations from NASA POWER climate data and a
sourced crop database. Every score is explained; crops whose reference data still
needs verification are flagged. Pages: Home, Farm, Recommendations, Climate, Map,
Sustainability, Advisor, About.

Kyro is decision support, not agronomic advice. NASA POWER is a gridded, modelled
product, not a field measurement.

## Quick start

```bash
py -3.11 -m pip install -r requirements.txt
py -3.11 -m streamlit run app.py
py -3.11 -m unittest discover -s tests -t .
```

Optional AI explanations: set the `ANTHROPIC_API_KEY` environment variable (never
commit it). Without it the Advisor page uses an offline template summary.

## Structure

```text
FIELDWISE_AI/            (folder name kept so existing clones keep working)
├── app.py               Streamlit UI only
├── config/              districts.py, soils.py (shared soil/water vocabulary)
├── dashboard/           theme.py (UI theme), map_view.py (Folium map)
├── modules/
│   ├── nasa_api.py          NASA POWER fetch + seasonal summaries
│   ├── kyro_service.py      farm profile -> plan; geotag -> nearest district
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
- The AI path is tested with a fake client only; it needs a real key to try live.

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
