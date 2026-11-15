
import xarray as xr

file_path = (
    "data/gpm/test/"
    "3B-DAY.MS.MRG.3IMERG.20250101-S000000-E235959.V07B.nc4"
)

locations = {
    "Ballari": (15.1394, 76.9214),
    "Shivamogga": (13.9326, 75.5750),
    "Vijayapura": (16.8275, 75.7253),
    "Belagavi": (15.8521, 74.5045),
    "Dharwad": (15.4589, 75.0078),
}

ds = xr.open_dataset(file_path, engine="netcdf4")

rain = ds["precipitation"]

print("Rainfall variable information:")
print("Units:", rain.attrs.get("units", "Not specified"))
print("Description:", rain.attrs.get("long_name", "Not specified"))

print("\nGPM rainfall for 1 January 2025:\n")

for name, (latitude, longitude) in locations.items():
    point = rain.sel(
        lat=latitude,
        lon=longitude,
        method="nearest"
    )

    print(
        f"{name}: "
        f"Grid lat={float(point.lat.values):.2f}, "
        f"lon={float(point.lon.values):.2f}, "
        f"rainfall={float(point.values.squeeze()):.4f}"
    )

ds.close()
