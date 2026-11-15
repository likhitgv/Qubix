
"""
Kyro - Environmental Data Analysis Module
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
