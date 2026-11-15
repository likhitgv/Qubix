
import json
from pathlib import Path

import pandas as pd


# --------------------------------------------------
# KAIRO - INDIA-WIDE NASA DATA PROCESSING
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

RAW_DIR = BASE_DIR / "data" / "india_grid_2021_2025" / "raw"
OUTPUT_DIR = BASE_DIR / "data" / "india_grid_2021_2025" / "processed"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

YEARS = range(2021, 2026)
TILES = [f"T{i:02d}" for i in range(1, 13)]

MET_VARIABLES = [
    "T2M", "T2M_MAX", "T2M_MIN",
    "PRECTOTCORR", "RH2M"
]

SOLAR_VARIABLES = ["ALLSKY_SFC_SW_DWN"]

VARIABLE_INFO = {
    "T2M": ("°C", "MERRA-2"),
    "T2M_MAX": ("°C", "MERRA-2 / POWER"),
    "T2M_MIN": ("°C", "MERRA-2 / POWER"),
    "PRECTOTCORR": ("mm/day", "MERRA-2"),
    "RH2M": ("%", "MERRA-2 / POWER"),
    "ALLSKY_SFC_SW_DWN": ("MJ/m²/day", "SYN1DEG"),
}


def load_variable_file(tile, year, variable):
    """Load one NASA POWER variable file."""

    path = RAW_DIR / tile / str(year) / f"{variable}.json"

    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    records = []

    for feature in data["features"]:
        lon, lat, elevation = feature["geometry"]["coordinates"]

        values = feature["properties"]["parameter"][variable]

        for date, value in values.items():

            if value is None or value == -999:
                value = float("nan")

            records.append({
                "tile_id": tile,
                "latitude": lat,
                "longitude": lon,
                "elevation_m": elevation,
                "date": pd.to_datetime(date, format="%Y%m%d"),
                variable: value,
            })

    return pd.DataFrame(records)


def process_group(variables, group_name):
    """Process one tile-year at a time to limit memory use."""

    yearly_frames = []

    for tile in TILES:
        for year in YEARS:

            print(f"Processing {tile} - {year} - {group_name}")

            merged = None

            for variable in variables:

                current = load_variable_file(tile, year, variable)

                keys = [
                    "tile_id",
                    "latitude",
                    "longitude",
                    "elevation_m",
                    "date",
                ]

                if merged is None:
                    merged = current
                else:
                    merged = merged.merge(
                        current,
                        on=keys,
                        how="outer",
                        validate="one_to_one",
                    )

                del current

            yearly_frames.append(merged)
            del merged

    result = pd.concat(yearly_frames, ignore_index=True)
    del yearly_frames

    # Track all tiles contributing to each grid coordinate.
    tile_sources = (
        result.groupby(["latitude", "longitude"])["tile_id"]
        .agg(lambda values: "|".join(sorted(set(values))))
        .rename("source_tiles")
        .reset_index()
    )

    # Remove verified identical boundary duplicates.
    result = result.drop_duplicates(
        subset=["latitude", "longitude", "date"],
        keep="first",
    )

    result = result.drop(columns=["tile_id"])

    result = result.merge(
        tile_sources,
        on=["latitude", "longitude"],
        how="left",
        validate="many_to_one",
    )

    result = result.sort_values(
        ["latitude", "longitude", "date"]
    ).reset_index(drop=True)

    return result


def create_quality_report(meteorological, solar):
    """Create variable-wise data quality and provenance report."""

    report = []

    datasets = [
        ("meteorological", meteorological, MET_VARIABLES),
        ("solar", solar, SOLAR_VARIABLES),
    ]

    for name, dataframe, variables in datasets:

        duplicate_count = dataframe.duplicated(
            subset=["latitude", "longitude", "date"]
        ).sum()

        unique_points = dataframe[
            ["latitude", "longitude"]
        ].drop_duplicates().shape[0]

        for variable in variables:

            unit, source = VARIABLE_INFO[variable]

            report.append({
                "dataset": name,
                "variable": variable,
                "unit": unit,
                "data_source": source,
                "total_records": len(dataframe),
                "missing_observations": int(
                    dataframe[variable].isna().sum()
                ),
                "duplicate_grid_date_records": int(duplicate_count),
                "unique_grid_points": unique_points,
                "start_date": dataframe["date"].min(),
                "end_date": dataframe["date"].max(),
            })

    return pd.DataFrame(report)


def main():

    print("=" * 60)
    print("KAIRO - INDIA-WIDE DATA PROCESSING")
    print("=" * 60)

    print("\nProcessing meteorological data...")

    meteorological = process_group(
        MET_VARIABLES,
        "METEOROLOGICAL",
    )

    print("\nProcessing solar data...")

    solar = process_group(
        SOLAR_VARIABLES,
        "SOLAR",
    )

    met_path = OUTPUT_DIR / "india_meteorological_daily.csv"
    solar_path = OUTPUT_DIR / "india_solar_daily.csv"

    report_path = OUTPUT_DIR / "india_data_quality_report.csv"

    print("\nSaving processed datasets...")

    meteorological.to_csv(met_path, index=False)
    solar.to_csv(solar_path, index=False)

    report = create_quality_report(meteorological, solar)
    report.to_csv(report_path, index=False)

    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)

    print("Meteorological records:", len(meteorological))
    print(
        "Meteorological grid points:",
        meteorological[["latitude", "longitude"]]
        .drop_duplicates().shape[0],
    )

    print("Solar records:", len(solar))
    print(
        "Solar grid points:",
        solar[["latitude", "longitude"]]
        .drop_duplicates().shape[0],
    )

    print("\nQUALITY REPORT")
    print(report.to_string(index=False))

    print("\nOUTPUT FILES")
    print(met_path)
    print(solar_path)
    print(report_path)

    print("\nPROCESSING COMPLETED.")


if __name__ == "__main__":
    main()
