
import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "india_grid_2021_2025"
RAW_DIR = DATA_DIR / "raw_2026"
TILE_FILE = DATA_DIR / "india_tiles.csv"

MANIFEST_FILE = RAW_DIR / "daily_update_manifest.csv"

API_URL = (
    "https://power.larc.nasa.gov/api/temporal/daily/regional"
)

COMMUNITY = "AG"

VARIABLES = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",
    "RH2M",
    "ALLSKY_SFC_SW_DWN",
]

FILL_VALUE = -999.0
REQUEST_PAUSE = 3
MAX_ATTEMPTS = 3


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def coordinate_key(coordinates):
    """Create a stable key for a NASA grid point."""

    longitude, latitude = coordinates[:2]

    return (
        round(float(longitude), 5),
        round(float(latitude), 5),
    )


def is_valid_value(value):
    """Check whether a NASA observation is usable."""

    if value is None:
        return False

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False

    return pd.notna(number) and number != FILL_VALUE


def save_json_atomically(path, data):
    """Save JSON safely without leaving a partial file."""

    temporary_path = path.with_suffix(".tmp")

    with open(temporary_path, "w", encoding="utf-8") as file:
        json.dump(data, file, separators=(",", ":"))

    temporary_path.replace(path)


# --------------------------------------------------
# NASA API DOWNLOAD
# --------------------------------------------------

def download_variable(tile, variable, start_date, end_date):

    params = {
        "parameters": variable,
        "community": COMMUNITY,
        "longitude-min": float(tile["longitude_min"]),
        "longitude-max": float(tile["longitude_max"]),
        "latitude-min": float(tile["latitude_min"]),
        "latitude-max": float(tile["latitude_max"]),
        "start": start_date,
        "end": end_date,
        "format": "JSON",
    }

    for attempt in range(1, MAX_ATTEMPTS + 1):

        try:
            response = requests.get(
                API_URL,
                params=params,
                timeout=180,
            )

            if response.status_code == 200:
                data = response.json()

                if not data.get("features"):
                    raise ValueError("NASA response contains no features")

                return data

            print(
                f"HTTP {response.status_code} "
                f"for {tile['tile_id']} {variable}"
            )

        except Exception as error:
            print(
                f"Attempt {attempt}/{MAX_ATTEMPTS} failed: {error}"
            )

        if attempt < MAX_ATTEMPTS:
            time.sleep(10 * attempt)

    raise RuntimeError(
        f"Download failed: {tile['tile_id']} {variable}"
    )


# --------------------------------------------------
# MERGE NEW OBSERVATIONS WITH EXISTING JSON
# --------------------------------------------------

def merge_observations(existing, incoming, variable):

    existing_features = existing.get("features", [])
    incoming_features = incoming.get("features", [])

    feature_map = {
        coordinate_key(feature["geometry"]["coordinates"]): feature
        for feature in existing_features
    }

    added_values = 0
    replaced_values = 0
    preserved_values = 0
    new_points = 0

    for new_feature in incoming_features:

        coordinates = new_feature["geometry"]["coordinates"]
        key = coordinate_key(coordinates)

        if key not in feature_map:

            feature_map[key] = new_feature
            new_points += 1

            continue

        old_feature = feature_map[key]

        old_parameters = (
            old_feature.setdefault("properties", {})
            .setdefault("parameter", {})
        )

        new_parameters = (
            new_feature.get("properties", {})
            .get("parameter", {})
        )

        old_values = old_parameters.setdefault(variable, {})
        new_values = new_parameters.get(variable, {})

        for date, new_value in new_values.items():

            old_value = old_values.get(date)

            if is_valid_value(new_value):

                if not is_valid_value(old_value):
                    old_values[date] = new_value
                    added_values += 1

                elif float(old_value) != float(new_value):
                    old_values[date] = new_value
                    replaced_values += 1

            else:

                if is_valid_value(old_value):
                    preserved_values += 1

                elif date not in old_values:
                    old_values[date] = new_value

    existing["features"] = list(feature_map.values())

    # Preserve all previously known NASA source names.
    old_sources = existing.get("header", {}).get("sources", [])
    new_sources = incoming.get("header", {}).get("sources", [])

    combined_sources = sorted(set(old_sources + new_sources))

    existing.setdefault("header", {})["sources"] = combined_sources

    # Keep the complete date coverage in the raw file.
    all_dates = []

    for feature in existing["features"]:

        values = (
            feature.get("properties", {})
            .get("parameter", {})
            .get(variable, {})
        )

        all_dates.extend(values.keys())

    if all_dates:
        existing["header"]["start"] = min(all_dates)
        existing["header"]["end"] = max(all_dates)

    existing["header"]["fill_value"] = FILL_VALUE

    return {
        "added": added_values,
        "replaced": replaced_values,
        "preserved": preserved_values,
        "new_points": new_points,
    }


