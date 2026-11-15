
import argparse
import csv
import json
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests


# --------------------------------------------------
# Kyro - INDIA NASA POWER DOWNLOADER
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "india_grid_2021_2025"
RAW_DIR = DATA_DIR / "raw"
TILE_FILE = DATA_DIR / "india_tiles.csv"
MANIFEST_FILE = DATA_DIR / "download_manifest.csv"

URL = "https://power.larc.nasa.gov/api/temporal/daily/regional"

VARIABLES = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
]

COMMUNITY = "AG"
MAX_ATTEMPTS = 3
REQUEST_PAUSE_SECONDS = 3

session = requests.Session()
session.headers.update({
    "User-Agent": "FIELDWISE-AI-NASA-POWER-Research/1.0"
})


def expected_dates(year):
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    return {
        start.strftime("%Y%m%d"),
        end.strftime("%Y%m%d"),
    }, (end - start).days + 1


def output_path(tile_id, year, variable):
    return RAW_DIR / tile_id / str(year) / f"{variable}.json"


def validate_file(path, variable, year):
    """Check that an existing file is complete enough to reuse."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        features = data.get("features", [])

        if not features:
            return False

        if variable not in data.get("parameters", {}):
            return False

        _, expected_count = expected_dates(year)

        for feature in features:
            values = (
                feature.get("properties", {})
                .get("parameter", {})
                .get(variable, {})
            )

            if len(values) != expected_count:
                return False

        return True

    except (OSError, json.JSONDecodeError, TypeError):
        return False


def save_manifest(row):
    fields = [
        "tile_id",
        "year",
        "variable",
        "status",
        "grid_points",
        "daily_records",
        "missing_values",
        "file_size_mb",
        "message",
    ]

    file_exists = MANIFEST_FILE.exists()

    with MANIFEST_FILE.open(
        "a", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)

        if not file_exists:
            writer.writeheader()

        writer.writerow(row)


def download_one(tile, year, variable):
    tile_id = tile["tile_id"]
    path = output_path(tile_id, year, variable)

    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and validate_file(path, variable, year):
        print(f"SKIPPED (already valid): {tile_id} {year} {variable}")
        return True

    start = f"{year}0101"
    end = f"{year}1231"
    _, expected_count = expected_dates(year)

    params = {
        "parameters": variable,
        "community": COMMUNITY,
        "latitude-min": float(tile["latitude_min"]),
        "latitude-max": float(tile["latitude_max"]),
        "longitude-min": float(tile["longitude_min"]),
        "longitude-max": float(tile["longitude_max"]),
        "start": start,
        "end": end,
        "format": "JSON",
        "time-standard": "UTC",
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            print(
                f"REQUEST {tile_id} | {year} | {variable} "
                f"| attempt {attempt}/{MAX_ATTEMPTS}"
            )

            response = session.get(
                URL,
                params=params,
                timeout=300,
            )
            response.raise_for_status()

            data = response.json()
            features = data.get("features", [])

            if not features:
                raise ValueError("NASA response contains no grid features")

            if variable not in data.get("parameters", {}):
                raise ValueError("Variable metadata missing in response")

            missing = 0
            total = 0

            for feature in features:
                values = (
                    feature.get("properties", {})
                    .get("parameter", {})
                    .get(variable, {})
                )

                if len(values) != expected_count:
                    raise ValueError(
                        f"Incomplete dates: expected {expected_count}, "
                        f"received {len(values)}"
                    )

                total += len(values)
                missing += sum(
                    value is None or value == -999
                    for value in values.values()
                )

            # Save atomically so interrupted writes are not mistaken
            # for completed downloads.
            temp_path = path.with_suffix(".json.tmp")
            temp_path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )
            temp_path.replace(path)

            size_mb = path.stat().st_size / (1024 * 1024)

            save_manifest({
                "tile_id": tile_id,
                "year": year,
                "variable": variable,
                "status": "SUCCESS",
                "grid_points": len(features),
                "daily_records": expected_count,
                "missing_values": missing,
                "file_size_mb": round(size_mb, 3),
                "message": "",
            })

            print(
                f"SUCCESS | points={len(features)} "
                f"| dates={expected_count} "
                f"| missing={missing}/{total} "
                f"| size={size_mb:.2f} MB"
            )

            return True

        except Exception as error:
            print(f"ERROR: {error}")

            if attempt < MAX_ATTEMPTS:
                wait_seconds = 10 * attempt
                print(f"Waiting {wait_seconds} seconds before retry...")
                time.sleep(wait_seconds)

    save_manifest({
        "tile_id": tile_id,
        "year": year,
        "variable": variable,
        "status": "FAILED",
        "grid_points": 0,
        "daily_records": 0,
        "missing_values": "",
        "file_size_mb": "",
        "message": "All retry attempts failed",
    })

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Download NASA POWER India-region grid data"
    )

    parser.add_argument("--tile", default="T05")
    parser.add_argument("--start-year", type=int, default=2021)
    parser.add_argument("--end-year", type=int, default=2021)
    parser.add_argument("--all", action="store_true")

    args = parser.parse_args()

    if not 1981 <= args.start_year <= args.end_year <= 2025:
        raise ValueError("Choose valid years between 1981 and 2025.")

    if not TILE_FILE.exists():
        raise FileNotFoundError(f"Tile file not found: {TILE_FILE}")

    tiles = pd.read_csv(TILE_FILE).to_dict("records")

    if args.all:
        selected_tiles = tiles
    else:
        selected_tiles = [
            tile for tile in tiles
            if tile["tile_id"] == args.tile
        ]

    if not selected_tiles:
        raise ValueError(f"Unknown tile: {args.tile}")

    total_requests = (
        len(selected_tiles)
        * (args.end_year - args.start_year + 1)
        * len(VARIABLES)
    )

    print("=" * 60)
    print("Kyro - NASA POWER DATA DOWNLOAD")
    print("Tiles:", len(selected_tiles))
    print("Years:", args.start_year, "to", args.end_year)
    print("Variables:", len(VARIABLES))
    print("Planned requests:", total_requests)
    print("Output:", RAW_DIR)
    print("=" * 60)

    completed = 0
    failed = 0

    for tile in selected_tiles:
        for year in range(args.start_year, args.end_year + 1):
            for variable in VARIABLES:
                success = download_one(tile, year, variable)

                if success:
                    completed += 1
                else:
                    failed += 1

                time.sleep(REQUEST_PAUSE_SECONDS)

    print("\nDOWNLOAD RUN FINISHED")
    print("Successful or already valid:", completed)
    print("Failed:", failed)
    print("Manifest:", MANIFEST_FILE)


if __name__ == "__main__":
    main()
