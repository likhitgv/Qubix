import csv
import json
import time
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd
import requests

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "india_grid_2021_2025"
OUTPUT_DIR = DATA_DIR / "raw_2026"
TILE_FILE = DATA_DIR / "india_tiles.csv"
MANIFEST = OUTPUT_DIR / "update_manifest.csv"

URL = "https://power.larc.nasa.gov/api/temporal/daily/regional"

VARIABLES = [
    "T2M", "T2M_MAX", "T2M_MIN",
    "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"
]

START_DATE = "20260101"
END_DATE = "20261115"
PAUSE_SECONDS = 3
MAX_ATTEMPTS = 3


def save_manifest(record):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "tile_id", "variable", "status", "grid_points",
        "dates", "valid_observations", "missing_observations",
        "sources", "retrieved_at_utc", "message"
    ]

    exists = MANIFEST.exists()

    with open(MANIFEST, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow(record)


def download_one(tile, variable):
    tile_id = tile["tile_id"]
    folder = OUTPUT_DIR / tile_id / "2026"
    folder.mkdir(parents=True, exist_ok=True)

    output_file = folder / f"{variable}.json"

    if output_file.exists():
        try:
            with open(output_file, encoding="utf-8") as f:
                old = json.load(f)

            if old.get("features") and old.get("header", {}).get("start") == START_DATE:
                print(f"SKIPPED: {tile_id} {variable} already downloaded")
                return True
        except Exception:
            pass

    params = {
        "parameters": variable,
        "community": "AG",
        "latitude-min": float(tile["latitude_min"]),
        "latitude-max": float(tile["latitude_max"]),
        "longitude-min": float(tile["longitude_min"]),
        "longitude-max": float(tile["longitude_max"]),
        "start": START_DATE,
        "end": END_DATE,
        "format": "JSON",
        "time-standard": "UTC"
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(URL, params=params, timeout=240)
            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])
            if not features:
                raise ValueError("NASA returned no grid features")

            dates = set()
            valid = 0
            missing = 0

            for feature in features:
                values = feature["properties"]["parameter"][variable]
                dates.update(values.keys())

                for value in values.values():
                    if value is None or value == -999:
                        missing += 1
                    else:
                        valid += 1

            if not data.get("parameters", {}).get(variable):
                raise ValueError("Variable metadata missing")

            if len(dates) != 319:
                raise ValueError(
                    f"Expected 319 dates, received {len(dates)}"
                )

            temp_file = output_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f)

            temp_file.replace(output_file)

            sources = data.get("header", {}).get("sources", [])

            save_manifest({
                "tile_id": tile_id,
                "variable": variable,
                "status": "SUCCESS",
                "grid_points": len(features),
                "dates": len(dates),
                "valid_observations": valid,
                "missing_observations": missing,
                "sources": "|".join(sources),
                "retrieved_at_utc": datetime.utcnow().isoformat(),
                "message": ""
            })

            print(
                f"SUCCESS: {tile_id} {variable} | "
                f"Points: {len(features)} | "
                f"Valid: {valid} | Missing: {missing} | "
                f"Source: {sources}"
            )
            return True

        except Exception as error:
            print(
                f"ATTEMPT {attempt} FAILED: "
                f"{tile_id} {variable} | {error}"
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(10 * attempt)

    save_manifest({
        "tile_id": tile_id,
        "variable": variable,
        "status": "FAILED",
        "grid_points": 0,
        "dates": 0,
        "valid_observations": 0,
        "missing_observations": 0,
        "sources": "",
        "retrieved_at_utc": datetime.utcnow().isoformat(),
        "message": "All download attempts failed"
    })

    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tile",
        default="ALL",
        help="Tile ID such as T05, or ALL"
    )
    args = parser.parse_args()

    tiles = pd.read_csv(TILE_FILE).to_dict("records")

    if args.tile.upper() != "ALL":
        tiles = [t for t in tiles if t["tile_id"] == args.tile.upper()]

    if not tiles:
        raise ValueError("No matching tile found")

    total = len(tiles) * len(VARIABLES)
    success = 0
    failed = 0
    count = 0

    print("=" * 55)
    print("FIELDWISE AI - 2026 NASA POWER DATA DOWNLOAD")
    print("Tiles:", len(tiles))
    print("Variables:", len(VARIABLES))
    print("Requests:", total)
    print("Period:", START_DATE, "to", END_DATE)
    print("Output:", OUTPUT_DIR)
    print("=" * 55)

    for tile in tiles:
        for variable in VARIABLES:
            count += 1
            print(f"\nREQUEST {count}/{total}")
            if download_one(tile, variable):
                success += 1
            else:
                failed += 1
            time.sleep(PAUSE_SECONDS)

    print("\nDOWNLOAD SUMMARY")
    print("Successful:", success)
    print("Failed:", failed)
    print("Manifest:", MANIFEST)


if __name__ == "__main__":
    main()