# --------------------------------------------------
# MANIFEST
# --------------------------------------------------

def record_manifest(record):

    MANIFEST_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    new_row = pd.DataFrame([record])

    if MANIFEST_FILE.exists():

        old = pd.read_csv(MANIFEST_FILE)

        result = pd.concat(
            [old, new_row],
            ignore_index=True,
        )

    else:
        result = new_row

    result.to_csv(
        MANIFEST_FILE,
        index=False,
        encoding="utf-8-sig",
    )


# --------------------------------------------------
# PROCESS ONE TILE AND VARIABLE
# --------------------------------------------------

def update_one(tile, variable, start_date, end_date):

    tile_id = tile["tile_id"]

    raw_file = (
        RAW_DIR
        / tile_id
        / "2026"
        / f"{variable}.json"
    )

    if not raw_file.exists():
        raise FileNotFoundError(
            f"Original YTD JSON not found: {raw_file}"
        )

    print(f"\nDownloading {tile_id} | {variable}")

    incoming = download_variable(
        tile,
        variable,
        start_date,
        end_date,
    )

    with open(raw_file, "r", encoding="utf-8") as file:
        existing = json.load(file)

    result = merge_observations(
        existing,
        incoming,
        variable,
    )

    save_json_atomically(raw_file, existing)

    sources = incoming.get("header", {}).get("sources", [])

    record_manifest({
        "retrieval_time_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "tile_id": tile_id,
        "variable": variable,
        "requested_start": start_date,
        "requested_end": end_date,
        "api_start": incoming.get("header", {}).get("start"),
        "api_end": incoming.get("header", {}).get("end"),
        "sources": ";".join(sources),
        "new_valid_values": result["added"],
        "updated_valid_values": result["replaced"],
        "protected_valid_values": result["preserved"],
        "new_grid_points": result["new_points"],
        "status": "SUCCESS",
    })

    print("Sources:", sources)
    print("New valid values:", result["added"])
    print("Updated valid values:", result["replaced"])
    print("Existing valid values protected:", result["preserved"])
    print("New grid points:", result["new_points"])
    print("Saved:", raw_file)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Incremental NASA POWER India daily updater"
    )

    parser.add_argument(
        "--tile",
        default="T05",
        help="Tile ID such as T05, or ALL",
    )

    parser.add_argument(
        "--lookback-days",
        type=int,
        default=120,
        help="Number of recent days to recheck",
    )

    parser.add_argument(
        "--end-date",
        default=None,
        help="Optional end date in YYYYMMDD format",
    )

    args = parser.parse_args()

    if args.lookback_days < 1:
        raise ValueError("Lookback days must be at least 1")

    if args.end_date:
        end_day = datetime.strptime(
            args.end_date,
            "%Y%m%d",
        ).date()
    else:
        end_day = datetime.now(timezone.utc).date()

    start_day = end_day - timedelta(
        days=args.lookback_days - 1
    )

    # This updater is intended for 2026 data.
    if start_day.year < 2026:
        raise ValueError(
            "The requested lookback extends before 2026. "
            "Use a shorter lookback."
        )

    start_date = start_day.strftime("%Y%m%d")
    end_date = end_day.strftime("%Y%m%d")

    tiles = pd.read_csv(TILE_FILE)

    if args.tile.upper() == "ALL":

        selected_tiles = tiles.to_dict("records")

    else:

        selected_tiles = tiles[
            tiles["tile_id"].str.upper() == args.tile.upper()
        ].to_dict("records")

        if not selected_tiles:
            raise ValueError(
                f"Unknown tile: {args.tile}"
            )

    print("=" * 60)
    print("FIELDWISE AI - NASA POWER DAILY UPDATER")
    print("=" * 60)

    print("Tiles:", len(selected_tiles))
    print("Variables:", len(VARIABLES))
    print("Requests:", len(selected_tiles) * len(VARIABLES))
    print("Start date:", start_date)
    print("End date:", end_date)
    print("Lookback days:", args.lookback_days)

    successful = 0
    failed = 0

    for tile in selected_tiles:

        for variable in VARIABLES:

            try:

                update_one(
                    tile,
                    variable,
                    start_date,
                    end_date,
                )

                successful += 1

            except Exception as error:

                failed += 1

                print(
                    f"\nFAILED: {tile['tile_id']} "
                    f"{variable}: {error}"
                )

                record_manifest({
                    "retrieval_time_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "tile_id": tile["tile_id"],
                    "variable": variable,
                    "requested_start": start_date,
                    "requested_end": end_date,
                    "status": "FAILED",
                    "error": str(error),
                })

            time.sleep(REQUEST_PAUSE)

    print("\n" + "=" * 60)
    print("DAILY UPDATE FINISHED")
    print("=" * 60)

    print("Successful:", successful)
    print("Failed:", failed)
    print("Manifest:", MANIFEST_FILE)


if __name__ == "__main__":
    main()
