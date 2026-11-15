
import json
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape, Point
from shapely.ops import unary_union
from shapely.prepared import prep

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "india_grid_2021_2025"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = PROCESSED_DIR / "india_clipped"

BOUNDARY_FILE = DATA_DIR / "india_boundary.geojson"

DATASETS = {
    "meteorological": PROCESSED_DIR / "india_meteorological_daily.csv",
    "solar": PROCESSED_DIR / "india_solar_daily.csv",
}

CHUNK_SIZE = 200_000


def load_boundary():
    with open(BOUNDARY_FILE, "r", encoding="utf-8") as file:
        geojson = json.load(file)

    geometries = [
        shape(feature["geometry"])
        for feature in geojson["features"]
    ]

    boundary = unary_union(geometries)

    if not boundary.is_valid:
        raise ValueError("India boundary is invalid.")

    return prep(boundary)


def get_inside_coordinates(file_path, india):
    grid = pd.read_csv(
        file_path,
        usecols=["latitude", "longitude"]
    ).drop_duplicates()

    inside_coordinates = set()

    for lat, lon in zip(grid["latitude"], grid["longitude"]):
        point = Point(float(lon), float(lat))

        if india.covers(point):
            inside_coordinates.add((float(lat), float(lon)))

    return inside_coordinates, len(grid)


def clip_dataset(name, file_path, india):
    print(f"\nProcessing {name} dataset...")

    inside_coordinates, original_points = get_inside_coordinates(
        file_path, india
    )

    output_file = OUTPUT_DIR / f"india_{name}_daily.csv"

    if output_file.exists():
        output_file.unlink()

    total_input = 0
    total_output = 0

    for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE):
        total_input += len(chunk)

        mask = np.fromiter(
            (
                (float(lat), float(lon)) in inside_coordinates
                for lat, lon in zip(
                    chunk["latitude"],
                    chunk["longitude"]
                )
            ),
            dtype=bool,
            count=len(chunk)
        )

        filtered = chunk.loc[mask]
        total_output += len(filtered)

        filtered.to_csv(
            output_file,
            mode="a",
            index=False,
            header=not output_file.exists() or output_file.stat().st_size == 0
        )

        print(
            f"Processed {total_input:,} rows | "
            f"Kept {total_output:,} rows",
            end="\r"
        )

    print(f"\n{name.upper()} COMPLETED")
    print("Original grid points:", original_points)
    print("India grid points:", len(inside_coordinates))
    print("Outside grid points:", original_points - len(inside_coordinates))
    print("Input records:", total_input)
    print("Output records:", total_output)
    print("Saved:", output_file)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 55)
    print("Kyro - INDIA DATA CLIPPING")
    print("=" * 55)

    india = load_boundary()
    print("India boundary loaded.")

    for name, file_path in DATASETS.items():
        clip_dataset(name, file_path, india)

    print("\nALL DATASETS CLIPPED SUCCESSFULLY.")
    print("Original CSV files were not modified.")
    print("Output folder:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
