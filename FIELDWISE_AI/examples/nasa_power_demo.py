
import csv
from pathlib import Path

from modules.nasa_api import fetch_for_locations

KARNATAKA_LOCATIONS = {
    "Ballari": (15.1394, 76.9214),
    "Shivamogga": (13.9326, 75.5750),
    "Vijayapura": (16.8275, 75.7253),
    "Belagavi": (15.8521, 74.5045),
    "Dharwad": (15.4589, 75.0078),
}

OUTPUT_DIR = Path("data/nasa_power")

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = fetch_for_locations(
        locations=KARNATAKA_LOCATIONS,
        start_date="2025-01-01",
        end_date="2025-01-31",
    )

    for name, result in results.items():
        filename = OUTPUT_DIR / f"{name.lower()}_2025-01.csv"

        records = result["records"]

        fieldnames = [
            "location",
            "latitude",
            "longitude",
            "date",
            "T2M",
            "T2M_MAX",
            "T2M_MIN",
            "PRECTOTCORR",
            "RH2M",
            "ALLSKY_SFC_SW_DWN",
        ]

        with filename.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for record in records:
                writer.writerow({
                    "location": name,
                    "latitude": result["latitude"],
                    "longitude": result["longitude"],
                    **record,
                })

        print(f"{name}: {len(records)} records saved to {filename}")
