import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape, Point
from shapely.prepared import prep

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "india_grid_2021_2025"
RAW = DATA / "raw_2026"
BOUNDARY_FILE = DATA / "india_boundary.geojson"
OUTPUT = DATA / "processed" / "india_clipped_2026"

MET_VARIABLES = [
    "T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M"
]
SOLAR_VARIABLES = ["ALLSKY_SFC_SW_DWN"]

UNITS = {
    "T2M": "deg C",
    "T2M_MAX": "deg C",
    "T2M_MIN": "deg C",
    "PRECTOTCORR": "mm/day",
    "RH2M": "percent",
    "ALLSKY_SFC_SW_DWN": "MJ/m2/day"
}

TILES = [f"T{i:02d}" for i in range(1, 13)]


def load_variable(tile, variable):
    path = RAW / tile / "2026" / f"{variable}.json"

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    source = "|".join(data.get("header", {}).get("sources", []))
    rows = []

    for feature in data["features"]:
        lon, lat, elevation = feature["geometry"]["coordinates"]
        values = feature["properties"]["parameter"][variable]

        for date, value in values.items():
            if value is None or value == -999:
                value = np.nan

            rows.append({
                "latitude": float(lat),
                "longitude": float(lon),
                "elevation_m": float(elevation),
                "date": pd.to_datetime(date, format="%Y%m%d"),
                variable: value,
                f"source_{variable}": source
            })

    return pd.DataFrame(rows)


def process_dataset(variables, polygon):
    tile_frames = []

    for tile in TILES:
        print(f"Processing {tile}...")

        combined = None

        for variable in variables:
            frame = load_variable(tile, variable)

            keys = [
                "latitude", "longitude",
                "elevation_m", "date"
            ]

            if combined is None:
                combined = frame
            else:
                combined = combined.merge(
                    frame, on=keys, how="outer",
                    validate="one_to_one"
                )

        combined["tile_id"] = tile

        inside = [
            polygon.covers(Point(lon, lat))
            for lon, lat in zip(
                combined["longitude"],
                combined["latitude"]
            )
        ]

        combined = combined.loc[inside].copy()
        tile_frames.append(combined)

    all_data = pd.concat(tile_frames, ignore_index=True)

    keys = ["latitude", "longitude", "date"]
    value_columns = variables + ["elevation_m"]

    # Check overlapping tiles before deduplication.
    grouped = all_data.groupby(keys, dropna=False)

    mismatch_count = 0

    for column in value_columns:
        mismatches = grouped[column].nunique(dropna=True)
        mismatch_count += int((mismatches > 1).sum())

    if mismatch_count:
        raise ValueError(
            f"Overlapping tile values disagree: {mismatch_count} "
            "coordinate/date/column combinations. No output saved."
        )

    duplicate_count = int(all_data.duplicated(keys).sum())

    aggregations = {
        column: "first"
        for column in value_columns
    }

    for variable in variables:
        aggregations[f"source_{variable}"] = (
            lambda values: "|".join(
                sorted(set(v for v in values if v))
            )
        )

    aggregations["source_tiles"] = (
        lambda values: "|".join(sorted(set(values)))
    )

    all_data["source_tiles"] = all_data["tile_id"]

    result = (
        all_data.groupby(keys, as_index=False, dropna=False)
        .agg(aggregations)
        .sort_values(keys)
        .reset_index(drop=True)
    )

    return result, duplicate_count


def create_quality_report(met, solar):
    rows = []

    for dataset_name, frame, variables in [
        ("meteorological", met, MET_VARIABLES),
        ("solar", solar, SOLAR_VARIABLES)
    ]:
        for variable in variables:
            rows.append({
                "dataset": dataset_name,
                "variable": variable,
                "unit": UNITS[variable],
                "total_records": len(frame),
                "grid_points": frame[
                    ["latitude", "longitude"]
                ].drop_duplicates().shape[0],
                "missing_observations": int(frame[variable].isna().sum()),
                "duplicate_grid_date_records": int(
                    frame.duplicated(
                        ["latitude", "longitude", "date"]
                    ).sum()
                ),
                "start_date": frame["date"].min().date(),
                "end_date": frame["date"].max().date(),
                "years": "2026"
            })

    return pd.DataFrame(rows)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    with open(BOUNDARY_FILE, encoding="utf-8") as f:
        boundary_data = json.load(f)

    india_geometry = shape(boundary_data["features"][0]["geometry"])
    india_polygon = prep(india_geometry)

    print("India boundary loaded.")
    print("Processing meteorological data...")

    met, met_duplicates = process_dataset(
        MET_VARIABLES, india_polygon
    )

    print("\nProcessing solar data...")

    solar, solar_duplicates = process_dataset(
        SOLAR_VARIABLES, india_polygon
    )

    met_path = OUTPUT / "india_meteorological_daily_2026.csv"
    solar_path = OUTPUT / "india_solar_daily_2026.csv"
    report_path = OUTPUT / "india_2026_quality_report.csv"

    met.to_csv(met_path, index=False, date_format="%Y-%m-%d")
    solar.to_csv(solar_path, index=False, date_format="%Y-%m-%d")

    report = create_quality_report(met, solar)
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    print("\n========== 2026 INDIA DATA PROCESSING ==========")
    print("Meteorological records:", len(met))
    print("Meteorological grid points:", met[
        ["latitude", "longitude"]
    ].drop_duplicates().shape[0])
    print("Meteorological boundary duplicates removed:", met_duplicates)

    print("\nSolar records:", len(solar))
    print("Solar grid points:", solar[
        ["latitude", "longitude"]
    ].drop_duplicates().shape[0])
    print("Solar boundary duplicates removed:", solar_duplicates)

    print("\nDate range:", met["date"].min(), "to", met["date"].max())
    print("\nMissing values by variable:")
    for variable in MET_VARIABLES:
        print(variable, ":", int(met[variable].isna().sum()))

    print(
        "ALLSKY_SFC_SW_DWN:",
        int(solar["ALLSKY_SFC_SW_DWN"].isna().sum())
    )

    print("\nOUTPUT FILES:")
    print(met_path)
    print(solar_path)
    print(report_path)
    print("\nPROCESSING COMPLETED.")


if __name__ == "__main__":
    main()
