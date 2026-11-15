
from pathlib import Path
import sys

# Find the main FIELDWISE_AI project folder
PROJECT_FOLDER = Path(__file__).resolve().parent.parent

# Add the project folder to Python's import path
sys.path.insert(0, str(PROJECT_FOLDER))

from modules.data_analysis import (
    load_climate_data,
    generate_climate_summary,
    generate_climate_trends
)

# Find the sample dataset inside the project
DATA_FILE = PROJECT_FOLDER / "data" / "sample_climate_data.csv"


# Load and clean the sample climate data
cleaned_data, report = load_climate_data(DATA_FILE)

print("\n========== Kyro DATA CLEANING TEST ==========")

print("\nCleaned Climate Data:")
print(cleaned_data.to_string(index=False))

print("\nData Quality Report:")
print(report)

print("\nTotal records:", report["total_records"])
print("Invalid dates:", report["invalid_dates"])
print("Invalid rainfall values:", report["invalid_rainfall_values"])

print("\nTEST COMPLETED SUCCESSFULLY!")

print("\n========== CLIMATE SUMMARY TEST ==========")

summary = generate_climate_summary(cleaned_data)

print("\nClimate Summary:")
for key, value in summary.items():
    print(f"{key}: {value}")

print("\nCLIMATE SUMMARY TEST COMPLETED!")

print("\n========== CLIMATE TREND TEST ==========")

trends = generate_climate_trends(cleaned_data)

print("\nDaily Temperature and Rainfall Trends:")
print(trends.to_string(index=False))

print("\nCLIMATE TREND TEST COMPLETED!")
