
import os
import earthaccess
import xarray as xr
import pandas as pd

# Project locations
LOCATIONS = {
    "Ballari": (15.1394, 76.9214),
    "Shivamogga": (13.9326, 75.5750),
    "Vijayapura": (16.8275, 75.7253),
    "Belagavi": (15.8521, 74.5045),
    "Dharwad": (15.4589, 75.0078),
}

START_DATE = "2025-01-01"
END_DATE = "2025-01-31"

OUTPUT_DIR = "data/gpm"
DOWNLOAD_DIR = "data/gpm/january_2025"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Authenticate
print("Logging in to NASA Earthdata...")
auth = earthaccess.login(strategy="interactive")

if not auth:
    raise RuntimeError("Earthdata login failed.")

# Search GPM daily granules
print("Searching GPM granules...")

granules = earthaccess.search_data(
    short_name="GPM_3IMERGDF",
    version="07",
    temporal=(START_DATE, END_DATE)
)

print("Granules found:", len(granules))

if len(granules) != 31:
    raise RuntimeError("Expected 31 daily granules. Check the search results.")

# Download January data
print("Downloading GPM files...")

downloaded_files = earthaccess.download(
    granules,
    local_path=DOWNLOAD_DIR
)

print("Downloaded files:", len(downloaded_files))

# Extract rainfall
records = []

for file_path in downloaded_files:
    print("Processing:", file_path)

    with xr.open_dataset(file_path, engine="netcdf4") as ds:
        rainfall = ds["precipitation"]

        date = pd.to_datetime(
            ds["time"].values[0]
        ).strftime("%Y-%m-%d")

        for location, (lat, lon) in LOCATIONS.items():
            point = rainfall.sel(
                lat=lat,
                lon=lon,
                method="nearest"
            )

            records.append({
                "date": date,
                "location": location,
                "latitude": lat,
                "longitude": lon,
                "rainfall_mm": float(point.values.squeeze()),
                "source": "NASA GPM IMERG Final V07B"
            })

# Save CSV
df = pd.DataFrame(records)

df = df.sort_values(
    ["date", "location"]
)

output_file = os.path.join(
    OUTPUT_DIR,
    "gpm_rainfall_january_2025.csv"
)

df.to_csv(output_file, index=False)

print("\nExtraction completed!")
print("Total records:", len(df))
print("CSV saved:", output_file)
print(df.head(10).to_string(index=False))
