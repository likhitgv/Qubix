
import pandas as pd
from pathlib import Path

NASA_DIR = Path("data/nasa_power")
GPM_FILE = Path("data/gpm/gpm_rainfall_january_2025.csv")
OUTPUT_DIR = Path("data/combined")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Read and combine the five NASA POWER CSV files
power_files = list(NASA_DIR.glob("*_2025-01.csv"))

if len(power_files) != 5:
    raise ValueError(f"Expected 5 NASA POWER files, found {len(power_files)}")

power = pd.concat(
    [pd.read_csv(file) for file in power_files],
    ignore_index=True
)

# Read GPM rainfall data
gpm = pd.read_csv(GPM_FILE)

# Select and rename NASA POWER columns
power = power[
    ["date", "location", "latitude", "longitude", "T2M", "PRECTOTCORR"]
].rename(columns={
    "T2M": "temperature_c",
    "PRECTOTCORR": "nasa_power_rainfall_mm"
})

# Prepare GPM columns
gpm = gpm[
    ["date", "location", "rainfall_mm"]
].rename(columns={
    "rainfall_mm": "gpm_rainfall_mm"
})
# Standardize date formats before merging
power["date"] = pd.to_datetime(
    power["date"].astype(str),
    format="%Y%m%d"
).dt.strftime("%Y-%m-%d")

gpm["date"] = pd.to_datetime(
    gpm["date"]
).dt.strftime("%Y-%m-%d")
# Merge by date and location
combined = pd.merge(
    power,
    gpm,
    on=["date", "location"],
    how="inner",
    validate="one_to_one"
)

combined["source"] = "NASA POWER + NASA GPM IMERG Final V07B"

# Sort and save
combined = combined.sort_values(["date", "location"])

output_file = OUTPUT_DIR / "nasa_environmental_data_january_2025.csv"
combined.to_csv(output_file, index=False)

print("Combination completed!")
print("Total records:", len(combined))
print("Locations:", combined["location"].nunique())
print("Dates:", combined["date"].nunique())
print("Missing values:", combined.isnull().sum().sum())
print("Saved:", output_file)
print(combined.head(10).to_string(index=False))
