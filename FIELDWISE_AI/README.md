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


