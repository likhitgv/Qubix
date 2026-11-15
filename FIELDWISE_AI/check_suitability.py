
from modules.crop_database import load_crop_database
from modules.crop_suitability import rank_crops

# Load your existing crop database
crops = load_crop_database()

# Illustrative test data (not live NASA data)
environment = {
    "temperature_c": 28,
    "rainfall_mm": 480,
}

farm = {
    "soil_type": "loamy",
    "water_availability": "rainfed",
    "season": "kharif",
}

# Calculate crop rankings
results = rank_crops(crops, environment, farm)

print("\n========== KAIRO ==========")
print("       CROP SUITABILITY RESULTS")
print("==================================")

for index, result in enumerate(results, start=1):
    print(f"\nRank: {index}")
    print(f"Crop: {result['crop_name']}")
    print(f"Suitability: {result['overall_score']}/100")
    print(f"Data coverage: {result['data_coverage_percent']}%")

    print("Component scores:")
    for component, score in result["component_scores"].items():
        print(f"  {component}: {score}/100")

print("\n==================================")
