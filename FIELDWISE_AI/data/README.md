# \# Kyro – NASA Environmental Data Documentation

# 

# \## 1. Dataset Overview

# 

# This dataset contains daily environmental data collected for five locations in Karnataka, India, covering January 1–31, 2025.

# 

# The dataset combines temperature and rainfall information from two NASA data sources:

# 

# \- NASA POWER Daily API

# \- NASA GPM IMERG Final Daily V07B

# 

# \*\*Data retrieval date:\*\* 2026-11-14

# 

# \*\*Reporting period:\*\* 2025-01-01 to 2025-01-31

# 

# \## 2. Locations and Coordinates

# 

# The following five locations were used for environmental data collection.

# 

# | Location | Latitude | Longitude |

# |---|---:|---:|

# | Ballari | 15.1394 | 76.9214 |

# | Shivamogga | 13.9326 | 75.5750 |

# | Vijayapura | 16.8275 | 75.7253 |

# | Belagavi | 15.8521 | 74.5045 |

# | Dharwad | 15.4589 | 75.0078 |

# 

# \*\*Coordinate note:\*\* These coordinates represent approximate city-centre points, not complete district boundaries or district-wide averages.

# 

# \## 3. Data Sources and Variables

# 

# \### 3.1 NASA POWER

# 

# NASA POWER provides daily meteorological data through its Daily Point API.

# 

# \- API: NASA POWER Daily Point API

# \- Endpoint: `https://power.larc.nasa.gov/api/temporal/daily/point`

# \- Community: AG

# \- Data retrieval date: 2026-11-14

# 

# Variables used in the combined environmental dataset:

# 

# | Parameter | Description | Unit |

# |---|---|---|

# | T2M | Temperature at 2 metres | °C |

# | PRECTOTCORR | Corrected precipitation | mm/day |

# 

# Other parameters were also requested in the original POWER collection, but T2M and PRECTOTCORR are the variables used in the combined dataset.

# 

# \### 3.2 NASA GPM IMERG

# 

# NASA GPM provides satellite-based precipitation estimates.

# 

# \- Product: GPM\_3IMERGDF

# \- Version: 07B

# \- Variable: `precipitation`

# \- Description: Daily mean precipitation rate

# \- Unit: mm/day

# \- Spatial resolution: 0.1° × 0.1°

# \- DOI: 10.5067/GPM/IMERGDF/DAY/07

# \- Data retrieval date: 2026-11-14

# 

# Daily precipitation values were extracted from the nearest GPM grid cell to each location's coordinates.

# 

# These are satellite-based estimates, not ground-based rain gauge measurements.

# 

# \## 4. Dataset Files

# 

# \### 4.1 Original NASA POWER Data

# 

# Directory:

# 

# `data/nasa\_power/`

# 

# Contains the individual daily climate CSV files for the five locations.

# 

# \### 4.2 NASA GPM Rainfall Data

# 

# Processed CSV:

# 

# `data/gpm/gpm\_rainfall\_january\_2025.csv`

# 

# Original downloaded NetCDF4 files:

# 

# `data/gpm/january\_2025/`

# 

# \### 4.3 Combined Environmental Dataset

# 

# File:

# 

# `data/combined/nasa\_environmental\_data\_january\_2025.csv`

# 

# Columns:

# 

# | Column | Description |

# |---|---|

# | date | Daily observation date |

# | location | Location name |

# | latitude | Location latitude |

# | longitude | Location longitude |

# | temperature\_c | NASA POWER temperature (°C) |

# | nasa\_power\_rainfall\_mm | NASA POWER corrected precipitation (mm/day) |

# | gpm\_rainfall\_mm | NASA GPM precipitation estimate (mm/day) |

# | source | Data source information |

# 

# \### 4.4 Member 2 Handoff Dataset

# 

# File:

# 

# `data/handoff/FIELDWISE\_AI\_member2\_january\_2025.csv`

# 

# Columns:

# 

# \- date

# \- location

# \- latitude

# \- longitude

# \- temperature\_c

# \- rainfall\_mm

# \- source

# 

# The handoff dataset uses NASA POWER T2M for temperature and NASA GPM IMERG Final V07B for rainfall.

# 

# \## 5. Data Processing Methodology

# 

# The following processing steps were performed:

# 

# 1\. Collected daily temperature and precipitation data using the NASA POWER Daily Point API.

# 2\. Downloaded NASA GPM IMERG Final V07B daily NetCDF4 granules through NASA Earthdata.

# 3\. Extracted the GPM `precipitation` variable for the nearest grid cell to each location.

# 4\. Converted dates from the original NASA POWER and GPM formats into a common `YYYY-MM-DD` format.

# 5\. Combined the datasets using date and location as matching fields.

# 6\. Generated a normalized environmental dataset.

# 7\. Prepared a separate CSV file for Member 2 integration.

# 8\. Validated record counts, duplicate entries, missing values and rainfall values.

# 

# \## 6. Dataset Coverage

# 

# | Description | Value |

# |---|---:|

# | Start date | 2025-01-01 |

# | End date | 2025-01-31 |

# | Locations | 5 |

# | Days per location | 31 |

# | Expected records | 155 |

# | Actual records | 155 |

# 

# \## 7. Data Validation Results

# 

# The combined environmental dataset was validated.

# 

# | Validation | Result |

# |---|---:|

# | Total records | 155 |

# | Duplicate date/location records | 0 |

# | Missing values | 0 |

# | Negative GPM rainfall values | 0 |

# | Negative NASA POWER rainfall values | 0 |

# | Locations covered | 5 |

# | Daily coverage | 31 days |

# 

# The generated GPM rainfall CSV was also checked separately for its required columns, date coverage, location coverage, duplicate records, missing values and invalid rainfall values.

# 

# All 11 GPM dataset validation tests passed.

# 

# \## 8. Important Notes and Limitations

# 

# \- NASA POWER and NASA GPM are different precipitation products.

# \- Their rainfall estimates should be compared, not assumed to be identical.

# \- GPM values represent nearest-grid-cell estimates, not ground station measurements.

# \- Coordinates represent approximate city-centre locations.

# \- The dataset covers January 2025 only.

# \- The values should not be interpreted as district-wide rainfall measurements.

# \- The January dataset alone is not sufficient to establish long-term climate patterns or make reliable crop suitability decisions.

# \- Original GPM NetCDF4 files are retained locally and excluded from Git because of their large file sizes.

# \- Processed CSV datasets are included in the project repository.

# 

# \## 9. Data Source References

# 

# \*\*NASA POWER\*\*

# 

# https://power.larc.nasa.gov/

# 

# \*\*NASA GPM IMERG\*\*

# 

# https://gpm.nasa.gov/data/imerg

# 

# \*\*NASA GPM IMERG Final Daily Product\*\*

# 

# https://doi.org/10.5067/GPM/IMERGDF/DAY/07

# 

# \*\*NASA Earthdata\*\*

# 

# https://www.earthdata.nasa.gov/

# 

# \---

# 

# \*\*Project:\*\* Kyro  

# \*\*Module:\*\* NASA Environmental Data Collection  

# \*\*Data retrieval date:\*\* 2026-11-14  

# \*\*Reporting period:\*\* January 2025  

# \*\*Locations:\*\* Five Karnataka locations

