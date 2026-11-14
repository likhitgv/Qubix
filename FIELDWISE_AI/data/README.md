
# FIELDWISE AI – NASA Environmental Data

## 1. Dataset Overview

This dataset contains daily environmental data for five locations in Karnataka, India, for January 2025.

Data sources:
- NASA POWER Daily API
- NASA GPM IMERG Final Daily V07B

## 2. Locations

| Location | Latitude | Longitude |
|---|---:|---:|
| Ballari | 15.1394 | 76.9214 |
| Shivamogga | 13.9326 | 75.5750 |
| Vijayapura | 16.8275 | 75.7253 |
| Belagavi | 15.8521 | 74.5045 |
| Dharwad | 15.4589 | 75.0078 |

Coordinates represent approximate city-centre points.

## 3. Data Sources and Variables

### NASA POWER
- T2M: Temperature at 2 metres (°C)
- PRECTOTCORR: Corrected precipitation (mm/day)
- API: NASA POWER Daily Point API
- Community: AG

### NASA GPM IMERG
- Product: GPM_3IMERGDF
- Version: 07B
- Variable: precipitation
- Description: Daily mean precipitation rate
- Unit: mm/day
- Spatial resolution: 0.1° × 0.1°
- DOI: 10.5067/GPM/IMERGDF/DAY/07

GPM values were extracted from the nearest grid cell to each location.

## 4. Combined Dataset

File:
data/combined/nasa_environmental_data_january_2025.csv

Columns:
- date
- location
- latitude
- longitude
- temperature_c
- nasa_power_rainfall_mm
- gpm_rainfall_mm
- source

## 5. Coverage

- Start date: 2025-01-01
- End date: 2025-01-31
- Locations: 5
- Days: 31
- Expected records: 155

## 6. Validation

- Total records: 155
- Duplicate date/location records: 0
- Missing values: 0
- Negative GPM rainfall values: 0
- Negative NASA POWER rainfall values: 0

## 7. Important Notes

- NASA POWER and GPM are different precipitation products.
- Their rainfall estimates should be compared, not assumed to be identical.
- GPM values represent nearest-grid-cell estimates, not ground station measurements.
- The dataset covers January 2025 only.
- Original source CSV files and GPM NetCDF4 files are retained separately.
