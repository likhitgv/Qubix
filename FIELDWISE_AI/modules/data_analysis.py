
"""
KAIRO - Environmental Data Analysis Module
"""

import pandas as pd

REQUIRED_COLUMNS = [
    "date",
    "location",
    "latitude",
    "longitude",
    "temperature_c",
    "rainfall_mm",
    "source"
]


def clean_climate_data(data):

    if not isinstance(data, pd.DataFrame):
        raise TypeError("Input must be a Pandas DataFrame.")

    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    cleaned_data = data.copy()

    # Convert dates
    cleaned_data["date"] = pd.to_datetime(
        cleaned_data["date"],
        errors="coerce"
    )

    # Convert numeric columns
    numeric_columns = [
        "latitude",
        "longitude",
        "temperature_c",
        "rainfall_mm"
    ]

    for column in numeric_columns:
        cleaned_data[column] = pd.to_numeric(
            cleaned_data[column],
            errors="coerce"
        )

    # Validate coordinates
    cleaned_data.loc[
        ~cleaned_data["latitude"].between(-90, 90),
        "latitude"
    ] = float("nan")

    cleaned_data.loc[
        ~cleaned_data["longitude"].between(-180, 180),
        "longitude"
    ] = float("nan")

    # Validate rainfall
    invalid_rainfall = cleaned_data["rainfall_mm"] < 0
    invalid_rainfall_count = int(invalid_rainfall.sum())

    cleaned_data.loc[
        invalid_rainfall,
        "rainfall_mm"
    ] = float("nan")

    # Generate quality report
    missing_values = (
        cleaned_data[REQUIRED_COLUMNS]
        .isnull()
        .sum()
        .to_dict()
    )

    report = {
        "total_records": len(cleaned_data),
        "invalid_dates": int(
            cleaned_data["date"].isnull().sum()
        ),
        "invalid_rainfall_values": invalid_rainfall_count,
        "missing_values": missing_values
    }

    return cleaned_data, report


def load_climate_data(file_path):

    data = pd.read_csv(file_path)

    return clean_climate_data(data)

def generate_climate_summary(data):
    """
    Generate basic temperature and rainfall statistics.
    """

    summary = {
        "location": data["location"].iloc[0],
        "total_records": len(data),

        "average_temperature_c": round(
            data["temperature_c"].mean(), 2
        ),

        "minimum_temperature_c": round(
            data["temperature_c"].min(), 2
        ),

        "maximum_temperature_c": round(
            data["temperature_c"].max(), 2
        ),

        "total_rainfall_mm": round(
            data["rainfall_mm"].sum(), 2
        ),

        "average_rainfall_mm": round(
            data["rainfall_mm"].mean(), 2
        )
    }

    return summary

def generate_climate_trends(data):
    """
    Prepare daily temperature and rainfall trends.
    """

    trends = data[
        ["date", "temperature_c", "rainfall_mm"]
    ].copy()

    trends = trends.sort_values("date")

    trends = trends.reset_index(drop=True)

    return trends


def load_nasa_power_data(file_path):
    """
    Load and convert actual NASA POWER climate data
    into the format required by KAIRO.
    """

    nasa_data = pd.read_csv(file_path)

    required_nasa_columns = [
        "location",
        "latitude",
        "longitude",
        "date",
        "T2M",
        "T2M_MAX",
        "T2M_MIN",
        "PRECTOTCORR",
        "RH2M",
        "ALLSKY_SFC_SW_DWN"
    ]

    missing_columns = [
        column for column in required_nasa_columns
        if column not in nasa_data.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing NASA columns: {missing_columns}"
        )

     # Support both NASA date formats: YYYY-MM-DD and YYYYMMDD
    date_values = nasa_data["date"].astype(str).str.strip()

    parsed_dates = pd.to_datetime(
        date_values,
        format="%Y-%m-%d",
        errors="coerce"
    )

    missing_dates = parsed_dates.isna()

    parsed_dates.loc[missing_dates] = pd.to_datetime(
        date_values.loc[missing_dates],
        format="%Y%m%d",
        errors="coerce"
    )

    nasa_data["date"] = parsed_dates

       # Remove previously converted columns to avoid duplicates
    nasa_data = nasa_data.drop(
        columns=["temperature_c", "rainfall_mm"],
        errors="ignore"
    )

    # Convert NASA column names
    converted_data = nasa_data.rename(columns={
        "T2M": "temperature_c",
        "PRECTOTCORR": "rainfall_mm"
    })
 # Add source information
    converted_data["source"] = "NASA POWER"

    # Clean and validate the converted data
    cleaned_data, report = clean_climate_data(
        converted_data
    )

    return cleaned_data, report


def generate_district_summaries(data):
    """
    Generate separate climate summaries
    for all districts in KAIRO.
    """

    district_summaries = []

    for location, district_data in data.groupby("location"):

        summary = {
            "location": location,
            "total_records": len(district_data),

            "average_temperature_c": round(
                float(district_data["temperature_c"].mean()), 2
            ),

            "minimum_temperature_c": round(
                float(district_data["temperature_c"].min()), 2
            ),

            "maximum_temperature_c": round(
                float(district_data["temperature_c"].max()), 2
            ),

            "total_rainfall_mm": round(
                float(district_data["rainfall_mm"].sum()), 2
            ),

                       "average_rainfall_mm": round(
                float(district_data["rainfall_mm"].mean()), 3
            ),
            "average_humidity_percent": round(
                float(district_data["RH2M"].mean()), 2
            ),

            "average_solar_radiation": round(
                float(district_data["ALLSKY_SFC_SW_DWN"].mean()), 2
            )
        }

        district_summaries.append(summary)

    return district_summaries


def generate_district_trends(data):
    """
    Generate daily climate trends for all five districts.
    These records can be used for dashboard visualizations.
    """

    required_columns = [
        "location",
        "date",
        "temperature_c",
        "T2M_MAX",
        "T2M_MIN",
        "rainfall_mm",
        "RH2M",
        "ALLSKY_SFC_SW_DWN"
    ]

    trends = data[required_columns].copy()

    trends = trends.sort_values(
        ["location", "date"]
    )

    trends = trends.reset_index(drop=True)

    return trends


def create_temperature_chart(data):
    """
    Create an interactive daily temperature chart
    for all five districts.
    """
    import plotly.express as px

    fig = px.line(
        data,
        x="date",
        y="temperature_c",
        color="location",
        markers=True,
        title="Daily Temperature Trends - Karnataka Districts",
        labels={
            "date": "Date",
            "temperature_c": "Temperature (°C)",
            "location": "District"
        }
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified"
    )

    return fig


def create_rainfall_chart(data):
    """
    Create an interactive daily rainfall chart
    for all five districts.
    """
    import plotly.express as px

    fig = px.line(
        data,
        x="date",
        y="rainfall_mm",
        color="location",
        markers=True,
        title="Daily Rainfall Trends - Karnataka Districts",
        labels={
            "date": "Date",
            "rainfall_mm": "Rainfall (mm/day)",
            "location": "District"
        }
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified"
    )

    return fig




