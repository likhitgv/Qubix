# Member 1 Handoff - NASA Data Collection (M2)

## Files
- `modules/nasa_api.py` - retrieval module
- `config/districts.py` - 5 Karnataka districts (`DISTRICTS`, `get_district`, `get_locations`)
- `examples/nasa_power_demo.py` - usage example (writes `data/nasa_power/*`)
- `tests/test_nasa_api.py` - 18 unit tests (mocked network)
- `data/nasa_power/` - per-district CSVs, `nasa_power_consolidated.csv`, `provenance.json`

## Functions
| Function | Input | Output |
|---|---|---|
| `fetch_power_daily(lat, lon, start, end, parameters=None)` | coords, `YYYY-MM-DD` dates | dict: `records` (list of `{date, <var>: float/None}`), `metadata` |
| `fetch_for_locations({name:(lat,lon)}, start, end)` | dict | `{name: result}` |
| `fetch_for_district(name, start, end)` | district name | result dict |
| `to_climate_dataframe(result, location)` | result | wide DataFrame, works directly with `clean_climate_data()` |
| `to_long_dataframe(result, location)` | result | rows of date/variable/value/unit/source/retrieved_at |
| `load_sample_data()` | - | offline fallback, `source == "SAMPLE"` |

`metadata` holds: source, endpoint, data_nature, retrieved_at (UTC), start/end,
units, descriptions, missing_counts, is_sample_data, processing_steps.

## Units
T2M/T2M_MAX/T2M_MIN: C; PRECTOTCORR: mm/day; RH2M: %; ALLSKY_SFC_SW_DWN: MJ/m^2/day.
Missing values (-999 / null) become `None` / NaN.

## Behaviour
Input validation; timeout, HTTP, JSON, empty and API-message errors raise
`NASAPowerError`; transient errors retried (default 2), 4xx (except 429) not.

## Run
`py -3.11 -m unittest tests.test_nasa_api` (18 pass) and
`py -3.11 -m examples.nasa_power_demo` (live; verified for all 5 districts, Jan 2025).

## Limitations
- NASA POWER is gridded/modelled data, not field measurements.
- Only NASA POWER; GPM / SMAP / MODIS not implemented (optional).
- Demo period is Jan 2025 only; rain is ~0 in that dry-season month.
- Per-district CSVs now use ISO dates (`2025-01-01`) and `date,location,...` column order.
