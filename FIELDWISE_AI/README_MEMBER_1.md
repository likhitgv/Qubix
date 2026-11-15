# Member 1 -- NASA Data Collection and Integration

**Project:** KAIRO\
**Role:** Member 1 -- NASA Data Collection Developer\
**Repository:** [Qubix](https://github.com/likhitgv/Qubix)\
**Data period:** 1 January 2025 -- 31 January 2025\
**Data retrieval date:** 14 November 2026

------------------------------------------------------------------------

## 1. Role and responsibility

Member 1 is responsible for collecting, processing, validating, and
preparing environmental data from NASA sources for use by the FIELDWISE
AI project.

The module provides daily climate information for five Karnataka
locations, including temperature and rainfall data. It also prepares a
consolidated dataset and a simplified CSV handoff for the environmental
analysis module.

## 2. NASA data sources

### NASA POWER -- Daily Point API

NASA POWER provides daily meteorological and solar data for the selected
locations.

-   **API:** `https://power.larc.nasa.gov/api/temporal/daily/point`
-   **Temporal resolution:** Daily
-   **Community:** `AG`
-   **Parameters collected:**

  -----------------------------------------------------------------------
  NASA POWER parameter    Meaning                 Unit
  ----------------------- ----------------------- -----------------------
  `T2M`                   Temperature at 2 metres °C

  `T2M_MAX`               Maximum temperature at  °C
                          2 metres                

  `T2M_MIN`               Minimum temperature at  °C
                          2 metres                

  `PRECTOTCORR`           Corrected precipitation mm/day

  `RH2M`                  Relative humidity at 2  \%
                          metres                  

  `ALLSKY_SFC_SW_DWN`     All-sky surface         MJ/m²/day
                          shortwave downward      
                          radiation               
  -----------------------------------------------------------------------

### NASA GPM IMERG -- Final Daily

NASA Global Precipitation Measurement (GPM) IMERG Final Daily data is
used as a satellite-based rainfall source.

-   **Product:** `GPM_3IMERGDF`
-   **Version:** 07 (granules identified as V07B)
-   **DOI:** `10.5067/GPM/IMERGDF/DAY/07`
-   **Temporal resolution:** Daily
-   **Grid resolution:** 0.1° × 0.1°
-   **Variable used:** `precipitation`
-   **Unit:** mm/day
-   **Access method:** NASA Earthdata authentication and the
    `earthaccess` Python package

GPM data is extracted from the nearest grid cell to each selected
location.

## 3. Locations covered

  Location       Latitude   Longitude
  ------------ ---------- -----------
  Ballari         15.1394     76.9214
  Shivamogga      13.9326     75.5750
  Vijayapura      16.8275     75.7253
  Belagavi        15.8521     74.5045
  Dharwad         15.4589     75.0078

The GPM nearest-grid coordinates are not identical to the city-centre
coordinates because the satellite product uses a 0.1° grid.

## 4. Data period and volume

The collected datasets cover **1--31 January 2025**.

-   5 locations
-   31 daily records per location
-   155 location-date records per complete dataset

## 5. Main implementation files

  ------------------------------------------------------------------------------
  File                                       Responsibility
  ------------------------------------------ -----------------------------------
  `modules/nasa_api.py`                      NASA POWER API integration, request
                                             handling, validation and data
                                             preparation

  `examples/nasa_power_demo.py`              Demonstrates NASA POWER data
                                             retrieval

  `examples/combine_environmental_data.py`   Combines NASA POWER and GPM records

  `examples/create_member2_handoff.py`       Creates the simplified CSV for
                                             Member 2

  `gpm_download_test.py`                     Checks NASA Earthdata
                                             authentication and GPM granule
                                             download

  `tests/test_nasa_api.py`                   Tests NASA POWER API behaviour

  `tests/test_gpm_data.py`                   Validates the prepared GPM rainfall
                                             dataset
  ------------------------------------------------------------------------------

## 6. Generated datasets

### NASA POWER data

Location-specific CSV files and a consolidated file are stored under:

``` text
data/nasa_power/
```

The consolidated NASA POWER dataset is:

``` text
data/nasa_power/nasa_power_consolidated.csv
```

The NASA POWER records include the location, coordinates, date and
requested meteorological parameters. Source and retrieval details are
documented in the data documentation and provenance metadata.

### NASA GPM rainfall data

The extracted daily rainfall dataset is:

``` text
data/gpm/gpm_rainfall_january_2025.csv
```

It contains 155 records covering five locations and 31 dates.

Raw GPM NetCDF4 granules are kept separately and are excluded from Git
by the repository's `.gitignore` rules.

### Combined environmental dataset

``` text
data/combined/nasa_environmental_data_january_2025.csv
```

The combined dataset contains:

``` text
date
location
latitude
longitude
temperature_c
nasa_power_rainfall_mm
gpm_rainfall_mm
source
```

### Member 2 handoff dataset

``` text
data/handoff/FIELDWISE_AI_member2_january_2025.csv
```

The handoff CSV uses the following columns:

``` text
date
location
latitude
longitude
temperature_c
rainfall_mm
source
```

Temperature is sourced from NASA POWER `T2M`; the handoff rainfall field
uses the extracted NASA GPM precipitation values.

## 7. Processing and validation

The data preparation workflow includes:

1.  Request daily meteorological data from NASA POWER for the five
    selected locations.
2.  Authenticate with NASA Earthdata and access the GPM IMERG Final
    Daily product.
3.  Extract daily precipitation values from the nearest GPM grid cell
    for each location.
4.  Normalize dates and match records by location and date.
5.  Combine the datasets and prepare the Member 2 handoff CSV.
6.  Validate record counts, required columns, missing values, duplicate
    location-date records, numeric values and non-negative rainfall
    values.

The prepared January datasets contain 155 records for five locations,
with 31 records per location.

## 8. Tests and verification

The project test suite was run after synchronizing the local `main`
branch with `origin/main`.

Command:

``` powershell
python -m unittest discover -s tests -v
```

**Recorded result:** 55 tests ran successfully (`OK`).

The GPM dataset checks include required columns, record count, location
coverage, date coverage, duplicate keys, missing values, numeric
rainfall values, non-negative rainfall values, source/version
information and coordinate validity.

The Git working tree was also checked and reported clean, with the local
`main` branch up to date with `origin/main`.

## 9. Dependencies and authentication

The project uses Python packages including:

-   `requests`
-   `earthaccess`
-   `xarray`
-   `netCDF4`

NASA GPM access requires a NASA Earthdata Login. Authentication is
performed interactively through `earthaccess`; credentials should not be
committed to the repository.

Install project dependencies from the repository root with:

``` powershell
pip install -r requirements.txt
```

## 10. Data limitations and considerations

-   The data period documented here is January 2025 only; it should not
    be treated as a multi-season or year-round climate dataset.
-   NASA POWER and NASA GPM are gridded or model-derived/satellite
    products, not direct measurements from local weather stations.
-   GPM values are extracted from the nearest 0.1° grid cell. They are
    point-neighbour estimates and are not district-wide rainfall
    averages.
-   Satellite rainfall estimates can differ from local observations,
    especially when rainfall amounts are small.
-   The combined dataset retains both NASA POWER precipitation and GPM
    precipitation columns so that their values and sources remain
    distinguishable.
-   Any analysis or crop recommendation should account for the limited
    date range and the spatial resolution of the source data.

## 11. Member 1 deliverables

-   NASA POWER Daily Point API integration.
-   NASA GPM IMERG Final Daily data access and extraction workflow.
-   January 2025 climate datasets for five Karnataka locations.
-   Combined NASA POWER and GPM environmental dataset.
-   Simplified CSV handoff for Member 2.
-   Data validation tests and supporting scripts.
-   Data source, methodology and limitation documentation.

------------------------------------------------------------------------

**Member 1 status:** Data collection, dataset preparation, validation
and handoff artifacts have been completed and committed to the project
workflow.
