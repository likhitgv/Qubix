
import pandas as pd
from pathlib import Path

source_file = Path(
    "data/combined/nasa_environmental_data_january_2025.csv"
)

output_dir = Path("data/handoff")
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(source_file)

handoff = df[
    [
        "date",
        "location",
        "latitude",
        "longitude",
        "temperature_c",
        "gpm_rainfall_mm"
    ]
].copy()

handoff = handoff.rename(
    columns={"gpm_rainfall_mm": "rainfall_mm"}
)

handoff["source"] = "NASA POWER T2M + NASA GPM IMERG Final V07B"

handoff = handoff.sort_values(["date", "location"])

output_file = output_dir / "FIELDWISE_AI_member2_january_2025.csv"

handoff.to_csv(output_file, index=False)

print("Member 2 handoff created!")
print("Records:", len(handoff))
print("Columns:", list(handoff.columns))
print("Missing values:", handoff.isnull().sum().sum())
print("Saved:", output_file)
