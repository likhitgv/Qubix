# FIELDWISE_AI

A project for climate-aware crop recommendations, crop suitability analysis,
crop rotation planning, and sustainable farming insights.

## Project structure

```text
FIELDWISE_AI/
├── app.py
├── requirements.txt
├── README.md
├── config/
│   └── districts.py
├── data/
│   ├── crop_database.csv
│   └── soil_database.csv
├── modules/
│   ├── nasa_api.py
│   ├── data_analysis.py
│   ├── crop_database.py
│   ├── crop_suitability.py
│   ├── rotation_engine.py
│   └── sustainability.py
├── dashboard/
│   ├── farm_input.py
│   ├── climate_dashboard.py
│   ├── crop_dashboard.py
│   └── map_view.py
├── tests/
│   └── test_cases.py
└── assets/
    └── logo.png
```

## Setup

1. Clone this repository.
2. Create and activate a virtual environment.
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:

   ```bash
   python app.py
   ```

## Development

Implement the modules in `modules/`, dashboard components in `dashboard/`,
and add automated tests in `tests/`.

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
