"""
Usage example for modules/nasa_api.py.

Run from the project root:
    py -3.11 -m examples.nasa_power_demo

Fetches January 2025 NASA POWER daily data for every configured district,
saves one CSV per district (+ a combined CSV and a provenance JSON), and
shows the hand-off to Member 2's data_analysis module.
"""

import json
from pathlib import Path

import pandas as pd

from config.districts import get_locations
from modules.data_analysis import clean_climate_data, generate_climate_summary
from modules.nasa_api import (
    NASAPowerError,
    fetch_for_locations,
    to_climate_dataframe,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "nasa_power"
START, END = "2025-01-01", "2025-01-31"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        results = fetch_for_locations(get_locations(), START, END)
    except NASAPowerError as exc:
        print(f"NASA POWER unavailable: {exc}")
        print("Use modules.nasa_api.load_sample_data() and label it SAMPLE.")
        return

    frames = []
    provenance = {}

    for name, result in results.items():
        df = to_climate_dataframe(result, name)
        df.drop(columns=["temperature_c", "rainfall_mm", "source"]).to_csv(
            OUTPUT_DIR / f"{name.lower()}_2025-01.csv", index=False
        )
        frames.append(df)
        provenance[name] = {
            "latitude": result["latitude"],
            "longitude": result["longitude"],
            **result["metadata"],
        }
        print(f"{name}: {len(df)} records")

    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(OUTPUT_DIR / "nasa_power_consolidated.csv", index=False)

    with (OUTPUT_DIR / "provenance.json").open("w", encoding="utf-8") as f:
        json.dump(provenance, f, indent=2)

    # Hand-off check: Member 2's cleaner accepts our DataFrame as-is.
    cleaned, quality_report = clean_climate_data(frames[0])
    print(quality_report)
    print(generate_climate_summary(cleaned))


if __name__ == "__main__":
    main()
