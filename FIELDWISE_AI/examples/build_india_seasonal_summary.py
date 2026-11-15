"""Build compact all-India seasonal summaries from the downloaded NASA POWER grid.

Input  : data/india_grid_2021_2025/processed/india_combined_2021_2026/
         india_meteorological_daily_2021_2026.csv  (large, tracked with Git LFS)
Output : data/india_grid_points.csv            one row per NASA grid point
         data/india_grid_seasonal_summary.csv  one row per point/season/year
         data/india_grid_provenance.json       what the numbers are and where from

Run from the project root:  py -3.11 -m examples.build_india_seasonal_summary

The outputs are small (a few MB) so the app loads them instantly instead of
reading the 150 MB daily file. NASA POWER here is gridded/modelled data on a
~56 km grid, not field or weather-station measurements.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from modules.nasa_api import summarise_seasons

ROOT = Path(__file__).resolve().parents[1]
SRC = (
    ROOT / "data" / "india_grid_2021_2025" / "processed"
    / "india_combined_2021_2026" / "india_meteorological_daily_2021_2026.csv"
)
OUT_POINTS = ROOT / "data" / "india_grid_points.csv"
OUT_SUMMARY = ROOT / "data" / "india_grid_seasonal_summary.csv"
OUT_PROVENANCE = ROOT / "data" / "india_grid_provenance.json"

USECOLS = ["latitude", "longitude", "elevation_m", "date", "T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M"]


def grid_id(lat: float, lon: float) -> str:
    """Stable identifier for a grid point, e.g. '15.500,75.000'."""
    return f"{lat:.3f},{lon:.3f}"


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Source file not found (is Git LFS content pulled?): {SRC}")
    if SRC.stat().st_size < 1_000_000:
        raise SystemExit("Source looks like a Git LFS pointer. Run: git lfs pull")

    daily = pd.read_csv(SRC, usecols=USECOLS)
    daily["location"] = [grid_id(a, b) for a, b in zip(daily["latitude"], daily["longitude"])]
    daily["ALLSKY_SFC_SW_DWN"] = float("nan")  # solar covers fewer points; not used in scoring

    points = (
        daily[["location", "latitude", "longitude", "elevation_m"]]
        .drop_duplicates("location")
        .rename(columns={"location": "grid_id"})
        .sort_values(["latitude", "longitude"])
    )
    summary = summarise_seasons(daily)

    points.to_csv(OUT_POINTS, index=False)
    summary.to_csv(OUT_SUMMARY, index=False)

    provenance = {
        "source": "NASA POWER (gridded, MERRA-2 based daily data)",
        "data_nature": (
            "Gridded, modelled values on a ~56 km grid; not field or weather-station measurements."
        ),
        "input_file": str(SRC.relative_to(ROOT)),
        "period": [str(daily["date"].min()), str(daily["date"].max())],
        "grid_points": int(len(points)),
        "variables": ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M"],
        "season_windows": {"kharif": "Jun-Oct", "rabi": "Nov-Mar", "summer": "Apr-May"},
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "Seasons with missing days are marked complete=False and not used for recommendations.",
    }
    OUT_PROVENANCE.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    complete = int(summary["complete"].sum())
    print(f"points: {len(points)} | summary rows: {len(summary)} | complete seasons: {complete}")


if __name__ == "__main__":
    main()
