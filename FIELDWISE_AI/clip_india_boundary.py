
import json
from pathlib import Path

import pandas as pd
from shapely.geometry import shape, Point
from shapely.prepared import prep

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "india_grid_2021_2025"
BOUNDARY_FILE = DATA_DIR / "india_boundary.geojson"
MET_FILE = DATA_DIR / "processed" / "india_meteorological_daily.csv"
SOLAR_FILE = DATA_DIR / "processed" / "india_solar_daily.csv"

def load_india_boundary():
    with open(BOUNDARY_FILE, "r", encoding="utf-8") as f:
        geojson = json.load(f)

    geometries = [
        shape(feature["geometry"])
        for feature in geojson["features"]
    ]

    from shapely.ops import unary_union
    india = unary_union(geometries)

    if not india.is_valid:
        raise ValueError("India boundary geometry is invalid.")

    return prep(india)

def main():
    print("=" * 55)
    print("FIELDWISE AI - INDIA BOUNDARY CLIPPING")
    print("=" * 55)

    india = load_india_boundary()
    print("India boundary loaded successfully.")

    for label, file_path in [
        ("Meteorological", MET_FILE),
        ("Solar", SOLAR_FILE),
    ]:
        print(f"\nChecking {label} grid points...")

        df = pd.read_csv(
            file_path,
            usecols=["latitude", "longitude"]
        )

        points = df.drop_duplicates()
        inside = [
            india.covers(Point(lon, lat))
            for lat, lon in zip(
                points["latitude"],
                points["longitude"]
            )
        ]

        print("Original unique grid points:", len(points))
        print("Inside boundary:", sum(inside))
        print("Outside boundary:", len(inside) - sum(inside))

    print("\nBOUNDARY CHECK COMPLETED.")
    print("Original CSV files were not modified.")

if __name__ == "__main__":
    main()
